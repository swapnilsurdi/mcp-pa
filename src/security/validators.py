"""
Input Validation for OAuth 2.1 and MCP Compliance

Provides comprehensive validation for:
- OAuth 2.1 request parameters
- MCP protocol messages
- General input sanitization
- Security parameter validation
"""

import re
import json
import logging
from typing import Dict, Any, Optional, List, Union, Set
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone
import base64

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Input validation error"""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")

class InputValidator:
    """
    General input validation and sanitization
    """
    
    # Common regex patterns
    PATTERNS = {
        "client_id": re.compile(r"^[a-zA-Z0-9._-]{1,64}$"),
        "user_id": re.compile(r"^[a-zA-Z0-9._@-]{1,128}$"),
        "tenant_id": re.compile(r"^[a-zA-Z0-9._-]{1,64}$"),
        "scope": re.compile(r"^[a-zA-Z0-9._: -]+$"),
        "state": re.compile(r"^[a-zA-Z0-9._~-]{1,256}$"),
        "nonce": re.compile(r"^[a-zA-Z0-9._~-]{1,256}$"),
        "email": re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"),
        "url": re.compile(r"^https?://[a-zA-Z0-9.-]+(/.*)?$"),
        "jwt": re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*$"),
        "base64url": re.compile(r"^[A-Za-z0-9_-]+$")
    }
    
    @classmethod
    def validate_string(cls, 
                       value: Any, 
                       field_name: str,
                       pattern: Optional[str] = None,
                       min_length: int = 0,
                       max_length: int = 1000,
                       required: bool = True) -> Optional[str]:
        """
        Validate string input with pattern matching
        
        Args:
            value: Value to validate
            field_name: Name of the field for error messages
            pattern: Regex pattern name or custom pattern
            min_length: Minimum string length
            max_length: Maximum string length
            required: Whether field is required
            
        Returns:
            Validated string or None if optional and empty
            
        Raises:
            ValidationError: If validation fails
        """
        # Handle None/empty values
        if value is None or value == "":
            if required:
                raise ValidationError(field_name, "Field is required")
            return None
        
        # Ensure string type
        if not isinstance(value, str):
            raise ValidationError(field_name, f"Must be string, got {type(value)}")
        
        # Check length
        if len(value) < min_length:
            raise ValidationError(field_name, f"Minimum length {min_length}, got {len(value)}")
        
        if len(value) > max_length:
            raise ValidationError(field_name, f"Maximum length {max_length}, got {len(value)}")
        
        # Pattern validation
        if pattern:
            regex = cls.PATTERNS.get(pattern) or re.compile(pattern)
            if not regex.match(value):
                raise ValidationError(field_name, f"Invalid format for {pattern}")
        
        return value
    
    @classmethod
    def validate_url(cls, url: str, field_name: str, allowed_schemes: List[str] = None) -> str:
        """
        Validate URL format and scheme
        
        Args:
            url: URL to validate
            field_name: Field name for errors
            allowed_schemes: List of allowed schemes (default: ['https'])
            
        Returns:
            Validated URL
            
        Raises:
            ValidationError: If URL is invalid
        """
        if allowed_schemes is None:
            allowed_schemes = ['https']
        
        try:
            parsed = urlparse(url)
            
            if not parsed.scheme:
                raise ValidationError(field_name, "URL missing scheme")
            
            if parsed.scheme not in allowed_schemes:
                raise ValidationError(
                    field_name, 
                    f"URL scheme must be one of {allowed_schemes}, got {parsed.scheme}"
                )
            
            if not parsed.netloc:
                raise ValidationError(field_name, "URL missing hostname")
            
            # Basic hostname validation
            if not re.match(r"^[a-zA-Z0-9.-]+$", parsed.netloc.split(":")[0]):
                raise ValidationError(field_name, "Invalid hostname in URL")
            
            return url
            
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(field_name, f"Invalid URL format: {e}")
    
    @classmethod
    def validate_json(cls, data: Any, field_name: str, schema: Optional[Dict] = None) -> Dict:
        """
        Validate JSON data structure
        
        Args:
            data: Data to validate (string or dict)
            field_name: Field name for errors
            schema: Optional simple schema validation
            
        Returns:
            Parsed JSON data
            
        Raises:
            ValidationError: If JSON is invalid
        """
        # Parse if string
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                raise ValidationError(field_name, f"Invalid JSON: {e}")
        
        if not isinstance(data, dict):
            raise ValidationError(field_name, "Must be JSON object")
        
        # Basic schema validation if provided
        if schema:
            for required_field in schema.get("required", []):
                if required_field not in data:
                    raise ValidationError(field_name, f"Missing required field: {required_field}")
        
        return data
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 1000) -> str:
        """
        Sanitize string input by removing dangerous characters
        
        Args:
            value: String to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            return str(value)
        
        # Remove null bytes and control characters
        sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value)
        
        # Trim whitespace
        sanitized = sanitized.strip()
        
        # Limit length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized

