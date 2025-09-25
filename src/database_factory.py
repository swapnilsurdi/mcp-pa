from .database_interface import DatabaseInterface
from .sqlite_database import SQLiteDatabase
from .tinydb_database import TinyDBDatabase
from .config import get_config

def get_database() -> DatabaseInterface:
    """Factory function to get appropriate database instance based on configuration"""
    config = get_config()
    
    if config.database.type == "sqlite":
        return SQLiteDatabase(
            db_path=config.database.path,
            encryption_key=config.database.encryption_key
        )
    elif config.database.type == "tinydb":
        return TinyDBDatabase(
            db_path=config.database.path,
            encryption_key=config.database.encryption_key
        )
    else:
        raise ValueError(f"Unsupported database type: {config.database.type}")
