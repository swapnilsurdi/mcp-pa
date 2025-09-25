"""
External Identity Provider Integration

Integrates with popular OAuth providers for user authentication:
- Google OAuth 2.0
- Auth0 Universal Login  
- GitHub OAuth
- Apple Sign In
- Microsoft Azure AD

The MCP server acts as a resource server, validating tokens from these providers.
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ExternalUserInfo:
    """User information from external provider"""
    provider: str
    provider_user_id: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    email_verified: bool = False
    tenant_id: Optional[str] = None
    raw_claims: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.raw_claims is None:
            self.raw_claims = {}
        
        # Auto-generate tenant_id from email domain if not provided
        if not self.tenant_id and self.email:
            domain = self.email.split("@")[-1] if "@" in self.email else "default"
            self.tenant_id = domain.replace(".", "_")

class TokenValidationError(Exception):
    """External token validation error"""
    pass

class ExternalProvider(ABC):
    """Abstract base class for external identity providers"""
    
    @abstractmethod
    async def validate_token(self, token: str) -> ExternalUserInfo:
        """
        Validate token and return user information
        
        Args:
            token: Access token from external provider
            
        Returns:
            ExternalUserInfo with validated user data
            
        Raises:
            TokenValidationError: If token is invalid
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider name identifier"""
        pass

class GoogleProvider(ExternalProvider):
    """
    Google OAuth 2.0 provider integration
    
    Validates Google ID tokens and fetches user information.
    """
    
    GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid_configuration"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    
    def __init__(self, client_id: str, client_secret: Optional[str] = None):
        """
        Initialize Google provider
        
        Args:
            client_id: Google OAuth client ID
            client_secret: Optional client secret (for userinfo access)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self._discovery_cache: Optional[Dict] = None
        self._jwks_cache: Optional[Dict] = None
        self._cache_expiry: Optional[datetime] = None
        
        logger.info("GoogleProvider initialized")
    
    async def validate_token(self, token: str) -> ExternalUserInfo:
        """
        Validate Google ID token or access token
        
        Args:
            token: Google ID token (JWT) or access token
            
        Returns:
            ExternalUserInfo with Google user data
        """
        try:
            # Try as ID token first (JWT format)
            if "." in token and token.count(".") == 2:
                return await self._validate_id_token(token)
            else:
                # Try as access token
                return await self._validate_access_token(token)
                
        except Exception as e:
            logger.error(f"Google token validation failed: {e}")
            raise TokenValidationError(f"Invalid Google token: {e}")
    
    async def _validate_id_token(self, id_token: str) -> ExternalUserInfo:
        """Validate Google ID token (JWT)"""
        
        # Get Google's public keys
        jwks = await self._get_google_jwks()
        
        try:
            # Decode and verify JWT
            header = jwt.get_unverified_header(id_token)
            key_id = header.get("kid")
            
            # Find matching key
            signing_key = None
            for key in jwks.get("keys", []):
                if key.get("kid") == key_id:
                    signing_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
                    break
            
            if not signing_key:
                raise TokenValidationError("No matching signing key found")
            
            # Verify token
            payload = jwt.decode(
                id_token,
                signing_key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer="https://accounts.google.com",
                options={"verify_exp": True}
            )
            
            return ExternalUserInfo(
                provider="google",
                provider_user_id=payload["sub"],
                email=payload.get("email", ""),
                name=payload.get("name"),
                picture=payload.get("picture"),
                email_verified=payload.get("email_verified", False),
                raw_claims=payload
            )
            
        except jwt.InvalidTokenError as e:
            raise TokenValidationError(f"Invalid Google ID token: {e}")
    
    async def _validate_access_token(self, access_token: str) -> ExternalUserInfo:
        """Validate Google access token by calling userinfo endpoint"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.GOOGLE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                if response.status_code != 200:
                    raise TokenValidationError(f"Google userinfo error: {response.status_code}")
                
                user_data = response.json()
                
                return ExternalUserInfo(
                    provider="google",
                    provider_user_id=user_data["id"],
                    email=user_data.get("email", ""),
                    name=user_data.get("name"),
                    picture=user_data.get("picture"),
                    email_verified=user_data.get("verified_email", False),
                    raw_claims=user_data
                )
                
        except httpx.RequestError as e:
            raise TokenValidationError(f"Google userinfo request failed: {e}")
    
    async def _get_google_jwks(self) -> Dict[str, Any]:
        """Get Google's JWKS with caching"""
        
        if (self._jwks_cache and self._cache_expiry and 
            datetime.now(timezone.utc) < self._cache_expiry):
            return self._jwks_cache
        
        try:
            # Get discovery document first
            discovery = await self._get_google_discovery()
            jwks_uri = discovery.get("jwks_uri")
            
            if not jwks_uri:
                raise TokenValidationError("No JWKS URI in Google discovery document")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(jwks_uri)
                response.raise_for_status()
                
                self._jwks_cache = response.json()
                self._cache_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
                
                return self._jwks_cache
                
        except Exception as e:
            raise TokenValidationError(f"Failed to fetch Google JWKS: {e}")
    
    async def _get_google_discovery(self) -> Dict[str, Any]:
        """Get Google discovery document with caching"""
        
        if (self._discovery_cache and self._cache_expiry and 
            datetime.now(timezone.utc) < self._cache_expiry):
            return self._discovery_cache
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.GOOGLE_DISCOVERY_URL)
                response.raise_for_status()
                
                self._discovery_cache = response.json()
                self._cache_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
                
                return self._discovery_cache
                
        except Exception as e:
            raise TokenValidationError(f"Failed to fetch Google discovery: {e}")
    
    def get_provider_name(self) -> str:
        return "google"