class OAuthValidator:
    """
    OAuth 2.1 specific parameter validation
    """
    
    @classmethod
    def validate_authorization_request(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate OAuth 2.1 authorization request parameters
        
        Args:
            params: Authorization request parameters
            
        Returns:
            Validated parameters
            
        Raises:
            ValidationError: If validation fails
        """
        validated = {}
        
        # Required parameters
        validated["client_id"] = InputValidator.validate_string(
            params.get("client_id"), "client_id", pattern="client_id", required=True
        )
        
        validated["redirect_uri"] = InputValidator.validate_url(
            params.get("redirect_uri"), "redirect_uri", allowed_schemes=["https", "http"]
        )
        
        # OAuth 2.1 requires PKCE
        validated["code_challenge"] = InputValidator.validate_string(
            params.get("code_challenge"), "code_challenge", 
            pattern="base64url", min_length=43, max_length=128, required=True
        )
        
        validated["code_challenge_method"] = InputValidator.validate_string(
            params.get("code_challenge_method"), "code_challenge_method", required=True
        )
        
        if validated["code_challenge_method"] not in ["S256", "plain"]:
            raise ValidationError(
                "code_challenge_method", 
                "Must be 'S256' or 'plain'"
            )
        
        # Optional parameters
        validated["scope"] = InputValidator.validate_string(
            params.get("scope"), "scope", pattern="scope", required=False
        )
        
        validated["state"] = InputValidator.validate_string(
            params.get("state"), "state", pattern="state", required=False
        )
        
        # Resource indicators (RFC 8707)
        validated["resource"] = InputValidator.validate_url(
            params.get("resource"), "resource", allowed_schemes=["https"]
        ) if params.get("resource") else None
        
        # Response type must be 'code' for OAuth 2.1
        response_type = params.get("response_type")
        if response_type != "code":
            raise ValidationError(
                "response_type",
                "OAuth 2.1 only supports 'code' response type"
            )
        validated["response_type"] = response_type
        
        return validated
    
    @classmethod
    def validate_token_request(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate OAuth 2.1 token request parameters
        
        Args:
            params: Token request parameters
            
        Returns:
            Validated parameters
            
        Raises:
            ValidationError: If validation fails
        """
        validated = {}
        
        # Grant type
        grant_type = params.get("grant_type")
        if grant_type not in ["authorization_code", "refresh_token"]:
            raise ValidationError(
                "grant_type",
                "OAuth 2.1 only supports 'authorization_code' and 'refresh_token'"
            )
        validated["grant_type"] = grant_type
        
        if grant_type == "authorization_code":
            # Authorization code grant parameters
            validated["code"] = InputValidator.validate_string(
                params.get("code"), "code", pattern="base64url", required=True
            )
            
            validated["redirect_uri"] = InputValidator.validate_url(
                params.get("redirect_uri"), "redirect_uri", required=True
            )
            
            # PKCE code verifier (required in OAuth 2.1)
            validated["code_verifier"] = InputValidator.validate_string(
                params.get("code_verifier"), "code_verifier",
                min_length=43, max_length=128, required=True
            )
            
            # Validate code verifier characters
            if not re.match(r"^[A-Za-z0-9._~-]+$", validated["code_verifier"]):
                raise ValidationError(
                    "code_verifier",
                    "Invalid characters in code verifier"
                )
        
        elif grant_type == "refresh_token":
            # Refresh token grant parameters
            validated["refresh_token"] = InputValidator.validate_string(
                params.get("refresh_token"), "refresh_token", required=True
            )
        
        # Optional resource indicator
        validated["resource"] = InputValidator.validate_url(
            params.get("resource"), "resource", required=False
        ) if params.get("resource") else None
        
        return validated
    
    @classmethod
    def validate_client_credentials(cls, auth_header: str = None, **form_params) -> Dict[str, Any]:
        """
        Validate client authentication credentials
        
        Args:
            auth_header: Authorization header value
            **form_params: Form parameters for client credentials
            
        Returns:
            Validated client authentication data
            
        Raises:
            ValidationError: If validation fails
        """
        if auth_header and auth_header.startswith("Basic "):
            # HTTP Basic authentication
            try:
                encoded = auth_header[6:]  # Remove "Basic "
                decoded = base64.b64decode(encoded).decode("utf-8")
                client_id, client_secret = decoded.split(":", 1)
                
                return {
                    "method": "client_secret_basic",
                    "credentials": {
                        "client_id": InputValidator.validate_string(
                            client_id, "client_id", pattern="client_id"
                        ),
                        "client_secret": client_secret
                    }
                }
            except Exception as e:
                raise ValidationError("authorization", f"Invalid Basic auth: {e}")
        
        elif form_params.get("client_assertion_type"):
            # JWT client assertion
            assertion_type = form_params.get("client_assertion_type")
            if assertion_type != "urn:ietf:params:oauth:client-assertion-type:jwt-bearer":
                raise ValidationError("client_assertion_type", "Invalid assertion type")
            
            return {
                "method": "private_key_jwt",
                "credentials": {
                    "client_assertion": InputValidator.validate_string(
                        form_params.get("client_assertion"), "client_assertion", 
                        pattern="jwt", required=True
                    ),
                    "client_assertion_type": assertion_type
                }
            }
        
        elif form_params.get("client_id") and form_params.get("client_secret"):
            # POST parameters
            return {
                "method": "client_secret_post",
                "credentials": {
                    "client_id": InputValidator.validate_string(
                        form_params.get("client_id"), "client_id", pattern="client_id"
                    ),
                    "client_secret": form_params.get("client_secret")
                }
            }
        
        else:
            raise ValidationError("client_auth", "No valid client authentication method found")

class MCPValidator:
    """
    MCP protocol message validation
    """
    
    @classmethod
    def validate_mcp_request(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate MCP request message
        
        Args:
            data: MCP request data
            
        Returns:
            Validated MCP request
            
        Raises:
            ValidationError: If validation fails
        """
        validated = {}
        
        # Method is required
        validated["method"] = InputValidator.validate_string(
            data.get("method"), "method", required=True
        )
        
        # Validate method name format
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_/]*$", validated["method"]):
            raise ValidationError("method", "Invalid method name format")
        
        # Parameters (optional)
        params = data.get("params")
        if params is not None:
            validated["params"] = InputValidator.validate_json(
                params, "params" if isinstance(params, str) else params
            )
        
        return validated
    
    @classmethod
    def validate_tool_call(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate MCP tool call parameters
        
        Args:
            data: Tool call data
            
        Returns:
            Validated tool call
            
        Raises:
            ValidationError: If validation fails
        """
        validated = {}
        
        # Tool name
        validated["name"] = InputValidator.validate_string(
            data.get("name"), "name", required=True
        )
        
        # Tool arguments (optional)
        arguments = data.get("arguments", {})
        if not isinstance(arguments, dict):
            raise ValidationError("arguments", "Tool arguments must be object")
        
        validated["arguments"] = arguments
        
        return validated

# Convenience functions

def validate_oauth_authorization_request(params: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function for OAuth authorization validation"""
    return OAuthValidator.validate_authorization_request(params)

def validate_oauth_token_request(params: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function for OAuth token validation"""
    return OAuthValidator.validate_token_request(params)

def validate_mcp_message(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function for MCP message validation"""
    return MCPValidator.validate_mcp_request(data)