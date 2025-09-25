"""
Authentication Service for HTTP MCP Server

Provides OAuth 2.0, JWT, and API key authentication with
multi-tenancy support and user context management.
"""

import logging
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
import jwt
import asyncio
from dataclasses import dataclass

import httpx
from fastapi import HTTPException, status
from authlib.jose import jwt as authlib_jwt
from authlib.integrations.httpx_client import AsyncOAuth2Client

logger = logging.getLogger(__name__)

@dataclass
class UserContext:
    """User context with tenant information"""
    user_id: str
    email: str
    name: Optional[str] = None
    tenant_id: str = "default"
    permissions: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = ["read", "write"]
        if self.metadata is None:
            self.metadata = {}

class AuthenticationError(Exception):
    """Authentication error"""
    pass

class AuthorizationError(Exception):
    """Authorization error"""
    pass

class OAuthProvider:
    """OAuth 2.0 provider integration"""
    
    def __init__(self, client_id: str, client_secret: str, issuer: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.issuer = issuer
        self.client = AsyncOAuth2Client(client_id, client_secret)
        self._discovery_cache: Optional[Dict] = None
        self._jwks_cache: Optional[Dict] = None
        self._cache_expiry: Optional[datetime] = None
    
    async def get_discovery_document(self) -> Dict[str, Any]:
        """Get OAuth discovery document with caching"""
        if (self._discovery_cache and self._cache_expiry and 
            datetime.now(timezone.utc) < self._cache_expiry):
            return self._discovery_cache
        
        discovery_url = f"{self.issuer}/.well-known/openid_configuration"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(discovery_url)
                response.raise_for_status()
                
                self._discovery_cache = response.json()
                self._cache_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
                
                return self._discovery_cache
                
        except Exception as e:
            logger.error(f"Failed to fetch discovery document: {e}")
            raise AuthenticationError("Failed to fetch OAuth configuration")
    
    async def get_jwks(self) -> Dict[str, Any]:
        """Get JSON Web Key Set with caching"""
        if (self._jwks_cache and self._cache_expiry and 
            datetime.now(timezone.utc) < self._cache_expiry):
            return self._jwks_cache
        
        discovery = await self.get_discovery_document()
        jwks_uri = discovery.get("jwks_uri")
        
        if not jwks_uri:
            raise AuthenticationError("JWKS URI not found in discovery document")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(jwks_uri)
                response.raise_for_status()
                
                self._jwks_cache = response.json()
                return self._jwks_cache
                
        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            raise AuthenticationError("Failed to fetch OAuth keys")
    
    async def verify_token(self, token: str) -> UserContext:
        """Verify OAuth JWT token and return user context"""
        try:
            # Get JWKS for token verification
            jwks = await self.get_jwks()
            
            # Decode and verify token
            claims = authlib_jwt.decode(token, jwks)
            
            # Validate standard claims
            if claims.get("iss") != self.issuer:
                raise AuthenticationError("Invalid issuer")
            
            if claims.get("aud") != self.client_id:
                raise AuthenticationError("Invalid audience")
            
            # Extract user information
            user_id = claims.get("sub")
            email = claims.get("email") or claims.get("preferred_username")
            name = claims.get("name") or claims.get("given_name", "") + " " + claims.get("family_name", "")
            
            if not user_id:
                raise AuthenticationError("User ID not found in token")
            
            # Determine tenant ID (could be from claims or derived from email domain)
            tenant_id = claims.get("tenant_id") or self._derive_tenant_id(email)
            
            # Extract permissions/roles
            permissions = self._extract_permissions(claims)
            
            return UserContext(
                user_id=user_id,
                email=email,
                name=name.strip() if name else None,
                tenant_id=tenant_id,
                permissions=permissions,
                metadata={
                    "oauth_claims": claims,
                    "auth_time": claims.get("auth_time"),
                    "session_state": claims.get("session_state")
                }
            )
            
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise AuthenticationError("Invalid or expired token")
    
    def _derive_tenant_id(self, email: Optional[str]) -> str:
        """Derive tenant ID from email domain or other factors"""
        if not email:
            return "default"
        
        # Extract domain from email
        domain = email.split("@")[-1] if "@" in email else "default"
        
        # Map known domains to tenant IDs
        domain_mapping = {
            "gmail.com": "personal",
            "outlook.com": "personal",
            "yahoo.com": "personal"
        }
        
        return domain_mapping.get(domain, domain.replace(".", "_"))
    
    def _extract_permissions(self, claims: Dict[str, Any]) -> List[str]:
        """Extract permissions from OAuth claims"""
        permissions = []
        
        # Check for roles
        roles = claims.get("roles", [])
        if isinstance(roles, str):
            roles = [roles]
        
        # Map roles to permissions
        role_permission_mapping = {
            "admin": ["read", "write", "admin"],
            "user": ["read", "write"],
            "viewer": ["read"]
        }
        
        for role in roles:
            permissions.extend(role_permission_mapping.get(role, ["read"]))
        
        # Check for direct permissions claim
        if "permissions" in claims:
            perms = claims["permissions"]
            if isinstance(perms, list):
                permissions.extend(perms)
            elif isinstance(perms, str):
                permissions.extend(perms.split(","))
        
        # Default permissions if none found
        if not permissions:
            permissions = ["read", "write"]
        
        return list(set(permissions))  # Remove duplicates

class JWTAuth:
    """JWT authentication handler"""
    
    def __init__(self, secret: str, algorithm: str = "HS256", expiry_hours: int = 24):
        self.secret = secret
        self.algorithm = algorithm
        self.expiry_hours = expiry_hours
    
    def create_token(self, user_context: UserContext) -> str:
        """Create JWT token for user"""
        payload = {
            "sub": user_context.user_id,
            "email": user_context.email,
            "name": user_context.name,
            "tenant_id": user_context.tenant_id,
            "permissions": user_context.permissions,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=self.expiry_hours)
        }
        
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> UserContext:
        """Verify JWT token and return user context"""
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            
            return UserContext(
                user_id=payload["sub"],
                email=payload["email"],
                name=payload.get("name"),
                tenant_id=payload.get("tenant_id", "default"),
                permissions=payload.get("permissions", ["read", "write"]),
                metadata={"jwt_payload": payload}
            )
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {e}")

