"""
OAuth 2.1 Token Management Implementation

Handles token lifecycle with OAuth 2.1 requirements:
- Short-lived access tokens (≤ 1 hour)
- Refresh token rotation
- Resource indicators for audience validation
- Secure token storage and validation
"""

import json
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Set
import jwt
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

logger = logging.getLogger(__name__)

@dataclass
class TokenContext:
    """Token context with OAuth 2.1 compliance"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600  # 1 hour max per OAuth 2.1
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    resource: Optional[str] = None  # Resource indicator
    client_id: str = ""
    user_id: str = ""
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

class TokenError(Exception):
    """Token-related errors"""
    pass

class TokenManager:
    """
    OAuth 2.1 compliant token manager with resource indicators support
    
    Features:
    - Short-lived access tokens (max 1 hour)
    - Refresh token rotation for enhanced security
    - Resource indicators for audience validation
    - Secure token generation and validation
    - Token introspection capabilities
    """
    
    def __init__(self, 
                 secret_key: str,
                 default_token_expiry: int = 3600,  # 1 hour
                 refresh_token_expiry: int = 7200,  # 2 hours
                 issuer: str = "mcp-personal-assistant"):
        """
        Initialize token manager
        
        Args:
            secret_key: Secret key for token signing
            default_token_expiry: Default access token expiry in seconds
            refresh_token_expiry: Refresh token expiry in seconds
            issuer: Token issuer identifier
        """
        self.secret_key = secret_key
        self.default_token_expiry = min(default_token_expiry, 3600)  # Enforce 1 hour max
        self.refresh_token_expiry = refresh_token_expiry
        self.issuer = issuer
        
        # In-memory token store (use Redis/database in production)
        self.active_tokens: Dict[str, TokenContext] = {}
        self.refresh_tokens: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"TokenManager initialized with {default_token_expiry}s token expiry")
    
    def create_access_token(self,
                          client_id: str,
                          user_id: str,
                          scope: Optional[str] = None,
                          resource: Optional[str] = None,
                          expires_in: Optional[int] = None) -> TokenContext:
        """
        Create OAuth 2.1 compliant access token
        
        Args:
            client_id: OAuth client identifier
            user_id: User identifier
            scope: Token scope
            resource: Resource indicator (RFC 8707)
            expires_in: Token expiry in seconds (max 3600)
            
        Returns:
            TokenContext with access token details
        """
        # Enforce OAuth 2.1 token expiry limits
        if expires_in is None:
            expires_in = self.default_token_expiry
        expires_in = min(expires_in, 3600)  # Max 1 hour
        
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(seconds=expires_in)
        
        # Create JWT payload with resource indicator support
        payload = {
            "iss": self.issuer,
            "sub": user_id,
            "aud": resource or self.issuer,  # Use resource as audience
            "client_id": client_id,
            "exp": int(expiry.timestamp()),
            "iat": int(now.timestamp()),
            "jti": self._generate_token_id(),
            "token_type": "access_token"
        }
        
        # Add scope if provided
        if scope:
            payload["scope"] = scope
        
        # Add resource indicator if provided
        if resource:
            payload["resource"] = resource
        
        # Generate JWT access token
        access_token = jwt.encode(payload, self.secret_key, algorithm="HS256")
        
        # Create token context
        token_context = TokenContext(
            access_token=access_token,
            expires_in=expires_in,
            scope=scope,
            resource=resource,
            client_id=client_id,
            user_id=user_id,
            issued_at=now,
            metadata={
                "jti": payload["jti"],
                "algorithm": "HS256"
            }
        )
        
        # Store token for tracking
        self.active_tokens[payload["jti"]] = token_context
        
        logger.info(f"Created access token for client {client_id}, user {user_id}")
        return token_context
    
    def create_refresh_token(self, 
                           client_id: str,
                           user_id: str,
                           access_token_jti: str) -> str:
        """
        Create refresh token with rotation support
        
        Args:
            client_id: OAuth client identifier
            user_id: User identifier
            access_token_jti: Associated access token JTI
            
        Returns:
            Refresh token string
        """
        refresh_token = self._generate_secure_token()
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.refresh_token_expiry)
        
        # Store refresh token metadata
        self.refresh_tokens[refresh_token] = {
            "client_id": client_id,
            "user_id": user_id,
            "access_token_jti": access_token_jti,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc),
            "used": False
        }
        
        logger.info(f"Created refresh token for client {client_id}")
        return refresh_token
    
    def validate_access_token(self, token: str, resource: Optional[str] = None) -> TokenContext:
        """
        Validate access token with resource indicator support
        
        Args:
            token: JWT access token
            resource: Expected resource indicator
            
        Returns:
            TokenContext if valid
            
        Raises:
            TokenError: If token is invalid
        """
        try:
            # Decode and verify JWT
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=["HS256"],
                options={
                    "require": ["exp", "iat", "iss", "sub", "jti"],
                    "verify_exp": True,
                    "verify_iat": True,
                }
            )
            
            # Validate issuer
            if payload.get("iss") != self.issuer:
                raise TokenError("Invalid token issuer")
            
            # Validate token type
            if payload.get("token_type") != "access_token":
                raise TokenError("Invalid token type")
            
            # Validate resource indicator if provided
            if resource:
                token_resource = payload.get("resource")
                token_audience = payload.get("aud")
                
                if token_resource and token_resource != resource:
                    raise TokenError("Token not valid for requested resource")
                
                if token_audience and token_audience != resource:
                    raise TokenError("Token audience mismatch")
            
            # Check if token is still active
            jti = payload.get("jti")
            if jti not in self.active_tokens:
                raise TokenError("Token not found or revoked")
            
            token_context = self.active_tokens[jti]
            
            # Verify token hasn't expired (additional check)
            if datetime.now(timezone.utc) >= token_context.issued_at + timedelta(seconds=token_context.expires_in):
                self._revoke_token(jti)
                raise TokenError("Token has expired")
            
            logger.debug(f"Token validation successful for jti: {jti}")
            return token_context
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"JWT validation failed: {e}")
            raise TokenError(f"Invalid token: {e}")
        
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise TokenError(f"Token validation failed: {e}")
    
    def refresh_access_token(self, 
                           refresh_token: str,
                           resource: Optional[str] = None) -> TokenContext:
        """
        Refresh access token using refresh token with rotation
        
        Args:
            refresh_token: Valid refresh token
            resource: Optional resource indicator
            
        Returns:
            New TokenContext with fresh access token
            
        Raises:
            TokenError: If refresh token is invalid
        """
        # Validate refresh token
        refresh_data = self.refresh_tokens.get(refresh_token)
        if not refresh_data:
            raise TokenError("Invalid refresh token")
        
        if refresh_data["used"]:
            # Refresh token reuse detected - revoke all tokens
            logger.warning(f"Refresh token reuse detected for client {refresh_data['client_id']}")
            self._revoke_all_client_tokens(refresh_data["client_id"], refresh_data["user_id"])
            raise TokenError("Refresh token already used")
        
        if datetime.now(timezone.utc) >= refresh_data["expires_at"]:
            raise TokenError("Refresh token has expired")
        
        # Mark refresh token as used
        refresh_data["used"] = True
        
        # Revoke old access token
        old_jti = refresh_data["access_token_jti"]
        if old_jti in self.active_tokens:
            del self.active_tokens[old_jti]
        
        # Create new access token
        new_token_context = self.create_access_token(
            client_id=refresh_data["client_id"],
            user_id=refresh_data["user_id"],
            resource=resource
        )
        
        # Create new refresh token (refresh token rotation)
        new_refresh_token = self.create_refresh_token(
            client_id=refresh_data["client_id"],
            user_id=refresh_data["user_id"],
            access_token_jti=new_token_context.metadata["jti"]
        )
        
        new_token_context.refresh_token = new_refresh_token
        
        # Remove old refresh token
        del self.refresh_tokens[refresh_token]
        
        logger.info(f"Access token refreshed for client {refresh_data['client_id']}")
        return new_token_context
    
    def revoke_token(self, token: str) -> bool:
        """
        Revoke access or refresh token
        
        Args:
            token: Token to revoke
            
        Returns:
            True if token was revoked, False if not found
        """
        # Try to decode as access token
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=["HS256"],
                options={"verify_signature": False}
            )
            
            jti = payload.get("jti")
            if jti and jti in self.active_tokens:
                return self._revoke_token(jti)
                
        except jwt.InvalidTokenError:
            pass  # Not a JWT, might be refresh token
        
        # Try as refresh token
        if token in self.refresh_tokens:
            del self.refresh_tokens[token]
            logger.info("Refresh token revoked")
            return True
        
        return False
    
    def introspect_token(self, token: str) -> Dict[str, Any]:
        """
        Introspect token (RFC 7662 style)
        
        Args:
            token: Token to introspect
            
        Returns:
            Token introspection response
        """
        try:
            token_context = self.validate_access_token(token)
            
            # Decode token for additional info
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=["HS256"]
            )
            
            return {
                "active": True,
                "client_id": token_context.client_id,
                "username": token_context.user_id,
                "scope": token_context.scope,
                "resource": token_context.resource,
                "exp": payload.get("exp"),
                "iat": payload.get("iat"),
                "iss": payload.get("iss"),
                "sub": payload.get("sub"),
                "aud": payload.get("aud"),
                "token_type": "access_token"
            }
            
        except TokenError:
            return {"active": False}
    
    def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired tokens from memory
        
        Returns:
            Number of tokens cleaned up
        """
        now = datetime.now(timezone.utc)
        cleaned_count = 0
        
        # Clean up expired access tokens
        expired_jtis = []
        for jti, token_context in self.active_tokens.items():
            if now >= token_context.issued_at + timedelta(seconds=token_context.expires_in):
                expired_jtis.append(jti)
        
        for jti in expired_jtis:
            del self.active_tokens[jti]
            cleaned_count += 1
        
        # Clean up expired refresh tokens
        expired_refresh_tokens = []
        for refresh_token, data in self.refresh_tokens.items():
            if now >= data["expires_at"]:
                expired_refresh_tokens.append(refresh_token)
        
        for refresh_token in expired_refresh_tokens:
            del self.refresh_tokens[refresh_token]
            cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired tokens")
        
        return cleaned_count
    
    def _generate_token_id(self) -> str:
        """Generate unique token ID (JTI)"""
        return secrets.token_urlsafe(32)
    
    def _generate_secure_token(self) -> str:
        """Generate cryptographically secure token"""
        return secrets.token_urlsafe(64)
    
    def _revoke_token(self, jti: str) -> bool:
        """Revoke access token by JTI"""
        if jti in self.active_tokens:
            del self.active_tokens[jti]
            logger.info(f"Access token revoked: {jti}")
            return True
        return False
    
    def _revoke_all_client_tokens(self, client_id: str, user_id: str) -> None:
        """Revoke all tokens for a client/user combination"""
        # Revoke access tokens
        jtis_to_remove = []
        for jti, token_context in self.active_tokens.items():
            if token_context.client_id == client_id and token_context.user_id == user_id:
                jtis_to_remove.append(jti)
        
        for jti in jtis_to_remove:
            del self.active_tokens[jti]
        
        # Revoke refresh tokens
        refresh_tokens_to_remove = []
        for refresh_token, data in self.refresh_tokens.items():
            if data["client_id"] == client_id and data["user_id"] == user_id:
                refresh_tokens_to_remove.append(refresh_token)
        
        for refresh_token in refresh_tokens_to_remove:
            del self.refresh_tokens[refresh_token]
        
        logger.warning(f"Revoked all tokens for client {client_id}, user {user_id}")

# Convenience functions

def create_token_manager(secret_key: str, **kwargs) -> TokenManager:
    """Create token manager with secure defaults"""
    return TokenManager(
        secret_key=secret_key,
        default_token_expiry=kwargs.get('token_expiry', 3600),  # 1 hour
        refresh_token_expiry=kwargs.get('refresh_expiry', 7200),  # 2 hours
        issuer=kwargs.get('issuer', 'mcp-personal-assistant')
    )