class Auth0Provider(ExternalProvider):
    """
    Auth0 provider integration
    
    Validates Auth0 access tokens and ID tokens.
    """
    
    def __init__(self, domain: str, audience: str):
        """
        Initialize Auth0 provider
        
        Args:
            domain: Auth0 domain (e.g., "myapp.auth0.com")
            audience: Auth0 API audience identifier
        """
        self.domain = domain
        self.audience = audience
        self.issuer = f"https://{domain}/"
        self._jwks_cache: Optional[Dict] = None
        self._cache_expiry: Optional[datetime] = None
        
        logger.info(f"Auth0Provider initialized: {domain}")
    
    async def validate_token(self, token: str) -> ExternalUserInfo:
        """
        Validate Auth0 access token or ID token
        
        Args:
            token: Auth0 JWT token
            
        Returns:
            ExternalUserInfo with Auth0 user data
        """
        try:
            # Get Auth0 JWKS
            jwks = await self._get_auth0_jwks()
            
            # Decode JWT header
            header = jwt.get_unverified_header(token)
            key_id = header.get("kid")
            
            # Find signing key
            signing_key = None
            for key in jwks.get("keys", []):
                if key.get("kid") == key_id:
                    signing_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
                    break
            
            if not signing_key:
                raise TokenValidationError("No matching Auth0 signing key found")
            
            # Verify token
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"verify_exp": True}
            )
            
            # Extract user info from token
            email = payload.get("email") or payload.get("https://myapp.com/email", "")
            name = payload.get("name") or payload.get("https://myapp.com/name")
            picture = payload.get("picture") or payload.get("https://myapp.com/picture")
            
            return ExternalUserInfo(
                provider="auth0",
                provider_user_id=payload["sub"],
                email=email,
                name=name,
                picture=picture,
                email_verified=payload.get("email_verified", False),
                raw_claims=payload
            )
            
        except jwt.InvalidTokenError as e:
            raise TokenValidationError(f"Invalid Auth0 token: {e}")
        except Exception as e:
            logger.error(f"Auth0 token validation failed: {e}")
            raise TokenValidationError(f"Auth0 validation error: {e}")
    
    async def _get_auth0_jwks(self) -> Dict[str, Any]:
        """Get Auth0 JWKS with caching"""
        
        if (self._jwks_cache and self._cache_expiry and 
            datetime.now(timezone.utc) < self._cache_expiry):
            return self._jwks_cache
        
        try:
            jwks_url = f"https://{self.domain}/.well-known/jwks.json"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(jwks_url)
                response.raise_for_status()
                
                self._jwks_cache = response.json()
                self._cache_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
                
                return self._jwks_cache
                
        except Exception as e:
            raise TokenValidationError(f"Failed to fetch Auth0 JWKS: {e}")
    
    def get_provider_name(self) -> str:
        return "auth0"

