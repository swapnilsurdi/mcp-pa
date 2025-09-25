"""
Token Validation Service for External Identity Providers

Simplified token validation that focuses on validating tokens from external
providers rather than being a full OAuth 2.1 authorization server.

This is the realistic architecture for MCP servers:
- Users authenticate with Google/Auth0/GitHub/etc.
- MCP server validates these external tokens
- No user login UI needed in MCP server
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timezone

from .external_providers import (
    ExternalProviderRegistry, 
    ExternalUserInfo, 
    TokenValidationError,
    create_google_provider,
    create_auth0_provider,
    create_github_provider
)

logger = logging.getLogger(__name__)

@dataclass 
class MCPUserContext:
    """
    MCP user context derived from external provider
    
    This is what the MCP server uses internally for authorization decisions.
    """
    user_id: str  # Derived from provider + provider_user_id
    email: str
    name: Optional[str] = None
    tenant_id: str = "default"
    provider: str = ""
    provider_user_id: str = ""
    permissions: List[str] = None
    metadata: Dict[str, Any] = None
    authenticated_at: datetime = None
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = ["read", "write"]  # Default permissions
        if self.metadata is None:
            self.metadata = {}
        if self.authenticated_at is None:
            self.authenticated_at = datetime.now(timezone.utc)

class TokenValidationService:
    """
    Token validation service for external identity providers
    
    This service:
    1. Validates tokens from external providers (Google, Auth0, etc.)
    2. Converts external user info to MCP user context
    3. Applies tenant isolation and permission mapping
    4. Provides simple API for MCP server authentication
    """
    
    def __init__(self, 
                 provider_configs: Dict[str, Dict[str, Any]] = None,
                 default_permissions: List[str] = None,
                 tenant_mapping: Optional[Dict[str, str]] = None):
        """
        Initialize token validation service
        
        Args:
            provider_configs: Configuration for external providers
            default_permissions: Default permissions for authenticated users
            tenant_mapping: Optional domain->tenant_id mapping
        """
        self.provider_registry = ExternalProviderRegistry()
        self.default_permissions = default_permissions or ["read", "write"]
        self.tenant_mapping = tenant_mapping or {}
        
        # Initialize configured providers
        if provider_configs:
            self._setup_providers(provider_configs)
        
        logger.info("TokenValidationService initialized")
    
    async def validate_token(self, 
                           token: str, 
                           provider_hint: Optional[str] = None) -> MCPUserContext:
        """
        Validate external token and return MCP user context
        
        Args:
            token: Token from external provider
            provider_hint: Optional hint about which provider issued the token
            
        Returns:
            MCPUserContext for use in MCP server
            
        Raises:
            TokenValidationError: If token validation fails
        """
        try:
            # Validate token with external provider
            external_user = await self.provider_registry.validate_token(
                token=token,
                provider_hint=provider_hint
            )
            
            # Convert to MCP user context
            mcp_user = self._convert_to_mcp_context(external_user)
            
            logger.info(f"Token validated for user: {mcp_user.user_id} ({mcp_user.provider})")
            return mcp_user
            
        except TokenValidationError as e:
            logger.warning(f"Token validation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise TokenValidationError(f"Token validation failed: {e}")
    
    def _convert_to_mcp_context(self, external_user: ExternalUserInfo) -> MCPUserContext:
        """
        Convert external user info to MCP user context
        
        Args:
            external_user: User info from external provider
            
        Returns:
            MCPUserContext for MCP server use
        """
        # Generate consistent user ID
        user_id = f"{external_user.provider}:{external_user.provider_user_id}"
        
        # Determine tenant ID
        tenant_id = self._determine_tenant_id(external_user)
        
        # Determine permissions
        permissions = self._determine_permissions(external_user)
        
        return MCPUserContext(
            user_id=user_id,
            email=external_user.email,
            name=external_user.name,
            tenant_id=tenant_id,
            provider=external_user.provider,
            provider_user_id=external_user.provider_user_id,
            permissions=permissions,
            metadata={
                "email_verified": external_user.email_verified,
                "picture": external_user.picture,
                "raw_provider_claims": external_user.raw_claims
            }
        )
    
    def _determine_tenant_id(self, external_user: ExternalUserInfo) -> str:
        """
        Determine tenant ID for user
        
        Args:
            external_user: External user information
            
        Returns:
            Tenant ID string
        """
        # Use explicit tenant mapping if configured
        if external_user.email:
            domain = external_user.email.split("@")[-1] if "@" in external_user.email else "default"
            if domain in self.tenant_mapping:
                return self.tenant_mapping[domain]
        
        # Use provider-generated tenant ID if available
        if external_user.tenant_id:
            return external_user.tenant_id
        
        # Fall back to provider-based tenant
        return f"{external_user.provider}_users"
    
    def _determine_permissions(self, external_user: ExternalUserInfo) -> List[str]:
        """
        Determine permissions for user
        
        Args:
            external_user: External user information
            
        Returns:
            List of permission strings
        """
        permissions = self.default_permissions.copy()
        
        # Add provider-specific permissions
        if external_user.provider == "github":
            permissions.append("developer")
        
        # Add admin permissions for specific domains (example)
        if external_user.email:
            domain = external_user.email.split("@")[-1] if "@" in external_user.email else ""
            if domain in ["mycompany.com", "admin.example.com"]:
                permissions.append("admin")
        
        return list(set(permissions))  # Remove duplicates
    
    def _setup_providers(self, provider_configs: Dict[str, Dict[str, Any]]) -> None:
        """
        Setup external providers from configuration
        
        Args:
            provider_configs: Provider configuration dictionary
        """
        for provider_name, config in provider_configs.items():
            try:
                if provider_name == "google" and config.get("enabled", False):
                    provider = create_google_provider(
                        client_id=config["client_id"],
                        client_secret=config.get("client_secret")
                    )
                    self.provider_registry.register_provider(provider)
                    
                elif provider_name == "auth0" and config.get("enabled", False):
                    provider = create_auth0_provider(
                        domain=config["domain"],
                        audience=config["audience"]
                    )
                    self.provider_registry.register_provider(provider)
                    
                elif provider_name == "github" and config.get("enabled", False):
                    provider = create_github_provider()
                    self.provider_registry.register_provider(provider)
                    
                logger.info(f"Configured provider: {provider_name}")
                
            except Exception as e:
                logger.error(f"Failed to configure provider {provider_name}: {e}")
    
    def get_configured_providers(self) -> List[str]:
        """Get list of configured provider names"""
        return self.provider_registry.list_providers()
    
    def is_provider_configured(self, provider_name: str) -> bool:
        """Check if a specific provider is configured"""
        return provider_name in self.provider_registry.providers

class APIKeyValidator:
    """
    Simple API key validation for service-to-service authentication
    
    This provides a fallback authentication method when OAuth flows
    are not practical (e.g., server-to-server integration).
    """
    
    def __init__(self, api_keys: Dict[str, Dict[str, Any]]):
        """
        Initialize API key validator
        
        Args:
            api_keys: Dictionary mapping API keys to user context data
        """
        self.api_keys = api_keys
        logger.info(f"APIKeyValidator initialized with {len(api_keys)} keys")
    
    def validate_api_key(self, api_key: str) -> MCPUserContext:
        """
        Validate API key and return user context
        
        Args:
            api_key: API key string
            
        Returns:
            MCPUserContext for the API key
            
        Raises:
            TokenValidationError: If API key is invalid
        """
        key_data = self.api_keys.get(api_key)
        if not key_data:
            raise TokenValidationError("Invalid API key")
        
        return MCPUserContext(
            user_id=key_data["user_id"],
            email=key_data.get("email", ""),
            name=key_data.get("name"),
            tenant_id=key_data.get("tenant_id", "api"),
            provider="api_key",
            provider_user_id=key_data["user_id"],
            permissions=key_data.get("permissions", ["read", "write"]),
            metadata={"api_key_name": key_data.get("name", "unnamed")}
        )

# Convenience functions and configuration helpers

def create_token_validator(config: Dict[str, Any]) -> TokenValidationService:
    """
    Create token validation service from configuration
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configured TokenValidationService
    """
    provider_configs = config.get("external_providers", {})
    default_permissions = config.get("default_permissions", ["read", "write"])
    tenant_mapping = config.get("tenant_mapping", {})
    
    return TokenValidationService(
        provider_configs=provider_configs,
        default_permissions=default_permissions,
        tenant_mapping=tenant_mapping
    )

def get_sample_provider_config() -> Dict[str, Any]:
    """
    Get sample configuration for external providers
    
    Returns:
        Sample configuration dictionary
    """
    return {
        "external_providers": {
            "google": {
                "enabled": True,
                "client_id": "your-google-client-id.googleusercontent.com",
                "client_secret": "optional-for-userinfo-access"
            },
            "auth0": {
                "enabled": True,
                "domain": "your-app.auth0.com",
                "audience": "https://your-mcp-api.com"
            },
            "github": {
                "enabled": True
            }
        },
        "default_permissions": ["read", "write"],
        "tenant_mapping": {
            "mycompany.com": "company_tenant",
            "gmail.com": "personal_users",
            "outlook.com": "personal_users"
        },
        "api_keys": {
            "mcp-api-key-123": {
                "user_id": "service-account-1", 
                "email": "service@mycompany.com",
                "name": "Service Account",
                "tenant_id": "service_tenant",
                "permissions": ["read", "write", "admin"]
            }
        }
    }