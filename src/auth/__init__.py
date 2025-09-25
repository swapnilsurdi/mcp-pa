"""
OAuth 2.1 Authentication Module for MCP Personal Assistant

This module provides OAuth 2.1 compliant authentication with:
- PKCE (Proof Key for Code Exchange) support
- Resource indicators for audience validation
- Multiple client authentication methods
- MCP specification compliance
"""

from .oauth21_provider import OAuth21Provider
from .pkce_verifier import PKCEVerifier, PKCEChallenge
from .client_authenticator import ClientAuthenticator, ClientContext
from .token_manager import TokenManager, TokenContext
from .discovery import DiscoveryService

__all__ = [
    'OAuth21Provider',
    'PKCEVerifier',
    'PKCEChallenge', 
    'ClientAuthenticator',
    'ClientContext',
    'TokenManager',
    'TokenContext',
    'DiscoveryService'
]