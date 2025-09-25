import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

class DatabaseConfig(BaseModel):
    type: str = "sqlite"  # "sqlite" or "tinydb"
    path: Optional[str] = None
    encryption_key: Optional[str] = None

class StorageConfig(BaseModel):
    documents_dir: Optional[str] = None
    max_file_size_mb: int = 100

class Config(BaseModel):
    database: DatabaseConfig = DatabaseConfig()
    storage: StorageConfig = StorageConfig()

def get_config() -> Config:
    """Load configuration from environment variables or use defaults"""
    
    # Determine default paths based on OS
    if os.name == 'nt':  # Windows
        app_dir = Path(os.environ.get('APPDATA', ''), 'mcp-pa')
    elif os.name == 'posix':
        if 'darwin' in os.sys.platform:  # macOS
            app_dir = Path.home() / 'Library' / 'Application Support' / 'mcp-pa'
        else:  # Linux
            app_dir = Path.home() / '.config' / 'mcp-pa'
    else:
        app_dir = Path.home() / '.mcp-pa'
    
    # Create app directory if it doesn't exist
    app_dir.mkdir(parents=True, exist_ok=True)
    
    # Default database path
    default_db_path = str(app_dir / 'database.sqlite')
    if os.environ.get('MCP_PA_DB_TYPE', '').lower() == 'tinydb':
        default_db_path = str(app_dir / 'database.json')
    
    # Default documents directory
    default_docs_dir = str(app_dir / 'documents')
    
    config = Config(
        database=DatabaseConfig(
            type=os.environ.get('MCP_PA_DB_TYPE', 'sqlite').lower(),
            path=os.environ.get('MCP_PA_DB_PATH', default_db_path),
            encryption_key=os.environ.get('MCP_PA_ENCRYPTION_KEY')
        ),
        storage=StorageConfig(
            documents_dir=os.environ.get('MCP_PA_DOCS_DIR', default_docs_dir),
            max_file_size_mb=int(os.environ.get('MCP_PA_MAX_FILE_SIZE_MB', '100'))
        )
    )
    
    # Create directories if they don't exist
    Path(config.database.path).parent.mkdir(parents=True, exist_ok=True)
    Path(config.storage.documents_dir).mkdir(parents=True, exist_ok=True)
    
    return config
