"""
OAuth 2.1 Discovery Service Implementation

Implements RFC 8414 (OAuth 2.0 Authorization Server Metadata) and
RFC 9728 (OAuth 2.0 Protected Resource Metadata) for MCP compliance.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class DiscoveryService:
    """
    OAuth 2.1 Discovery Service for MCP Authorization
    
    Provides metadata endpoints as required by:
    - RFC 8414: Authorization Server Metadata
    - RFC 9728: Protected Resource Metadata
    - MCP Authorization Specification
    """
    
    def __init__(self,
                 issuer: str,
                 supported_scopes: List[str] = None,
                 supported_resources: List[str] = None):
        """
        Initialize discovery service
        
        Args:
            issuer: Authorization server issuer URL
            supported_scopes: List of supported OAuth scopes
            supported_resources: List of supported resource indicators
        """
        self.issuer = issuer.rstrip('/')
        self.supported_scopes = supported_scopes or ["read", "write", "admin"]
        self.supported_resources = supported_resources or []
        
        logger.info(f"DiscoveryService initialized for issuer: {self.issuer}")
    
    def get_authorization_server_metadata(self) -> Dict[str, Any]:
        """
        OAuth 2.0 Authorization Server Metadata (RFC 8414)
        
        Available at: /.well-known/oauth-authorization-server
        """
        metadata = {
            # Core OAuth 2.1 metadata
            "issuer": self.issuer,
            "authorization_endpoint": f"{self.issuer}/oauth/authorize",
            "token_endpoint": f"{self.issuer}/oauth/token",
            "revocation_endpoint": f"{self.issuer}/oauth/revoke",
            "introspection_endpoint": f"{self.issuer}/oauth/introspect",
            
            # OAuth 2.1 specific requirements
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256", "plain"],
            
            # Token endpoint authentication
            "token_endpoint_auth_methods_supported": [
                "client_secret_basic",
                "client_secret_post",
                "private_key_jwt",
                "tls_client_auth",
                "none"  # For public clients with PKCE
            ],
            "token_endpoint_auth_signing_alg_values_supported": [
                "HS256", "HS384", "HS512",
                "RS256", "RS384", "RS512", 
                "ES256", "ES384", "ES512"
            ],
            
            # Scopes and capabilities
            "scopes_supported": self.supported_scopes,
            "response_modes_supported": ["query", "fragment"],
            "subject_types_supported": ["public"],
            
            # Security features
            "require_signed_request_object": False,
            "require_request_uri_registration": False,
            
            # MCP specific extensions
            "resource_indicators_supported": True,
            "pkce_required": True,
            "dynamic_client_registration_supported": True,
            
            # Additional endpoints
            "registration_endpoint": f"{self.issuer}/oauth/register",
            "jwks_uri": f"{self.issuer}/.well-known/jwks.json",
            
            # Metadata
            "service_documentation": f"{self.issuer}/docs",
            "op_policy_uri": f"{self.issuer}/policy",
            "op_tos_uri": f"{self.issuer}/terms"
        }
        
        # Add resource-specific metadata if resources are defined
        if self.supported_resources:
            metadata["resource_indicators_supported"] = True
            metadata["resources_supported"] = self.supported_resources
        
        logger.debug("Generated authorization server metadata")
        return metadata
    
    def get_protected_resource_metadata(self, resource_uri: str) -> Dict[str, Any]:
        """
        OAuth 2.0 Protected Resource Metadata (RFC 9728)
        
        Available at: /.well-known/oauth-protected-resource
        """
        metadata = {
            # Core resource metadata
            "resource": resource_uri,
            "authorization_servers": [self.issuer],
            
            # Bearer token requirements
            "bearer_methods_supported": ["header"],  # Authorization: Bearer <token>
            "resource_signing_alg_values_supported": ["HS256", "RS256"],
            
            # Scopes required for this resource
            "scopes_supported": self.supported_scopes,
            
            # Token requirements
            "bearer_token_type": "Bearer",
            
            # MCP specific requirements
            "mcp_version_supported": ["2024-11-05"],
            "mcp_capabilities": [
                "resources",
                "tools", 
                "prompts",
                "logging"
            ],
            
            # Resource-specific metadata
            "resource_documentation": f"{resource_uri}/docs",
            "resource_policy_uri": f"{resource_uri}/policy"
        }
        
        logger.debug(f"Generated protected resource metadata for: {resource_uri}")
        return metadata
    
    def get_jwks(self, public_keys: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        JSON Web Key Set (JWKS) for token verification
        
        Available at: /.well-known/jwks.json
        
        Args:
            public_keys: List of public key dictionaries in JWK format
        """
        jwks = {
            "keys": public_keys
        }
        
        logger.debug(f"Generated JWKS with {len(public_keys)} keys")
        return jwks
    
    def get_openid_configuration(self) -> Dict[str, Any]:
        """
        OpenID Connect Discovery metadata (if OIDC is supported)
        
        Available at: /.well-known/openid_configuration
        """
        # Start with OAuth metadata
        metadata = self.get_authorization_server_metadata()
        
        # Add OpenID Connect specific metadata
        oidc_metadata = {
            "userinfo_endpoint": f"{self.issuer}/oauth/userinfo",
            "id_token_signing_alg_values_supported": ["HS256", "RS256"],
            "subject_types_supported": ["public"],
            "response_types_supported": ["code", "id_token", "code id_token"],
            "claims_supported": [
                "sub", "iss", "aud", "exp", "iat", "auth_time",
                "email", "email_verified", "name", "given_name", "family_name"
            ],
            "claim_types_supported": ["normal"],
            "claims_parameter_supported": False,
            "request_parameter_supported": False,
            "request_uri_parameter_supported": False
        }
        
        # Merge OAuth and OIDC metadata
        metadata.update(oidc_metadata)
        
        logger.debug("Generated OpenID Connect configuration")
        return metadata
    
    def validate_discovery_request(self, 
                                 endpoint: str,
                                 host: str,
                                 scheme: str = "https") -> bool:
        """
        Validate discovery request according to security requirements
        
        Args:
            endpoint: Discovery endpoint path
            host: Request host header
            scheme: Request scheme (should be https)
            
        Returns:
            True if request is valid
        """
        # Ensure HTTPS for production
        if scheme != "https":
            logger.warning(f"Discovery request over {scheme} - HTTPS required")
            return False
        
        # Validate host matches issuer
        issuer_host = self.issuer.split("://")[1].split("/")[0]
        if host != issuer_host:
            logger.warning(f"Host mismatch: {host} vs {issuer_host}")
            return False
        
        # Validate endpoint is a recognized discovery endpoint
        valid_endpoints = [
            "/.well-known/oauth-authorization-server",
            "/.well-known/oauth-protected-resource",
            "/.well-known/openid_configuration",
            "/.well-known/jwks.json"
        ]
        
        if endpoint not in valid_endpoints:
            logger.warning(f"Unknown discovery endpoint: {endpoint}")
            return False
        
        return True
    
    def get_server_capabilities(self) -> Dict[str, Any]:
        """
        Get comprehensive server capabilities for MCP clients
        """
        return {
            # OAuth 2.1 compliance
            "oauth_version": "2.1",
            "pkce_required": True,
            "supported_flows": ["authorization_code"],
            
            # Security features
            "tls_required": True,
            "token_expiry_max": 3600,  # 1 hour
            "refresh_token_rotation": True,
            
            # MCP specific
            "mcp_version": "2024-11-05",
            "resource_indicators": True,
            "multi_tenancy": True,
            
            # Client support
            "dynamic_registration": True,
            "client_authentication_methods": [
                "client_secret_basic",
                "client_secret_post",
                "private_key_jwt", 
                "tls_client_auth"
            ],
            
            # Discovery endpoints
            "discovery_endpoints": {
                "authorization_server": "/.well-known/oauth-authorization-server",
                "protected_resource": "/.well-known/oauth-protected-resource", 
                "openid_configuration": "/.well-known/openid_configuration",
                "jwks": "/.well-known/jwks.json"
            }
        }

# Convenience functions

def create_discovery_service(
    issuer: str,
    scopes: List[str] = None,
    resources: List[str] = None
) -> DiscoveryService:
    """Create discovery service with default configuration"""
    
    default_scopes = ["read", "write", "admin", "mcp:tools", "mcp:resources"]
    default_resources = [issuer, f"{issuer}/mcp"]
    
    return DiscoveryService(
        issuer=issuer,
        supported_scopes=scopes or default_scopes,
        supported_resources=resources or default_resources
    )

def generate_sample_jwk() -> Dict[str, Any]:
    """Generate sample JWK for testing (use proper keys in production)"""
    return {
        "kty": "RSA",
        "use": "sig", 
        "kid": "mcp-key-1",
        "alg": "RS256",
        "n": "sample_modulus_base64url",
        "e": "AQAB"
    }