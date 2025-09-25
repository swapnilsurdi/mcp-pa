"""
Configuration Module for MCP Personal Assistant

Provides configuration management for both deployment modes:
- Local MCP server (STDIO transport)  
- HTTP MCP server (cloud deployment)
"""

from .local_config import LocalConfig, get_local_config
from .http_config import HTTPConfig, get_http_config
# from .security_config import SecurityConfig, get_security_config

# For backwards compatibility, import from the old config.py
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from ..config import get_config, Config
except ImportError:
    # Fallback if the old config doesn't exist
    def get_config():
        return get_local_config()
    Config = LocalConfig

__all__ = [
    'LocalConfig',
    'HTTPConfig',
    # 'SecurityConfig',
    'get_local_config',
    'get_http_config',
    # 'get_security_config'
    'get_config',
    'Config'
]