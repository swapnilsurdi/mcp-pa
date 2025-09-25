"""
Local MCP Server Configuration

Configuration for single-user, STDIO-based MCP server deployment.
Used with Claude Desktop and other local MCP clients.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

class LocalDatabaseConfig(BaseModel):
    """Local database configuration"""
    type: str = Field(default="sqlite", description="Database type: sqlite or tinydb")
    path: Optional[str] = Field(default=None, description="Database file path")
    encryption_key: Optional[str] = Field(default=None, description="Optional encryption key")

class LocalStorageConfig(BaseModel):
    """Local storage configuration"""
    documents_dir: Optional[str] = Field(default=None, description="Document storage directory")
    max_file_size_mb: int = Field(default=100, description="Maximum file size in MB")

class LocalLoggingConfig(BaseModel):
    """Local logging configuration"""
    level: str = Field(default="INFO", description="Log level")
    file_path: Optional[str] = Field(default=None, description="Log file path")
    max_size_mb: int = Field(default=10, description="Maximum log file size")
    backup_count: int = Field(default=3, description="Number of backup log files")

class LocalConfig(BaseModel):
    """
    Local MCP server configuration
    
    This configuration is used for single-user, local MCP server deployments
    that communicate via STDIO with Claude Desktop and other MCP clients.
    """
    
    # Server mode
    mode: str = Field(default="local", description="Server mode: local")
    transport: str = Field(default="stdio", description="Transport: stdio")
    
    # Database configuration
    database: LocalDatabaseConfig = Field(default_factory=LocalDatabaseConfig)
    
    # Storage configuration
    storage: LocalStorageConfig = Field(default_factory=LocalStorageConfig)
    
    # Logging configuration
    logging: LocalLoggingConfig = Field(default_factory=LocalLoggingConfig)
    
    # Feature flags
    enable_vector_search: bool = Field(default=False, description="Enable local vector search")
    enable_encryption: bool = Field(default=False, description="Enable data encryption")
    enable_audit_logging: bool = Field(default=False, description="Enable audit logging")
    
    # Performance settings
    max_concurrent_operations: int = Field(default=10, description="Max concurrent operations")
    operation_timeout: int = Field(default=30, description="Operation timeout in seconds")
    
    class Config:
        env_prefix = "MCP_LOCAL_"
        case_sensitive = False

def get_local_config() -> LocalConfig:
    """
    Load local MCP server configuration from environment variables and defaults
    
    Environment Variables:
        MCP_LOCAL_MODE: Server mode (default: local)
        MCP_LOCAL_DATABASE_TYPE: Database type (sqlite/tinydb)
        MCP_LOCAL_DATABASE_PATH: Database file path
        MCP_LOCAL_ENCRYPTION_KEY: Encryption key
        MCP_LOCAL_DOCUMENTS_DIR: Documents directory
        MCP_LOCAL_LOG_LEVEL: Logging level
        MCP_LOCAL_ENABLE_VECTOR_SEARCH: Enable vector search
        
    Returns:
        LocalConfig instance with loaded configuration
    """
    
    # Determine platform-specific default paths
    app_dir = _get_app_directory()
    
    # Create app directory if it doesn't exist
    app_dir.mkdir(parents=True, exist_ok=True)
    
    # Default database path
    db_type = os.getenv("MCP_LOCAL_DATABASE_TYPE", "sqlite").lower()
    if db_type == "tinydb":
        default_db_path = str(app_dir / "database.json")
    else:
        default_db_path = str(app_dir / "database.sqlite")
    
    # Default directories
    default_docs_dir = str(app_dir / "documents")
    default_log_path = str(app_dir / "mcp-local.log")
    
    # Create configuration with defaults
    config = LocalConfig(
        database=LocalDatabaseConfig(
            type=db_type,
            path=os.getenv("MCP_LOCAL_DATABASE_PATH", default_db_path),
            encryption_key=os.getenv("MCP_LOCAL_ENCRYPTION_KEY")
        ),
        storage=LocalStorageConfig(
            documents_dir=os.getenv("MCP_LOCAL_DOCUMENTS_DIR", default_docs_dir),
            max_file_size_mb=int(os.getenv("MCP_LOCAL_MAX_FILE_SIZE_MB", "100"))
        ),
        logging=LocalLoggingConfig(
            level=os.getenv("MCP_LOCAL_LOG_LEVEL", "INFO"),
            file_path=os.getenv("MCP_LOCAL_LOG_FILE", default_log_path),
            max_size_mb=int(os.getenv("MCP_LOCAL_LOG_MAX_SIZE_MB", "10")),
            backup_count=int(os.getenv("MCP_LOCAL_LOG_BACKUP_COUNT", "3"))
        ),
        enable_vector_search=os.getenv("MCP_LOCAL_ENABLE_VECTOR_SEARCH", "false").lower() == "true",
        enable_encryption=os.getenv("MCP_LOCAL_ENABLE_ENCRYPTION", "false").lower() == "true",
        enable_audit_logging=os.getenv("MCP_LOCAL_ENABLE_AUDIT_LOGGING", "false").lower() == "true",
        max_concurrent_operations=int(os.getenv("MCP_LOCAL_MAX_CONCURRENT_OPS", "10")),
        operation_timeout=int(os.getenv("MCP_LOCAL_OPERATION_TIMEOUT", "30"))
    )
    
    # Create required directories
    _create_directories(config)
    
    logger.info(f"Local MCP configuration loaded: db={config.database.type}, docs={config.storage.documents_dir}")
    return config

def _get_app_directory() -> Path:
    """Get platform-specific application directory"""
    
    if os.name == 'nt':  # Windows
        app_dir = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')) / 'mcp-pa'
    elif os.name == 'posix':
        import sys
        if 'darwin' in sys.platform:  # macOS
            app_dir = Path.home() / 'Library' / 'Application Support' / 'mcp-pa'
        else:  # Linux
            xdg_config_home = os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')
            app_dir = Path(xdg_config_home) / 'mcp-pa'
    else:
        # Fallback for unknown platforms
        app_dir = Path.home() / '.mcp-pa'
    
    return app_dir

def _create_directories(config: LocalConfig) -> None:
    """Create required directories based on configuration"""
    
    directories_to_create = []
    
    # Database directory
    if config.database.path:
        db_dir = Path(config.database.path).parent
        directories_to_create.append(db_dir)
    
    # Documents directory
    if config.storage.documents_dir:
        directories_to_create.append(Path(config.storage.documents_dir))
    
    # Log file directory
    if config.logging.file_path:
        log_dir = Path(config.logging.file_path).parent
        directories_to_create.append(log_dir)
    
    # Create directories
    for directory in directories_to_create:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")
        except Exception as e:
            logger.warning(f"Failed to create directory {directory}: {e}")

def get_sample_local_config() -> Dict[str, Any]:
    """
    Get sample local configuration for documentation
    
    Returns:
        Dictionary with sample configuration values
    """
    return {
        "description": "Local MCP Server Configuration",
        "environment_variables": {
            "MCP_LOCAL_DATABASE_TYPE": "sqlite",
            "MCP_LOCAL_DATABASE_PATH": "~/.config/mcp-pa/database.sqlite",
            "MCP_LOCAL_ENCRYPTION_KEY": "your-encryption-key-here",
            "MCP_LOCAL_DOCUMENTS_DIR": "~/.config/mcp-pa/documents",
            "MCP_LOCAL_LOG_LEVEL": "INFO",
            "MCP_LOCAL_ENABLE_VECTOR_SEARCH": "false",
            "MCP_LOCAL_ENABLE_AUDIT_LOGGING": "false"
        },
        "claude_desktop_config": {
            "mcpServers": {
                "personal-assistant": {
                    "command": "python",
                    "args": ["-m", "src.servers.local_server"],
                    "cwd": "/path/to/mcp-pa",
                    "env": {
                        "MCP_LOCAL_DATABASE_TYPE": "sqlite",
                        "MCP_LOCAL_LOG_LEVEL": "INFO"
                    }
                }
            }
        },
        "features": {
            "authentication": False,
            "multi_tenancy": False,
            "vector_search": "Optional (local embeddings)",
            "audit_logging": "Optional",
            "encryption": "Optional (local data protection)"
        }
    }