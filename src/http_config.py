"""
Configuration for HTTP MCP Server

Enhanced configuration supporting multi-tenancy, vector search,
and cloud deployment options.
"""

import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class DatabaseConfig:
    """Database configuration"""
    type: str = "postgresql"  # postgresql, sqlite, tinydb
    connection_string: Optional[str] = None
    path: Optional[str] = None
    pool_size: int = 10
    encryption_key: Optional[str] = None

@dataclass
class VectorSearchConfig:
    """Vector search configuration"""
    enabled: bool = True
    provider: str = "local"  # openai, local
    model: str = "all-MiniLM-L6-v2"  # or text-embedding-ada-002 for OpenAI
    dimension: int = 384  # 384 for MiniLM, 1536 for OpenAI ada-002
    similarity_threshold: float = 0.7
    max_results: int = 10

@dataclass
class AuthConfig:
    """Authentication configuration"""
    enabled: bool = True
    provider: str = "oauth"  # oauth, jwt, api_key
    oauth_client_id: Optional[str] = None
    oauth_client_secret: Optional[str] = None
    oauth_issuer: Optional[str] = None
    jwt_secret: Optional[str] = None
    api_keys: List[str] = field(default_factory=list)

@dataclass
class ServerConfig:
    """Server configuration"""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    max_request_size: int = 16 * 1024 * 1024  # 16MB
    timeout: int = 300  # 5 minutes

@dataclass
class CacheConfig:
    """Cache configuration"""
    enabled: bool = True
    backend: str = "redis"  # redis, memory
    redis_url: Optional[str] = None
    ttl: int = 3600  # 1 hour
    max_size: int = 1000

@dataclass
class MonitoringConfig:
    """Monitoring and logging configuration"""
    log_level: str = "INFO"
    metrics_enabled: bool = True
    health_check_path: str = "/health"
    prometheus_path: str = "/metrics"

