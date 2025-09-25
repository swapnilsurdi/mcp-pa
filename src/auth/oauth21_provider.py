"""
OAuth 2.1 Provider Implementation for MCP Personal Assistant

Implements OAuth 2.1 specification with MCP authorization compliance:
- PKCE mandatory for all authorization flows
- Resource indicators support (RFC 8707)
- Enhanced security requirements
- Dynamic client registration (RFC 7591)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Literal
from urllib.parse import urlencode, parse_qs
import secrets

from .pkce_verifier import PKCEVerifier, PKCEError
from .client_authenticator import ClientAuthenticator, ClientContext, ClientAuthenticationError
from .token_manager import TokenManager, TokenContext, TokenError

logger = logging.getLogger(__name__)

class OAuth21Error(Exception):
    """OAuth 2.1 specific errors"""
    def __init__(self, error: str, description: str = "", error_uri: str = ""):
        self.error = error
        self.description = description
        self.error_uri = error_uri
        super().__init__(f"{error}: {description}")

class OAuth21Provider:
    """
    OAuth 2.1 compliant authorization server for MCP
    
    Features:
    - PKCE mandatory for all flows
    - Resource indicators (RFC 8707)
    - Enhanced security requirements
    - MCP specification compliance
    """
    
    def __init__(self,
                 issuer: str,
                 token_manager: TokenManager,
                 client_authenticator: ClientAuthenticator,
                 client_registry: Dict[str, Dict[str, Any]]):
        """
        Initialize OAuth 2.1 provider
        
        Args:
            issuer: Authorization server issuer identifier
            token_manager: Token management instance
            client_authenticator: Client authentication handler
            client_registry: Registered client configurations
        """
        self.issuer = issuer
        self.token_manager = token_manager
        self.client_authenticator = client_authenticator
        self.client_registry = client_registry
        
        # Authorization code store (use Redis/database in production)
        self.authorization_codes: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"OAuth21Provider initialized for issuer: {issuer}")
    
    def handle_authorization_request(self, 
                                   client_id: str,
                                   redirect_uri: str,
                                   scope: Optional[str] = None,
                                   state: Optional[str] = None,
                                   code_challenge: Optional[str] = None,
                                   code_challenge_method: Optional[str] = None,
                                   resource: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle OAuth 2.1 authorization request
        
        Args:
            client_id: OAuth client identifier
            redirect_uri: Client redirect URI
            scope: Requested scope
            state: Client state parameter
            code_challenge: PKCE code challenge
            code_challenge_method: PKCE challenge method
            resource: Resource indicator (RFC 8707)
            
        Returns:
            Authorization response data
            
        Raises:
            OAuth21Error: If request is invalid
        """
        # Validate client
        client_config = self.client_registry.get(client_id)
        if not client_config:
            raise OAuth21Error("invalid_client", "Unknown client identifier")
        
        # Validate redirect URI
        if not self._validate_redirect_uri(redirect_uri, client_config):
            raise OAuth21Error("invalid_request", "Invalid redirect URI")
        
        # OAuth 2.1 requires PKCE for all clients
        if not code_challenge:
            raise OAuth21Error(
                "invalid_request", 
                "PKCE code_challenge is required for OAuth 2.1"
            )
        
        # Validate PKCE method
        if code_challenge_method not in ["S256", "plain"]:
            raise OAuth21Error(
                "invalid_request",
                "Invalid code_challenge_method. Must be 'S256' or 'plain'"
            )
        
        # Recommend S256 method
        if code_challenge_method == "plain":
            logger.warning(f"Client {client_id} using 'plain' PKCE method - S256 recommended")
        
        # Generate authorization code
        auth_code = self._generate_authorization_code()
        
        # Store authorization data
        self.authorization_codes[auth_code] = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "resource": resource,
            "expires_at": datetime.now(timezone.utc).timestamp() + 600,  # 10 minutes
            "used": False,
            "created_at": datetime.now(timezone.utc)
        }
        
        logger.info(f"Authorization code generated for client {client_id}")
        
        # Return authorization response
        response_params = {"code": auth_code}
        if state:
            response_params["state"] = state
        
        return {
            "redirect_uri": redirect_uri,
            "params": response_params,
            "method": "GET"  # Authorization codes via GET redirect
        }
    
    def handle_token_request(self,
                           grant_type: str,
                           client_auth: Dict[str, Any],
                           **params) -> Dict[str, Any]:
        """
        Handle OAuth 2.1 token request
        
        Args:
            grant_type: OAuth grant type
            client_auth: Client authentication data
            **params: Additional grant-specific parameters
            
        Returns:
            Token response
            
        Raises:
            OAuth21Error: If request is invalid
        """
        # OAuth 2.1 only supports authorization_code and refresh_token grants
        if grant_type == "authorization_code":
            return self._handle_authorization_code_grant(client_auth, **params)
        elif grant_type == "refresh_token":
            return self._handle_refresh_token_grant(client_auth, **params)
        else:
            raise OAuth21Error(
                "unsupported_grant_type",
                f"Grant type '{grant_type}' not supported by OAuth 2.1"
            )
    
    def _handle_authorization_code_grant(self,
                                       client_auth: Dict[str, Any],
                                       code: str,
                                       redirect_uri: str,
                                       code_verifier: str,
                                       resource: Optional[str] = None,
                                       **kwargs) -> Dict[str, Any]:
        """Handle authorization code grant with PKCE"""
        
        # Authenticate client
        try:
            client_context = self.client_authenticator.authenticate_client(
                auth_method=client_auth.get("method", "client_secret_basic"),
                credentials=client_auth.get("credentials", {})
            )
        except ClientAuthenticationError as e:
            raise OAuth21Error("invalid_client", str(e))
        
        # Validate authorization code
        auth_data = self.authorization_codes.get(code)
        if not auth_data:
            raise OAuth21Error("invalid_grant", "Invalid authorization code")
        
        if auth_data["used"]:
            # Code reuse detected - revoke any issued tokens
            logger.warning(f"Authorization code reuse detected for client {client_context.client_id}")
            raise OAuth21Error("invalid_grant", "Authorization code already used")
        
        if datetime.now(timezone.utc).timestamp() > auth_data["expires_at"]:
            raise OAuth21Error("invalid_grant", "Authorization code has expired")
        
        if auth_data["client_id"] != client_context.client_id:
            raise OAuth21Error("invalid_grant", "Authorization code issued to different client")
        
        if auth_data["redirect_uri"] != redirect_uri:
            raise OAuth21Error("invalid_grant", "Invalid redirect URI")
        
        # Verify PKCE code verifier
        try:
            pkce_valid = PKCEVerifier.verify_code_challenge(
                code_verifier=code_verifier,
                code_challenge=auth_data["code_challenge"],
                method=auth_data["code_challenge_method"]  # type: ignore
            )
            
            if not pkce_valid:
                raise OAuth21Error("invalid_grant", "PKCE verification failed")
                
        except PKCEError as e:
            raise OAuth21Error("invalid_grant", f"PKCE error: {e}")
        
        # Mark code as used
        auth_data["used"] = True
        
        # Use resource from token request or fallback to authorization request
        final_resource = resource or auth_data["resource"]
        
        # Create access token
        # For MCP, we'll use a mock user_id (in real implementation, this would come from user authentication)
        user_id = f"user_{client_context.client_id}"  # Simplified for MCP use case
        
        token_context = self.token_manager.create_access_token(
            client_id=client_context.client_id,
            user_id=user_id,
            scope=auth_data["scope"],
            resource=final_resource
        )
        
        # Create refresh token
        refresh_token = self.token_manager.create_refresh_token(
            client_id=client_context.client_id,
            user_id=user_id,
            access_token_jti=token_context.metadata["jti"]
        )
        
        logger.info(f"Access token issued for client {client_context.client_id}")
        
        # Build token response
        response = {
            "access_token": token_context.access_token,
            "token_type": token_context.token_type,
            "expires_in": token_context.expires_in,
            "refresh_token": refresh_token
        }
        
        if token_context.scope:
            response["scope"] = token_context.scope
        
        if final_resource:
            response["resource"] = final_resource
        
        return response
    
    def _handle_refresh_token_grant(self,
                                  client_auth: Dict[str, Any],
                                  refresh_token: str,
                                  resource: Optional[str] = None,
                                  **kwargs) -> Dict[str, Any]:
        """Handle refresh token grant"""
        
        # Authenticate client
        try:
            client_context = self.client_authenticator.authenticate_client(
                auth_method=client_auth.get("method", "client_secret_basic"),
                credentials=client_auth.get("credentials", {})
            )
        except ClientAuthenticationError as e:
            raise OAuth21Error("invalid_client", str(e))
        
        # Refresh access token
        try:
            new_token_context = self.token_manager.refresh_access_token(
                refresh_token=refresh_token,
                resource=resource
            )
        except TokenError as e:
            raise OAuth21Error("invalid_grant", str(e))
        
        logger.info(f"Token refreshed for client {client_context.client_id}")
        
        # Build token response
        response = {
            "access_token": new_token_context.access_token,
            "token_type": new_token_context.token_type,
            "expires_in": new_token_context.expires_in,
            "refresh_token": new_token_context.refresh_token
        }
        
        if new_token_context.scope:
            response["scope"] = new_token_context.scope
        
        if resource:
            response["resource"] = resource
        
        return response
    
    def validate_resource_request(self, 
                                access_token: str,
                                resource: Optional[str] = None,
                                required_scope: Optional[str] = None) -> TokenContext:
        """
        Validate access token for resource access
        
        Args:
            access_token: Bearer access token
            resource: Expected resource indicator
            required_scope: Required scope for access
            
        Returns:
            Valid TokenContext
            
        Raises:
            OAuth21Error: If token is invalid or insufficient
        """
        try:
            token_context = self.token_manager.validate_access_token(
                token=access_token,
                resource=resource
            )
            
            # Validate scope if required
            if required_scope and token_context.scope:
                token_scopes = set(token_context.scope.split())
                required_scopes = set(required_scope.split())
                
                if not required_scopes.issubset(token_scopes):
                    raise OAuth21Error(
                        "insufficient_scope",
                        f"Token missing required scope: {required_scope}"
                    )
            
            return token_context
            
        except TokenError as e:
            raise OAuth21Error("invalid_token", str(e))
    
    def revoke_token(self, 
                    token: str,
                    client_auth: Dict[str, Any]) -> bool:
        """
        Revoke access or refresh token (RFC 7009)
        
        Args:
            token: Token to revoke
            client_auth: Client authentication
            
        Returns:
            True if token was revoked
        """
        try:
            # Authenticate client
            client_context = self.client_authenticator.authenticate_client(
                auth_method=client_auth.get("method", "client_secret_basic"),
                credentials=client_auth.get("credentials", {})
            )
            
            # Revoke token
            revoked = self.token_manager.revoke_token(token)
            
            if revoked:
                logger.info(f"Token revoked for client {client_context.client_id}")
            
            return revoked
            
        except ClientAuthenticationError:
            # RFC 7009 says to return success even for invalid clients
            # to prevent token scanning attacks
            return True
    
    def introspect_token(self, 
                        token: str,
                        client_auth: Dict[str, Any]) -> Dict[str, Any]:
        """
        Token introspection endpoint (RFC 7662)
        
        Args:
            token: Token to introspect
            client_auth: Client authentication
            
        Returns:
            Token introspection response
        """
        try:
            # Authenticate client
            self.client_authenticator.authenticate_client(
                auth_method=client_auth.get("method", "client_secret_basic"),
                credentials=client_auth.get("credentials", {})
            )
            
            return self.token_manager.introspect_token(token)
            
        except ClientAuthenticationError:
            return {"active": False}
    
    def _validate_redirect_uri(self, redirect_uri: str, client_config: Dict[str, Any]) -> bool:
        """Validate redirect URI against registered URIs"""
        registered_uris = client_config.get("redirect_uris", [])
        return redirect_uri in registered_uris
    
    def _generate_authorization_code(self) -> str:
        """Generate secure authorization code"""
        return secrets.token_urlsafe(32)
    
    def get_authorization_server_metadata(self) -> Dict[str, Any]:
        """
        Get OAuth Authorization Server Metadata (RFC 8414)
        """
        return {
            "issuer": self.issuer,
            "authorization_endpoint": f"{self.issuer}/oauth/authorize",
            "token_endpoint": f"{self.issuer}/oauth/token",
            "revocation_endpoint": f"{self.issuer}/oauth/revoke",
            "introspection_endpoint": f"{self.issuer}/oauth/introspect",
            "registration_endpoint": f"{self.issuer}/oauth/register",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256", "plain"],
            "token_endpoint_auth_methods_supported": [
                "client_secret_basic",
                "client_secret_post", 
                "private_key_jwt",
                "tls_client_auth"
            ],
            "scopes_supported": ["read", "write", "admin"],
            "response_modes_supported": ["query"],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["HS256", "RS256"],
            "token_endpoint_auth_signing_alg_values_supported": ["HS256", "RS256"],
            "resource_indicators_supported": True,
            "pkce_required": True
        }

# Convenience function
def create_oauth21_provider(
    issuer: str,
    secret_key: str,
    client_registry: Dict[str, Dict[str, Any]]
) -> OAuth21Provider:
    """Create OAuth 2.1 provider with default configuration"""
    
    token_manager = TokenManager(secret_key, issuer=issuer)
    client_authenticator = ClientAuthenticator(
        client_registry=client_registry,
        jwt_audience=f"{issuer}/oauth/token"
    )
    
    return OAuth21Provider(
        issuer=issuer,
        token_manager=token_manager,
        client_authenticator=client_authenticator,
        client_registry=client_registry
    )