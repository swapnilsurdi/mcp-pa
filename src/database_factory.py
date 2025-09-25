import asyncio
from typing import Optional

from .database_interface import DatabaseInterface
from .sqlite_database import SQLiteDatabase
from .tinydb_database import TinyDBDatabase
from .config import Config

class DatabaseFactory:
    """Factory class for creating database instances with async support"""
    
    @staticmethod
    async def create_database(config: Config) -> DatabaseInterface:
        """Create and initialize appropriate database instance based on configuration"""
        
        if config.database_type == "sqlite":
            db = SQLiteDatabase(
                db_path=config.database_path,
                encryption_key=getattr(config, 'encryption_key', None)
            )
            await db.connect()
            return db
            
        elif config.database_type == "tinydb":
            db = TinyDBDatabase(
                db_path=config.database_path,
                encryption_key=getattr(config, 'encryption_key', None)
            )
            await db.connect()
            return db
            
        elif config.database_type == "postgresql":
            try:
                from .postgres_database import PostgresDatabase
                db = PostgresDatabase(config.pgvector_connection_string)
                await db.connect()
                return db
            except ImportError as e:
                raise ImportError(f"PostgreSQL support requires additional dependencies: {e}")
            
        else:
            raise ValueError(f"Unsupported database type: {config.database_type}")

# Legacy function for backward compatibility
def get_database() -> DatabaseInterface:
    """Legacy factory function - use DatabaseFactory.create_database() for new code"""
    from .config import get_config
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