@dataclass
class Config:
    """Main configuration class for HTTP MCP Server"""
    
    # Legacy support
    database_type: str = "postgresql"
    database_path: str = "./data/personal_assistant.db"
    pgvector_connection_string: str = "postgresql://localhost:5432/mcp_pa"
    
    # New structured config
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    vector_search: VectorSearchConfig = field(default_factory=VectorSearchConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    # Feature flags
    features: Dict[str, bool] = field(default_factory=lambda: {
        "semantic_search": True,
        "intelligent_dashboard": True,
        "document_indexing": True,
        "multi_tenancy": True,
        "rate_limiting": True
    })
    
    # Environment-specific settings
    environment: str = "development"  # development, staging, production
    debug: bool = True
    
    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables"""
        
        # Database configuration
        db_config = DatabaseConfig(
            type=os.getenv("DB_TYPE", "postgresql"),
            connection_string=os.getenv("DATABASE_URL") or os.getenv("PGVECTOR_CONNECTION_STRING"),
            path=os.getenv("DB_PATH", "./data/personal_assistant.db"),
            pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
            encryption_key=os.getenv("DB_ENCRYPTION_KEY")
        )
        
        # Vector search configuration
        vector_config = VectorSearchConfig(
            enabled=os.getenv("VECTOR_SEARCH_ENABLED", "true").lower() == "true",
            provider=os.getenv("EMBEDDING_PROVIDER", "local"),
            model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            dimension=int(os.getenv("EMBEDDING_DIMENSION", "384")),
            similarity_threshold=float(os.getenv("SIMILARITY_THRESHOLD", "0.7")),
            max_results=int(os.getenv("MAX_SEARCH_RESULTS", "10"))
        )
        
        # Auth configuration
        auth_config = AuthConfig(
            enabled=os.getenv("AUTH_ENABLED", "true").lower() == "true",
            provider=os.getenv("AUTH_PROVIDER", "oauth"),
            oauth_client_id=os.getenv("OAUTH_CLIENT_ID"),
            oauth_client_secret=os.getenv("OAUTH_CLIENT_SECRET"),
            oauth_issuer=os.getenv("OAUTH_ISSUER"),
            jwt_secret=os.getenv("JWT_SECRET"),
            api_keys=os.getenv("API_KEYS", "").split(",") if os.getenv("API_KEYS") else []
        )
        
        # Server configuration
        server_config = ServerConfig(
            host=os.getenv("SERVER_HOST", "0.0.0.0"),
            port=int(os.getenv("SERVER_PORT", "8000")),
            workers=int(os.getenv("SERVER_WORKERS", "1")),
            cors_origins=os.getenv("CORS_ORIGINS", "*").split(","),
            max_request_size=int(os.getenv("MAX_REQUEST_SIZE", str(16 * 1024 * 1024))),
            timeout=int(os.getenv("SERVER_TIMEOUT", "300"))
        )
        
        # Cache configuration
        cache_config = CacheConfig(
            enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
            backend=os.getenv("CACHE_BACKEND", "redis"),
            redis_url=os.getenv("REDIS_URL"),
            ttl=int(os.getenv("CACHE_TTL", "3600")),
            max_size=int(os.getenv("CACHE_MAX_SIZE", "1000"))
        )
        
        # Monitoring configuration
        monitoring_config = MonitoringConfig(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            metrics_enabled=os.getenv("METRICS_ENABLED", "true").lower() == "true",
            health_check_path=os.getenv("HEALTH_CHECK_PATH", "/health"),
            prometheus_path=os.getenv("PROMETHEUS_PATH", "/metrics")
        )
        
        # Feature flags
        features = {
            "semantic_search": os.getenv("FEATURE_SEMANTIC_SEARCH", "true").lower() == "true",
            "intelligent_dashboard": os.getenv("FEATURE_INTELLIGENT_DASHBOARD", "true").lower() == "true",
            "document_indexing": os.getenv("FEATURE_DOCUMENT_INDEXING", "true").lower() == "true",
            "multi_tenancy": os.getenv("FEATURE_MULTI_TENANCY", "true").lower() == "true",
            "rate_limiting": os.getenv("FEATURE_RATE_LIMITING", "true").lower() == "true"
        }
        
        return cls(
            # Legacy support
            database_type=db_config.type,
            database_path=db_config.path or "./data/personal_assistant.db",
            pgvector_connection_string=db_config.connection_string or "postgresql://localhost:5432/mcp_pa",
            
            # New structured config
            database=db_config,
            vector_search=vector_config,
            auth=auth_config,
            server=server_config,
            cache=cache_config,
            monitoring=monitoring_config,
            features=features,
            environment=os.getenv("ENVIRONMENT", "development"),
            debug=os.getenv("DEBUG", "true").lower() == "true"
        )
    
    @classmethod
    def for_development(cls) -> "Config":
        """Create development configuration"""
        return cls(
            database_type="sqlite",
            database_path="./data/dev_personal_assistant.db",
            database=DatabaseConfig(
                type="sqlite",
                path="./data/dev_personal_assistant.db"
            ),
            auth=AuthConfig(enabled=False),  # Disable auth for development
            server=ServerConfig(port=8000, workers=1),
            environment="development",
            debug=True
        )
    
    @classmethod
    def for_production(cls) -> "Config":
        """Create production configuration with security defaults"""
        config = cls.from_env()
        
        # Override with production defaults
        config.environment = "production"
        config.debug = False
        config.auth.enabled = True
        config.server.cors_origins = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else []
        
        # Validate required production settings
        if config.database.type == "postgresql" and not config.database.connection_string:
            raise ValueError("DATABASE_URL is required for production")
        
        if config.auth.enabled and config.auth.provider == "oauth":
            if not config.auth.oauth_client_id or not config.auth.oauth_client_secret:
                raise ValueError("OAuth credentials are required when auth is enabled")
        
        return config
    
    def validate(self) -> None:
        """Validate configuration"""
        if self.database.type == "postgresql" and not self.database.connection_string:
            if not self.pgvector_connection_string:
                raise ValueError("PostgreSQL connection string is required")
            self.database.connection_string = self.pgvector_connection_string
        
        if self.vector_search.enabled and self.vector_search.provider == "openai":
            if not os.getenv("OPENAI_API_KEY"):
                raise ValueError("OPENAI_API_KEY is required for OpenAI embeddings")
        
        if self.cache.enabled and self.cache.backend == "redis" and not self.cache.redis_url:
            raise ValueError("Redis URL is required when Redis cache is enabled")


# Global configuration instance
_config: Optional[Config] = None

def get_config() -> Config:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = Config.from_env()
        _config.validate()
    return _config

def set_config(config: Config) -> None:
    """Set global configuration instance"""
    global _config
    config.validate()
    _config = config

def reset_config() -> None:
    """Reset global configuration instance"""
    global _config
    _config = None