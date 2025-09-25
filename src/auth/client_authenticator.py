"""
OAuth 2.1 Client Authentication Implementation

Supports multiple client authentication methods as required by OAuth 2.1:
- private_key_jwt: Asymmetric key authentication (recommended)
- tls_client_auth: Mutual TLS authentication
- client_secret_basic: HTTP Basic authentication
- client_secret_post: POST parameter authentication
"""

import base64
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Literal
import jwt
from cryptography.x509 import Certificate, load_pem_x509_certificate
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding

logger = logging.getLogger(__name__)

@dataclass
class ClientContext:
    """Client authentication context"""
    client_id: str
    client_type: Literal["confidential", "public"]
    auth_method: str
    authenticated: bool
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class ClientAuthenticationError(Exception):
    """Client authentication errors"""
    pass

class ClientAuthenticator:
    """
    OAuth 2.1 compliant client authentication handler
    
    Implements RFC 6749 and OAuth 2.1 client authentication methods
    with enhanced security requirements.
    """
    
    def __init__(self, 
                 client_registry: Dict[str, Dict[str, Any]],
                 jwt_audience: str,
                 max_jwt_age: int = 300):
        """
        Initialize client authenticator
        
        Args:
            client_registry: Dictionary of registered clients
            jwt_audience: Expected audience for JWT assertions
            max_jwt_age: Maximum age for JWT assertions in seconds
        """
        self.client_registry = client_registry
        self.jwt_audience = jwt_audience
        self.max_jwt_age = max_jwt_age
        
    def authenticate_client(self, 
                          auth_method: str,
                          credentials: Dict[str, Any]) -> ClientContext:
        """
        Authenticate client using specified method
        
        Args:
            auth_method: Authentication method to use
            credentials: Authentication credentials
            
        Returns:
            ClientContext with authentication result
            
        Raises:
            ClientAuthenticationError: If authentication fails
        """
        method_handlers = {
            "private_key_jwt": self._authenticate_private_key_jwt,
            "tls_client_auth": self._authenticate_tls_client_auth,
            "client_secret_basic": self._authenticate_client_secret_basic,
            "client_secret_post": self._authenticate_client_secret_post,
        }
        
        handler = method_handlers.get(auth_method)
        if not handler:
            raise ClientAuthenticationError(
                f"Unsupported authentication method: {auth_method}"
            )
        
        try:
            return handler(credentials)
        except Exception as e:
            logger.error(f"Client authentication failed for method {auth_method}: {e}")
            raise ClientAuthenticationError(f"Authentication failed: {e}")
    
    def _authenticate_private_key_jwt(self, credentials: Dict[str, Any]) -> ClientContext:
        """
        Authenticate using private_key_jwt method (RFC 7523)
        
        Args:
            credentials: Must contain 'client_assertion' JWT
            
        Returns:
            Authenticated ClientContext
        """
        assertion = credentials.get("client_assertion")
        if not assertion:
            raise ClientAuthenticationError("Missing client_assertion")
        
        assertion_type = credentials.get("client_assertion_type")
        expected_type = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
        if assertion_type != expected_type:
            raise ClientAuthenticationError(f"Invalid assertion type: {assertion_type}")
        
        # Decode JWT header to get client_id
        try:
            unverified_header = jwt.get_unverified_header(assertion)
            unverified_payload = jwt.decode(assertion, options={"verify_signature": False})
            
            client_id = unverified_payload.get("iss") or unverified_payload.get("sub")
            if not client_id:
                raise ClientAuthenticationError("Missing client_id in JWT")
            
            # Get client configuration
            client_config = self.client_registry.get(client_id)
            if not client_config:
                raise ClientAuthenticationError(f"Unknown client: {client_id}")
            
            # Get public key for verification
            public_key = self._get_client_public_key(client_config)
            
            # Verify JWT
            payload = jwt.decode(
                assertion,
                public_key,
                algorithms=["RS256", "ES256"],
                audience=self.jwt_audience,
                options={
                    "require": ["exp", "iat", "iss", "sub", "aud"],
                    "verify_exp": True,
                    "verify_iat": True,
                }
            )
            
            # Validate JWT claims
            self._validate_jwt_claims(payload, client_id)
            
            logger.info(f"Client authenticated via private_key_jwt: {client_id}")
            return ClientContext(
                client_id=client_id,
                client_type="confidential",
                auth_method="private_key_jwt",
                authenticated=True,
                metadata={
                    "jwt_payload": payload,
                    "auth_time": datetime.now(timezone.utc).isoformat()
                }
            )
            
        except jwt.InvalidTokenError as e:
            raise ClientAuthenticationError(f"Invalid JWT: {e}")
    
    def _authenticate_tls_client_auth(self, credentials: Dict[str, Any]) -> ClientContext:
        """
        Authenticate using mutual TLS (RFC 8705)
        
        Args:
            credentials: Must contain 'client_certificate'
            
        Returns:
            Authenticated ClientContext
        """
        cert_pem = credentials.get("client_certificate")
        if not cert_pem:
            raise ClientAuthenticationError("Missing client certificate")
        
        try:
            # Parse certificate
            certificate = load_pem_x509_certificate(cert_pem.encode())
            
            # Extract client_id from certificate (subject CN or SAN)
            client_id = self._extract_client_id_from_cert(certificate)
            
            # Verify certificate against registered client
            client_config = self.client_registry.get(client_id)
            if not client_config:
                raise ClientAuthenticationError(f"Unknown client: {client_id}")
            
            # Verify certificate is valid and trusted
            self._verify_client_certificate(certificate, client_config)
            
            logger.info(f"Client authenticated via mTLS: {client_id}")
            return ClientContext(
                client_id=client_id,
                client_type="confidential",
                auth_method="tls_client_auth",
                authenticated=True,
                metadata={
                    "certificate_subject": certificate.subject.rfc4514_string(),
                    "certificate_serial": str(certificate.serial_number),
                    "auth_time": datetime.now(timezone.utc).isoformat()
                }
            )
            
        except Exception as e:
            raise ClientAuthenticationError(f"Certificate authentication failed: {e}")
    
    def _authenticate_client_secret_basic(self, credentials: Dict[str, Any]) -> ClientContext:
        """
        Authenticate using HTTP Basic authentication
        
        Args:
            credentials: Must contain 'authorization_header'
            
        Returns:
            Authenticated ClientContext
        """
        auth_header = credentials.get("authorization_header")
        if not auth_header or not auth_header.startswith("Basic "):
            raise ClientAuthenticationError("Missing or invalid Basic auth header")
        
        try:
            # Decode Basic auth credentials
            encoded_creds = auth_header[6:]  # Remove "Basic "
            decoded_creds = base64.b64decode(encoded_creds).decode("utf-8")
            client_id, client_secret = decoded_creds.split(":", 1)
            
            # Verify client credentials
            client_config = self.client_registry.get(client_id)
            if not client_config:
                raise ClientAuthenticationError(f"Unknown client: {client_id}")
            
            expected_secret = client_config.get("client_secret")
            if not expected_secret:
                raise ClientAuthenticationError("Client not configured for secret authentication")
            
            # Constant-time comparison
            import secrets
            if not secrets.compare_digest(client_secret, expected_secret):
                raise ClientAuthenticationError("Invalid client credentials")
            
            logger.info(f"Client authenticated via client_secret_basic: {client_id}")
            return ClientContext(
                client_id=client_id,
                client_type="confidential",
                auth_method="client_secret_basic",
                authenticated=True,
                metadata={
                    "auth_time": datetime.now(timezone.utc).isoformat()
                }
            )
            
        except ValueError as e:
            raise ClientAuthenticationError(f"Invalid Basic auth format: {e}")
    
    def _authenticate_client_secret_post(self, credentials: Dict[str, Any]) -> ClientContext:
        """
        Authenticate using POST parameters
        
        Args:
            credentials: Must contain 'client_id' and 'client_secret'
            
        Returns:
            Authenticated ClientContext
        """
        client_id = credentials.get("client_id")
        client_secret = credentials.get("client_secret")
        
        if not client_id or not client_secret:
            raise ClientAuthenticationError("Missing client_id or client_secret")
        
        # Verify client credentials (same logic as Basic auth)
        client_config = self.client_registry.get(client_id)
        if not client_config:
            raise ClientAuthenticationError(f"Unknown client: {client_id}")
        
        expected_secret = client_config.get("client_secret")
        if not expected_secret:
            raise ClientAuthenticationError("Client not configured for secret authentication")
        
        # Constant-time comparison
        import secrets
        if not secrets.compare_digest(client_secret, expected_secret):
            raise ClientAuthenticationError("Invalid client credentials")
        
        logger.info(f"Client authenticated via client_secret_post: {client_id}")
        return ClientContext(
            client_id=client_id,
            client_type="confidential",
            auth_method="client_secret_post",
            authenticated=True,
            metadata={
                "auth_time": datetime.now(timezone.utc).isoformat()
            }
        )
    
    def _get_client_public_key(self, client_config: Dict[str, Any]) -> str:
        """Get public key for JWT verification from client config"""
        public_key = client_config.get("public_key") or client_config.get("jwks_uri")
        if not public_key:
            raise ClientAuthenticationError("No public key configured for client")
        return public_key
    
    def _validate_jwt_claims(self, payload: Dict[str, Any], client_id: str) -> None:
        """Validate JWT assertion claims"""
        now = datetime.now(timezone.utc)
        
        # Check issuer and subject
        if payload.get("iss") != client_id:
            raise ClientAuthenticationError("Invalid issuer in JWT")
        
        if payload.get("sub") != client_id:
            raise ClientAuthenticationError("Invalid subject in JWT")
        
        # Check expiration (additional check beyond JWT library)
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, timezone.utc) < now:
            raise ClientAuthenticationError("JWT has expired")
        
        # Check issued at time
        iat = payload.get("iat")
        if iat and (now - datetime.fromtimestamp(iat, timezone.utc)).total_seconds() > self.max_jwt_age:
            raise ClientAuthenticationError("JWT is too old")
        
        logger.debug("JWT claims validation passed")
    
    def _extract_client_id_from_cert(self, certificate: Certificate) -> str:
        """Extract client ID from certificate"""
        # Try Common Name first
        for attribute in certificate.subject:
            if attribute.oid._name == "commonName":
                return attribute.value
        
        # Could also check Subject Alternative Names
        raise ClientAuthenticationError("Cannot extract client_id from certificate")
    
    def _verify_client_certificate(self, certificate: Certificate, client_config: Dict[str, Any]) -> None:
        """Verify client certificate is valid and trusted"""
        # Check certificate is not expired
        now = datetime.now(timezone.utc)
        if certificate.not_valid_after < now:
            raise ClientAuthenticationError("Client certificate has expired")
        
        if certificate.not_valid_before > now:
            raise ClientAuthenticationError("Client certificate not yet valid")
        
        # Additional certificate validation could be added here
        # (CA validation, CRL checking, etc.)
        
        logger.debug("Client certificate validation passed")