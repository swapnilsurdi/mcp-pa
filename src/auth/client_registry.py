"""
Dynamic Client Registration for OAuth 2.1 (RFC 7591)

Implements OAuth 2.1 dynamic client registration with MCP-specific extensions:
- Automatic client registration for MCP clients
- Client metadata validation and storage
- Registration access token management
- Client configuration updates
"""

import json
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Literal
from dataclasses import dataclass, asdict
from urllib.parse import urlparse
import uuid

logger = logging.getLogger(__name__)

@dataclass
class ClientRegistration:
    """Client registration data structure"""
    client_id: str
    client_secret: Optional[str] = None
    client_name: str = ""
    client_uri: Optional[str] = None
    redirect_uris: List[str] = None
    grant_types: List[str] = None
    response_types: List[str] = None
    scope: Optional[str] = None
    token_endpoint_auth_method: str = "client_secret_basic"
    contacts: List[str] = None
    logo_uri: Optional[str] = None
    policy_uri: Optional[str] = None
    tos_uri: Optional[str] = None
    software_id: Optional[str] = None
    software_version: Optional[str] = None
    
    # OAuth 2.1 specific
    code_challenge_method: str = "S256"
    
    # MCP specific extensions
    mcp_version: str = "2024-11-05"
    mcp_capabilities: List[str] = None
    
    # Registration metadata
    client_id_issued_at: int = 0
    client_secret_expires_at: int = 0
    registration_client_uri: Optional[str] = None
    registration_access_token: Optional[str] = None
    
    def __post_init__(self):
        if self.redirect_uris is None:
            self.redirect_uris = []
        if self.grant_types is None:
            self.grant_types = ["authorization_code", "refresh_token"]
        if self.response_types is None:
            self.response_types = ["code"]
        if self.contacts is None:
            self.contacts = []
        if self.mcp_capabilities is None:
            self.mcp_capabilities = ["resources", "tools", "prompts"]

class ClientRegistrationError(Exception):
    """Client registration specific errors"""
    def __init__(self, error: str, description: str = ""):
        self.error = error
        self.description = description
        super().__init__(f"{error}: {description}")