class APIKeyAuth:
    """API Key authentication handler"""
    
    def __init__(self, api_keys: Dict[str, UserContext]):
        self.api_keys = api_keys
    
    def verify_api_key(self, api_key: str) -> UserContext:
        """Verify API key and return user context"""
        user_context = self.api_keys.get(api_key)
        
        if not user_context:
            raise AuthenticationError("Invalid API key")
        
        return user_context
    
    @classmethod
    def from_key_list(cls, api_keys: List[str]) -> "APIKeyAuth":
        """Create APIKeyAuth from list of keys with default contexts"""
        key_contexts = {}
        
        for i, key in enumerate(api_keys):
            key_contexts[key] = UserContext(
                user_id=f"api_user_{i}",
                email=f"api_user_{i}@system.local",
                tenant_id="api",
                permissions=["read", "write"]
            )
        
        return cls(key_contexts)

class AuthService:
    """Main authentication service"""
    
    def __init__(self, 
                 oauth_provider: Optional[OAuthProvider] = None,
                 jwt_auth: Optional[JWTAuth] = None,
                 api_key_auth: Optional[APIKeyAuth] = None):
        self.oauth_provider = oauth_provider
        self.jwt_auth = jwt_auth
        self.api_key_auth = api_key_auth
    
    async def authenticate(self, token: str, auth_type: str = "auto") -> UserContext:
        """Authenticate token and return user context"""
        
        if auth_type == "oauth" or (auth_type == "auto" and self.oauth_provider):
            if not self.oauth_provider:
                raise AuthenticationError("OAuth provider not configured")
            return await self.oauth_provider.verify_token(token)
        
        elif auth_type == "jwt" or (auth_type == "auto" and self.jwt_auth):
            if not self.jwt_auth:
                raise AuthenticationError("JWT authentication not configured")
            return self.jwt_auth.verify_token(token)
        
        elif auth_type == "api_key" or (auth_type == "auto" and self.api_key_auth):
            if not self.api_key_auth:
                raise AuthenticationError("API key authentication not configured")
            return self.api_key_auth.verify_api_key(token)
        
        else:
            # Try all available methods in order
            errors = []
            
            if self.oauth_provider:
                try:
                    return await self.oauth_provider.verify_token(token)
                except Exception as e:
                    errors.append(f"OAuth: {e}")
            
            if self.jwt_auth:
                try:
                    return self.jwt_auth.verify_token(token)
                except Exception as e:
                    errors.append(f"JWT: {e}")
            
            if self.api_key_auth:
                try:
                    return self.api_key_auth.verify_api_key(token)
                except Exception as e:
                    errors.append(f"API Key: {e}")
            
            raise AuthenticationError(f"Authentication failed: {'; '.join(errors)}")
    
    def check_permission(self, user_context: UserContext, required_permission: str) -> bool:
        """Check if user has required permission"""
        return required_permission in user_context.permissions
    
    def require_permission(self, user_context: UserContext, required_permission: str) -> None:
        """Require user to have permission, raise exception if not"""
        if not self.check_permission(user_context, required_permission):
            raise AuthorizationError(f"Permission '{required_permission}' required")


def create_auth_service(auth_config) -> Optional[AuthService]:
    """Create authentication service from configuration"""
    if not auth_config.enabled:
        return None
    
    oauth_provider = None
    jwt_auth = None
    api_key_auth = None
    
    # Setup OAuth provider
    if (auth_config.provider == "oauth" and 
        auth_config.oauth_client_id and 
        auth_config.oauth_client_secret and 
        auth_config.oauth_issuer):
        
        oauth_provider = OAuthProvider(
            auth_config.oauth_client_id,
            auth_config.oauth_client_secret,
            auth_config.oauth_issuer
        )
    
    # Setup JWT authentication
    if auth_config.jwt_secret:
        jwt_auth = JWTAuth(auth_config.jwt_secret)
    
    # Setup API key authentication
    if auth_config.api_keys:
        api_key_auth = APIKeyAuth.from_key_list(auth_config.api_keys)
    
    return AuthService(oauth_provider, jwt_auth, api_key_auth)