class GitHubProvider(ExternalProvider):
    """
    GitHub OAuth provider integration
    
    Validates GitHub access tokens via API.
    """
    
    GITHUB_USER_URL = "https://api.github.com/user"
    
    def __init__(self):
        """Initialize GitHub provider"""
        logger.info("GitHubProvider initialized")
    
    async def validate_token(self, token: str) -> ExternalUserInfo:
        """
        Validate GitHub access token
        
        Args:
            token: GitHub access token
            
        Returns:
            ExternalUserInfo with GitHub user data
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.GITHUB_USER_URL,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github.v3+json"
                    }
                )
                
                if response.status_code != 200:
                    raise TokenValidationError(f"GitHub API error: {response.status_code}")
                
                user_data = response.json()
                
                return ExternalUserInfo(
                    provider="github",
                    provider_user_id=str(user_data["id"]),
                    email=user_data.get("email", "") or f"{user_data['login']}@github.local",
                    name=user_data.get("name") or user_data.get("login"),
                    picture=user_data.get("avatar_url"),
                    email_verified=True,  # GitHub emails are considered verified
                    raw_claims=user_data
                )
                
        except httpx.RequestError as e:
            raise TokenValidationError(f"GitHub API request failed: {e}")
        except Exception as e:
            logger.error(f"GitHub token validation failed: {e}")
            raise TokenValidationError(f"GitHub validation error: {e}")
    
    def get_provider_name(self) -> str:
        return "github"

class ExternalProviderRegistry:
    """
    Registry for managing multiple external identity providers
    """
    
    def __init__(self):
        self.providers: Dict[str, ExternalProvider] = {}
        logger.info("ExternalProviderRegistry initialized")
    
    def register_provider(self, provider: ExternalProvider) -> None:
        """
        Register an external provider
        
        Args:
            provider: ExternalProvider instance
        """
        name = provider.get_provider_name()
        self.providers[name] = provider
        logger.info(f"Registered external provider: {name}")
    
    def get_provider(self, provider_name: str) -> Optional[ExternalProvider]:
        """
        Get provider by name
        
        Args:
            provider_name: Provider identifier
            
        Returns:
            ExternalProvider instance or None
        """
        return self.providers.get(provider_name)
    
    async def validate_token(self, token: str, provider_hint: Optional[str] = None) -> ExternalUserInfo:
        """
        Validate token against registered providers
        
        Args:
            token: Token to validate
            provider_hint: Optional provider name hint
            
        Returns:
            ExternalUserInfo from successful validation
            
        Raises:
            TokenValidationError: If no provider can validate the token
        """
        # Try hinted provider first
        if provider_hint and provider_hint in self.providers:
            try:
                return await self.providers[provider_hint].validate_token(token)
            except TokenValidationError:
                pass  # Fall back to trying all providers
        
        # Try all providers
        last_error = None
        for provider_name, provider in self.providers.items():
            try:
                return await provider.validate_token(token)
            except TokenValidationError as e:
                last_error = e
                continue
        
        # No provider could validate the token
        raise TokenValidationError(f"No provider could validate token: {last_error}")
    
    def list_providers(self) -> List[str]:
        """Get list of registered provider names"""
        return list(self.providers.keys())

# Convenience functions

def create_google_provider(client_id: str, client_secret: Optional[str] = None) -> GoogleProvider:
    """Create Google OAuth provider"""
    return GoogleProvider(client_id=client_id, client_secret=client_secret)

def create_auth0_provider(domain: str, audience: str) -> Auth0Provider:
    """Create Auth0 provider"""  
    return Auth0Provider(domain=domain, audience=audience)

def create_github_provider() -> GitHubProvider:
    """Create GitHub OAuth provider"""
    return GitHubProvider()

def create_provider_registry() -> ExternalProviderRegistry:
    """Create provider registry with common providers"""
    registry = ExternalProviderRegistry()
    return registry