class DynamicClientRegistry:
    """
    RFC 7591 compliant dynamic client registration
    
    Features:
    - OAuth 2.1 compliance with PKCE requirements
    - MCP-specific client metadata
    - Automatic client validation
    - Registration access tokens for updates
    """
    
    def __init__(self,
                 issuer: str,
                 default_scope: str = "read write",
                 client_secret_expiry: int = 7776000,  # 90 days
                 registration_token_expiry: int = 86400):  # 24 hours
        """
        Initialize dynamic client registry
        
        Args:
            issuer: OAuth issuer URI
            default_scope: Default scope for registered clients
            client_secret_expiry: Client secret expiry in seconds
            registration_token_expiry: Registration access token expiry
        """
        self.issuer = issuer
        self.default_scope = default_scope
        self.client_secret_expiry = client_secret_expiry
        self.registration_token_expiry = registration_token_expiry
        
        # Client storage (use database in production)
        self.registered_clients: Dict[str, ClientRegistration] = {}
        self.registration_tokens: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"DynamicClientRegistry initialized for issuer: {issuer}")
    
    def register_client(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register new OAuth 2.1 client (RFC 7591)
        
        Args:
            request_data: Client registration request
            
        Returns:
            Client registration response
            
        Raises:
            ClientRegistrationError: If registration fails
        """
        try:
            # Validate registration request
            validated_data = self._validate_registration_request(request_data)
            
            # Generate client credentials
            client_id = self._generate_client_id()
            client_secret = None
            client_secret_expires_at = 0
            
            # Determine if client needs secret
            auth_method = validated_data.get("token_endpoint_auth_method", "client_secret_basic")
            if auth_method in ["client_secret_basic", "client_secret_post"]:
                client_secret = self._generate_client_secret()
                client_secret_expires_at = int(
                    (datetime.now(timezone.utc) + timedelta(seconds=self.client_secret_expiry)).timestamp()
                )
            
            # Create registration
            now_timestamp = int(datetime.now(timezone.utc).timestamp())
            
            client_registration = ClientRegistration(
                client_id=client_id,
                client_secret=client_secret,
                client_name=validated_data.get("client_name", ""),
                client_uri=validated_data.get("client_uri"),
                redirect_uris=validated_data["redirect_uris"],
                grant_types=validated_data.get("grant_types", ["authorization_code"]),
                response_types=validated_data.get("response_types", ["code"]),
                scope=validated_data.get("scope", self.default_scope),
                token_endpoint_auth_method=auth_method,
                contacts=validated_data.get("contacts", []),
                logo_uri=validated_data.get("logo_uri"),
                policy_uri=validated_data.get("policy_uri"),
                tos_uri=validated_data.get("tos_uri"),
                software_id=validated_data.get("software_id"),
                software_version=validated_data.get("software_version"),
                mcp_version=validated_data.get("mcp_version", "2024-11-05"),
                mcp_capabilities=validated_data.get("mcp_capabilities", ["resources", "tools", "prompts"]),
                client_id_issued_at=now_timestamp,
                client_secret_expires_at=client_secret_expires_at
            )
            
            # Generate registration access token
            registration_token = self._generate_registration_token()
            client_registration.registration_access_token = registration_token
            client_registration.registration_client_uri = f"{self.issuer}/oauth/register/{client_id}"
            
            # Store registration
            self.registered_clients[client_id] = client_registration
            self._store_registration_token(registration_token, client_id)
            
            # Build response
            response = self._build_registration_response(client_registration)
            
            logger.info(f"Client registered: {client_id}")
            return response
            
        except Exception as e:
            if isinstance(e, ClientRegistrationError):
                raise
            logger.error(f"Client registration failed: {e}")
            raise ClientRegistrationError("server_error", "Internal registration error")
    
    def get_client(self, client_id: str) -> Optional[ClientRegistration]:
        """
        Get registered client by ID
        
        Args:
            client_id: Client identifier
            
        Returns:
            ClientRegistration if found, None otherwise
        """
        return self.registered_clients.get(client_id)
    
    def update_client(self, 
                     client_id: str,
                     registration_token: str, 
                     update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update existing client registration
        
        Args:
            client_id: Client identifier
            registration_token: Registration access token
            update_data: Client update data
            
        Returns:
            Updated client registration response
            
        Raises:
            ClientRegistrationError: If update fails
        """
        # Validate registration access token
        if not self._validate_registration_token(registration_token, client_id):
            raise ClientRegistrationError("invalid_token", "Invalid registration access token")
        
        # Get existing registration
        client_registration = self.registered_clients.get(client_id)
        if not client_registration:
            raise ClientRegistrationError("invalid_client_id", "Client not found")
        
        try:
            # Validate update data
            validated_data = self._validate_registration_request(update_data, is_update=True)
            
            # Update fields
            for field, value in validated_data.items():
                if hasattr(client_registration, field):
                    setattr(client_registration, field, value)
            
            # Store updated registration
            self.registered_clients[client_id] = client_registration
            
            response = self._build_registration_response(client_registration)
            
            logger.info(f"Client updated: {client_id}")
            return response
            
        except Exception as e:
            if isinstance(e, ClientRegistrationError):
                raise
            logger.error(f"Client update failed: {e}")
            raise ClientRegistrationError("server_error", "Internal update error")
    
    def delete_client(self, client_id: str, registration_token: str) -> bool:
        """
        Delete client registration
        
        Args:
            client_id: Client identifier
            registration_token: Registration access token
            
        Returns:
            True if deleted successfully
            
        Raises:
            ClientRegistrationError: If deletion fails
        """
        # Validate registration access token
        if not self._validate_registration_token(registration_token, client_id):
            raise ClientRegistrationError("invalid_token", "Invalid registration access token")
        
        # Remove client and token
        if client_id in self.registered_clients:
            del self.registered_clients[client_id]
            
        # Clean up registration tokens
        for token, data in list(self.registration_tokens.items()):
            if data.get("client_id") == client_id:
                del self.registration_tokens[token]
        
        logger.info(f"Client deleted: {client_id}")
        return True
    
    def list_clients(self) -> List[Dict[str, Any]]:
        """
        List all registered clients (admin function)
        
        Returns:
            List of client summaries
        """
        clients = []
        for client_id, registration in self.registered_clients.items():
            clients.append({
                "client_id": client_id,
                "client_name": registration.client_name,
                "issued_at": registration.client_id_issued_at,
                "scope": registration.scope,
                "grant_types": registration.grant_types
            })
        return clients
    
    def _validate_registration_request(self, 
                                     data: Dict[str, Any], 
                                     is_update: bool = False) -> Dict[str, Any]:
        """
        Validate client registration request data
        
        Args:
            data: Registration request data
            is_update: Whether this is an update request
            
        Returns:
            Validated request data
            
        Raises:
            ClientRegistrationError: If validation fails
        """
        validated = {}
        
        # Redirect URIs (required for new registrations)
        redirect_uris = data.get("redirect_uris")
        if not is_update and not redirect_uris:
            raise ClientRegistrationError("invalid_redirect_uri", "redirect_uris is required")
        
        if redirect_uris:
            if not isinstance(redirect_uris, list):
                raise ClientRegistrationError("invalid_redirect_uri", "redirect_uris must be array")
            
            validated_uris = []
            for uri in redirect_uris:
                parsed = urlparse(uri)
                if not parsed.scheme or not parsed.netloc:
                    raise ClientRegistrationError("invalid_redirect_uri", f"Invalid URI: {uri}")
                
                # OAuth 2.1 requires HTTPS for redirect URIs (except localhost)
                if parsed.scheme != "https" and parsed.hostname not in ["localhost", "127.0.0.1"]:
                    raise ClientRegistrationError(
                        "invalid_redirect_uri",
                        f"OAuth 2.1 requires HTTPS redirect URIs: {uri}"
                    )
                
                validated_uris.append(uri)
            
            validated["redirect_uris"] = validated_uris
        
        # Grant types (must be OAuth 2.1 compliant)
        grant_types = data.get("grant_types", ["authorization_code"])
        invalid_grants = set(grant_types) - {"authorization_code", "refresh_token"}
        if invalid_grants:
            raise ClientRegistrationError(
                "invalid_client_metadata",
                f"OAuth 2.1 only supports authorization_code and refresh_token: {invalid_grants}"
            )
        validated["grant_types"] = grant_types
        
        # Response types (must be 'code' for OAuth 2.1)
        response_types = data.get("response_types", ["code"])
        if response_types != ["code"]:
            raise ClientRegistrationError(
                "invalid_client_metadata",
                "OAuth 2.1 only supports 'code' response type"
            )
        validated["response_types"] = response_types
        
        # Token endpoint auth method
        auth_method = data.get("token_endpoint_auth_method", "client_secret_basic")
        valid_methods = [
            "client_secret_basic",
            "client_secret_post", 
            "private_key_jwt",
            "tls_client_auth",
            "none"
        ]
        if auth_method not in valid_methods:
            raise ClientRegistrationError(
                "invalid_client_metadata",
                f"Invalid token_endpoint_auth_method: {auth_method}"
            )
        validated["token_endpoint_auth_method"] = auth_method
        
        # Optional string fields
        string_fields = [
            "client_name", "client_uri", "scope", "logo_uri", 
            "policy_uri", "tos_uri", "software_id", "software_version"
        ]
        for field in string_fields:
            value = data.get(field)
            if value:
                if not isinstance(value, str):
                    raise ClientRegistrationError(
                        "invalid_client_metadata",
                        f"{field} must be string"
                    )
                validated[field] = value
        
        # Contacts (array of strings)
        contacts = data.get("contacts")
        if contacts:
            if not isinstance(contacts, list):
                raise ClientRegistrationError("invalid_client_metadata", "contacts must be array")
            
            for contact in contacts:
                if not isinstance(contact, str):
                    raise ClientRegistrationError(
                        "invalid_client_metadata",
                        "contacts must be array of strings"
                    )
            validated["contacts"] = contacts
        
        # MCP-specific metadata
        mcp_version = data.get("mcp_version", "2024-11-05")
        validated["mcp_version"] = mcp_version
        
        mcp_capabilities = data.get("mcp_capabilities", ["resources", "tools", "prompts"])
        if not isinstance(mcp_capabilities, list):
            raise ClientRegistrationError(
                "invalid_client_metadata",
                "mcp_capabilities must be array"
            )
        validated["mcp_capabilities"] = mcp_capabilities
        
        return validated
    
    def _generate_client_id(self) -> str:
        """Generate unique client ID"""
        return f"mcp-client-{uuid.uuid4().hex[:16]}"
    
    def _generate_client_secret(self) -> str:
        """Generate client secret"""
        return secrets.token_urlsafe(32)
    
    def _generate_registration_token(self) -> str:
        """Generate registration access token"""
        return secrets.token_urlsafe(32)
    
    def _store_registration_token(self, token: str, client_id: str) -> None:
        """Store registration access token"""
        self.registration_tokens[token] = {
            "client_id": client_id,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=self.registration_token_expiry)
        }
    
    def _validate_registration_token(self, token: str, client_id: str) -> bool:
        """Validate registration access token"""
        token_data = self.registration_tokens.get(token)
        if not token_data:
            return False
        
        if token_data["client_id"] != client_id:
            return False
        
        if datetime.now(timezone.utc) > token_data["expires_at"]:
            del self.registration_tokens[token]
            return False
        
        return True
    
    def _build_registration_response(self, registration: ClientRegistration) -> Dict[str, Any]:
        """Build client registration response"""
        response = {
            "client_id": registration.client_id,
            "client_name": registration.client_name,
            "redirect_uris": registration.redirect_uris,
            "grant_types": registration.grant_types,
            "response_types": registration.response_types,
            "token_endpoint_auth_method": registration.token_endpoint_auth_method,
            "scope": registration.scope,
            "client_id_issued_at": registration.client_id_issued_at
        }
        
        # Add client secret if present
        if registration.client_secret:
            response["client_secret"] = registration.client_secret
            response["client_secret_expires_at"] = registration.client_secret_expires_at
        
        # Add optional fields
        optional_fields = [
            "client_uri", "logo_uri", "policy_uri", "tos_uri",
            "contacts", "software_id", "software_version"
        ]
        for field in optional_fields:
            value = getattr(registration, field)
            if value:
                response[field] = value
        
        # Add registration management
        if registration.registration_access_token:
            response["registration_access_token"] = registration.registration_access_token
            response["registration_client_uri"] = registration.registration_client_uri
        
        # Add MCP-specific metadata
        response["mcp_version"] = registration.mcp_version
        response["mcp_capabilities"] = registration.mcp_capabilities
        
        return response

# Convenience functions

def create_client_registry(issuer: str) -> DynamicClientRegistry:
    """Create client registry with default configuration"""
    return DynamicClientRegistry(issuer=issuer)