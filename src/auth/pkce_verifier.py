"""
PKCE (Proof Key for Code Exchange) Implementation for OAuth 2.1

Implements RFC 7636 with OAuth 2.1 requirements:
- Mandatory PKCE for public clients
- S256 method recommended over plain
- Cryptographically secure code generation
"""

import base64
import hashlib
import secrets
import string
from dataclasses import dataclass
from typing import Literal, Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class PKCEChallenge:
    """PKCE challenge data structure"""
    code_verifier: str
    code_challenge: str
    code_challenge_method: Literal["S256", "plain"]

class PKCEError(Exception):
    """PKCE-related errors"""
    pass

class PKCEVerifier:
    """
    PKCE verification implementation compliant with OAuth 2.1
    
    OAuth 2.1 Requirements:
    - code_verifier: 43-128 characters, cryptographically random
    - Allowed characters: A-Z, a-z, 0-9, "-", ".", "_", "~"
    - code_challenge_method: "S256" (recommended) or "plain"
    """
    
    # Valid characters for code_verifier per RFC 7636
    VALID_CHARS = string.ascii_letters + string.digits + "-._~"
    
    MIN_VERIFIER_LENGTH = 43
    MAX_VERIFIER_LENGTH = 128
    
    @classmethod
    def generate_code_verifier(cls, length: int = 128) -> str:
        """
        Generate cryptographically secure code verifier
        
        Args:
            length: Length of code verifier (43-128 characters)
            
        Returns:
            Cryptographically random code verifier string
            
        Raises:
            PKCEError: If length is invalid
        """
        if not (cls.MIN_VERIFIER_LENGTH <= length <= cls.MAX_VERIFIER_LENGTH):
            raise PKCEError(
                f"Code verifier length must be between {cls.MIN_VERIFIER_LENGTH} "
                f"and {cls.MAX_VERIFIER_LENGTH} characters"
            )
        
        # Use cryptographically secure random generation
        code_verifier = ''.join(
            secrets.choice(cls.VALID_CHARS) for _ in range(length)
        )
        
        logger.debug(f"Generated code verifier of length {len(code_verifier)}")
        return code_verifier
    
    @classmethod
    def generate_code_challenge(
        cls, 
        code_verifier: str, 
        method: Literal["S256", "plain"] = "S256"
    ) -> str:
        """
        Generate code challenge from code verifier
        
        Args:
            code_verifier: The code verifier string
            method: Challenge method ("S256" or "plain")
            
        Returns:
            Code challenge string
            
        Raises:
            PKCEError: If verifier is invalid or method unsupported
        """
        cls._validate_code_verifier(code_verifier)
        
        if method == "S256":
            # SHA256 hash and base64url encode
            digest = hashlib.sha256(code_verifier.encode('ascii')).digest()
            code_challenge = base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')
            
        elif method == "plain":
            # Use code verifier directly (not recommended for production)
            logger.warning("Using 'plain' PKCE method - S256 is recommended for security")
            code_challenge = code_verifier
            
        else:
            raise PKCEError(f"Unsupported code challenge method: {method}")
        
        logger.debug(f"Generated code challenge using {method} method")
        return code_challenge
    
    @classmethod
    def create_pkce_challenge(
        cls, 
        verifier_length: int = 128,
        method: Literal["S256", "plain"] = "S256"
    ) -> PKCEChallenge:
        """
        Create complete PKCE challenge with verifier and challenge
        
        Args:
            verifier_length: Length of code verifier (43-128)
            method: Challenge method ("S256" or "plain")
            
        Returns:
            PKCEChallenge containing verifier, challenge, and method
        """
        code_verifier = cls.generate_code_verifier(verifier_length)
        code_challenge = cls.generate_code_challenge(code_verifier, method)
        
        return PKCEChallenge(
            code_verifier=code_verifier,
            code_challenge=code_challenge,
            code_challenge_method=method
        )
    
    @classmethod
    def verify_code_challenge(
        cls,
        code_verifier: str,
        code_challenge: str,
        method: Literal["S256", "plain"]
    ) -> bool:
        """
        Verify that code verifier matches the challenge
        
        Args:
            code_verifier: The original code verifier
            code_challenge: The code challenge to verify against
            method: The method used to generate the challenge
            
        Returns:
            True if verification succeeds, False otherwise
            
        Raises:
            PKCEError: If parameters are invalid
        """
        try:
            cls._validate_code_verifier(code_verifier)
            
            if not code_challenge:
                logger.error("Empty code challenge provided")
                return False
            
            # Generate expected challenge
            expected_challenge = cls.generate_code_challenge(code_verifier, method)
            
            # Constant-time comparison to prevent timing attacks
            is_valid = secrets.compare_digest(expected_challenge, code_challenge)
            
            if is_valid:
                logger.info("PKCE verification successful")
            else:
                logger.warning("PKCE verification failed - challenge mismatch")
                
            return is_valid
            
        except Exception as e:
            logger.error(f"PKCE verification error: {e}")
            return False
    
    @classmethod
    def _validate_code_verifier(cls, code_verifier: str) -> None:
        """
        Validate code verifier according to OAuth 2.1 requirements
        
        Args:
            code_verifier: The code verifier to validate
            
        Raises:
            PKCEError: If code verifier is invalid
        """
        if not code_verifier:
            raise PKCEError("Code verifier cannot be empty")
        
        if not (cls.MIN_VERIFIER_LENGTH <= len(code_verifier) <= cls.MAX_VERIFIER_LENGTH):
            raise PKCEError(
                f"Code verifier length must be between {cls.MIN_VERIFIER_LENGTH} "
                f"and {cls.MAX_VERIFIER_LENGTH} characters, got {len(code_verifier)}"
            )
        
        # Check for invalid characters
        invalid_chars = set(code_verifier) - set(cls.VALID_CHARS)
        if invalid_chars:
            raise PKCEError(
                f"Code verifier contains invalid characters: {sorted(invalid_chars)}"
            )
        
        logger.debug("Code verifier validation passed")

# Convenience functions for common usage patterns

def create_pkce_pair() -> PKCEChallenge:
    """Create PKCE challenge pair with secure defaults"""
    return PKCEVerifier.create_pkce_challenge(
        verifier_length=128,
        method="S256"
    )

def verify_pkce(
    code_verifier: str,
    code_challenge: str,
    method: str = "S256"
) -> bool:
    """Verify PKCE challenge with type conversion"""
    if method not in ["S256", "plain"]:
        logger.error(f"Invalid PKCE method: {method}")
        return False
    
    return PKCEVerifier.verify_code_challenge(
        code_verifier, 
        code_challenge, 
        method  # type: ignore
    )