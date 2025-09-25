"""
HTTP MCP Server Configuration

Configuration for multi-tenant, cloud-deployed MCP server with external
identity provider integration (Google, Auth0, GitHub, etc.).
"""

import os
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
import logging

logger = logging.getLogger(__name__)

class ExternalProviderConfig(BaseModel):
    """External identity provider configuration"""
    enabled: bool = Field(default=False, description="Enable this provider")
    client_id: Optional[str] = Field(default=None, description="OAuth client ID")
    client_secret: Optional[str] = Field(default=None, description="OAuth client secret")
    domain: Optional[str] = Field(default=None, description="Provider domain (Auth0)")
    audience: Optional[str] = Field(default=None, description="API audience (Auth0)")

class AuthConfig(BaseModel):
    """Authentication configuration for HTTP MCP server"""
    enabled: bool = Field(default=True, description="Enable authentication")
    
    # External provider configurations
    google: ExternalProviderConfig = Field(default_factory=ExternalProviderConfig)
    auth0: ExternalProviderConfig = Field(default_factory=ExternalProviderConfig)
    github: ExternalProviderConfig = Field(default_factory=ExternalProviderConfig)
    
    # API key fallback
    api_keys_enabled: bool = Field(default=True, description="Enable API key authentication")
    api_keys: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="API key configurations")
    
    # Permissions and tenancy
    default_permissions: List[str] = Field(default=["read", "write"], description="Default user permissions")
    tenant_mapping: Dict[str, str] = Field(default_factory=dict, description="Domain to tenant mapping")
    
    # Token validation
    token_cache_ttl: int = Field(default=300, description="Token cache TTL in seconds")
    max_token_age: int = Field(default=3600, description="Maximum token age in seconds")

class DatabaseConfig(BaseModel):
    """Database configuration"""
    type: str = Field(default="postgresql", description="Database type")
    connection_string: Optional[str] = Field(default=None, description="Database connection string") 
    pool_size: int = Field(default=10, description="Connection pool size")
    pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    encryption_key: Optional[str] = Field(default=None, description="Database encryption key")

class VectorSearchConfig(BaseModel):
    """Vector search configuration"""
    enabled: bool = Field(default=True, description="Enable vector search")
    provider: str = Field(default="local", description="Vector provider (local/openai)")
    model: str = Field(default="all-MiniLM-L6-v2", description="Embedding model")
    dimension: int = Field(default=384, description="Vector dimension")
    similarity_threshold: float = Field(default=0.7, description="Similarity threshold")

class ServerConfig(BaseModel):
    """HTTP server configuration"""
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=1, description="Number of worker processes")
    
    # TLS configuration
    tls_enabled: bool = Field(default=True, description="Enable TLS/HTTPS")
    tls_cert_path: Optional[str] = Field(default=None, description="TLS certificate path")
    tls_key_path: Optional[str] = Field(default=None, description="TLS private key path")
    
    # Security settings
    cors_origins: List[str] = Field(default=["*"], description="CORS allowed origins")
    max_request_size: int = Field(default=16*1024*1024, description="Max request size in bytes")
    request_timeout: int = Field(default=30, description="Request timeout in seconds")

class SecurityConfig(BaseModel):
    """Security configuration"""
    # Rate limiting
    rate_limiting_enabled: bool = Field(default=True, description="Enable rate limiting")
    default_rate_limit: int = Field(default=100, description="Default requests per minute")
    oauth_rate_limit: int = Field(default=20, description="OAuth endpoint rate limit")
    mcp_rate_limit: int = Field(default=200, description="MCP endpoint rate limit")
    
    # HTTPS enforcement
    https_required: bool = Field(default=True, description="Require HTTPS")
    hsts_max_age: int = Field(default=31536000, description="HSTS max age")
    
    # Security headers and protection
    csrf_protection: bool = Field(default=True, description="Enable CSRF protection")
    blocked_user_agents: List[str] = Field(default_factory=list, description="Blocked user agents")

class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = Field(default="INFO", description="Log level")
    format: str = Field(default="json", description="Log format (json/text)")
    
    # Audit logging
    audit_logging_enabled: bool = Field(default=True, description="Enable security audit logging")
    audit_log_file: Optional[str] = Field(default=None, description="Audit log file path")
    
    # Performance logging
    access_logging: bool = Field(default=True, description="Enable access logging")
    slow_query_threshold: float = Field(default=1.0, description="Slow query threshold in seconds")

class HTTPConfig(BaseModel):
    """
    Complete HTTP MCP server configuration
    
    This configuration is used for multi-tenant, cloud-deployed MCP servers
    with external identity provider authentication.
    """
    
    # Server mode
    mode: str = Field(default="http", description="Server mode")
    environment: str = Field(default="production", description="Environment (development/production)")
    
    # Component configurations
    auth: AuthConfig = Field(default_factory=AuthConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    vector_search: VectorSearchConfig = Field(default_factory=VectorSearchConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    # Feature flags
    multi_tenancy: bool = Field(default=True, description="Enable multi-tenancy")
    intelligent_retrieval: bool = Field(default=True, description="Enable intelligent retrieval")
    client_registration: bool = Field(default=False, description="Enable dynamic client registration")
    
    class Config:
        env_prefix = "MCP_HTTP_"
        case_sensitive = False

def get_http_config() -> HTTPConfig:
    """
    Load HTTP MCP server configuration from environment variables
    
    Environment Variables:
        MCP_HTTP_ENVIRONMENT: Environment (development/production)
        MCP_HTTP_DATABASE_CONNECTION_STRING: PostgreSQL connection string
        MCP_HTTP_GOOGLE_CLIENT_ID: Google OAuth client ID
        MCP_HTTP_AUTH0_DOMAIN: Auth0 domain
        MCP_HTTP_TLS_CERT_PATH: TLS certificate path
        MCP_HTTP_TLS_KEY_PATH: TLS private key path
        
    Returns:
        HTTPConfig instance with loaded configuration
    """
    
    environment = os.getenv("MCP_HTTP_ENVIRONMENT", "production")
    
    # Database configuration
    db_connection = os.getenv(
        "MCP_HTTP_DATABASE_CONNECTION_STRING",
        os.getenv("DATABASE_URL")  # Common env var name
    )
    
    # Google OAuth configuration
    google_client_id = os.getenv("MCP_HTTP_GOOGLE_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID")
    google_client_secret = os.getenv("MCP_HTTP_GOOGLE_CLIENT_SECRET") or os.getenv("GOOGLE_CLIENT_SECRET")
    
    # Auth0 configuration
    auth0_domain = os.getenv("MCP_HTTP_AUTH0_DOMAIN") or os.getenv("AUTH0_DOMAIN")
    auth0_audience = os.getenv("MCP_HTTP_AUTH0_AUDIENCE") or os.getenv("AUTH0_AUDIENCE")
    
    # API keys configuration (from JSON string or individual keys)
    api_keys = {}
    api_keys_json = os.getenv("MCP_HTTP_API_KEYS")
    if api_keys_json:
        import json
        try:
            api_keys = json.loads(api_keys_json)
        except json.JSONDecodeError:
            logger.warning("Invalid API_KEYS JSON format")
    
    # Individual API key (for simple setups)
    single_api_key = os.getenv("MCP_HTTP_API_KEY")
    if single_api_key:
        api_keys[single_api_key] = {
            "user_id": "default_user",
            "email": "user@example.com", 
            "name": "Default User",
            "tenant_id": "default",
            "permissions": ["read", "write"]
        }
    
    # TLS configuration
    tls_cert_path = os.getenv("MCP_HTTP_TLS_CERT_PATH")
    tls_key_path = os.getenv("MCP_HTTP_TLS_KEY_PATH")
    tls_enabled = bool(tls_cert_path and tls_key_path) if environment == "production" else False
    
    # Create configuration
    config = HTTPConfig(
        environment=environment,
        auth=AuthConfig(
            enabled=True,
            google=ExternalProviderConfig(
                enabled=bool(google_client_id),
                client_id=google_client_id,
                client_secret=google_client_secret
            ),
            auth0=ExternalProviderConfig(
                enabled=bool(auth0_domain and auth0_audience),
                domain=auth0_domain,
                audience=auth0_audience
            ),
            github=ExternalProviderConfig(
                enabled=os.getenv("MCP_HTTP_GITHUB_ENABLED", "false").lower() == "true"
            ),
            api_keys=api_keys,
            api_keys_enabled=bool(api_keys),
            default_permissions=["read", "write"],
            tenant_mapping={
                "gmail.com": "personal",
                "outlook.com": "personal", 
                "yahoo.com": "personal"
            }
        ),
        database=DatabaseConfig(
            type="postgresql",
            connection_string=db_connection,
            pool_size=int(os.getenv("MCP_HTTP_DB_POOL_SIZE", "10")),
            encryption_key=os.getenv("MCP_HTTP_DB_ENCRYPTION_KEY")
        ),
        server=ServerConfig(
            host=os.getenv("MCP_HTTP_HOST", "0.0.0.0"),
            port=int(os.getenv("MCP_HTTP_PORT", "8000")),
            tls_enabled=tls_enabled,
            tls_cert_path=tls_cert_path,
            tls_key_path=tls_key_path,
            cors_origins=os.getenv("MCP_HTTP_CORS_ORIGINS", "*").split(",")
        ),
        security=SecurityConfig(
            https_required=(environment == "production"),
            rate_limiting_enabled=True,
            csrf_protection=(environment == "production")
        ),
        logging=LoggingConfig(
            level=os.getenv("MCP_HTTP_LOG_LEVEL", "INFO"),
            audit_logging_enabled=True,
            access_logging=True
        )
    )
    
    logger.info(f"HTTP MCP configuration loaded: env={environment}, auth_providers={_get_enabled_providers(config)}")
    return config

def get_development_config() -> HTTPConfig:
    """Get development-friendly HTTP configuration"""
    return HTTPConfig(
        environment="development",
        auth=AuthConfig(
            enabled=False,  # Disable auth for development
            api_keys={
                "dev-key-123": {
                    "user_id": "dev_user",
                    "email": "dev@example.com",
                    "name": "Developer",
                    "tenant_id": "development",
                    "permissions": ["read", "write", "admin"]
                }
            }
        ),
        database=DatabaseConfig(
            connection_string="postgresql://localhost/mcp_dev"
        ),
        server=ServerConfig(
            port=8000,
            tls_enabled=False  # HTTP for development
        ),
        security=SecurityConfig(
            https_required=False,
            rate_limiting_enabled=False,
            csrf_protection=False
        ),
        logging=LoggingConfig(
            level="DEBUG",
            audit_logging_enabled=False
        )
    )

def get_production_config() -> HTTPConfig:
    """Get production-ready HTTP configuration template"""
    return HTTPConfig(
        environment="production",
        auth=AuthConfig(
            enabled=True,
            google=ExternalProviderConfig(enabled=True),
            auth0=ExternalProviderConfig(enabled=True),
            github=ExternalProviderConfig(enabled=True),
            api_keys_enabled=True
        ),
        server=ServerConfig(
            tls_enabled=True
        ),
        security=SecurityConfig(
            https_required=True,
            rate_limiting_enabled=True,
            csrf_protection=True
        ),
        logging=LoggingConfig(
            level="INFO",
            audit_logging_enabled=True,
            access_logging=True
        )
    )

def _get_enabled_providers(config: HTTPConfig) -> List[str]:
    """Get list of enabled authentication providers"""
    providers = []
    
    if config.auth.google.enabled:
        providers.append("google")
    if config.auth.auth0.enabled:
        providers.append("auth0")
    if config.auth.github.enabled:
        providers.append("github")
    if config.auth.api_keys_enabled:
        providers.append("api_keys")
    
    return providers

def get_sample_http_config() -> Dict[str, Any]:
    """
    Get sample HTTP configuration for documentation
    
    Returns:
        Dictionary with sample configuration
    """
    return {
        "description": "HTTP MCP Server Configuration with External Identity Providers",
        "environment_variables": {
            "MCP_HTTP_ENVIRONMENT": "production",
            "MCP_HTTP_DATABASE_CONNECTION_STRING": "postgresql://user:pass@host:5432/mcp_db",
            "MCP_HTTP_GOOGLE_CLIENT_ID": "your-app.googleusercontent.com",
            "MCP_HTTP_GOOGLE_CLIENT_SECRET": "your-google-client-secret",
            "MCP_HTTP_AUTH0_DOMAIN": "your-app.auth0.com", 
            "MCP_HTTP_AUTH0_AUDIENCE": "https://your-mcp-api.com",
            "MCP_HTTP_TLS_CERT_PATH": "/path/to/cert.pem",
            "MCP_HTTP_TLS_KEY_PATH": "/path/to/key.pem",
            "MCP_HTTP_API_KEY": "your-api-key-for-services"
        },
        "deployment_options": {
            "railway": {
                "description": "Deploy to Railway with PostgreSQL addon",
                "command": "railway up",
                "database": "Railway PostgreSQL addon"
            },
            "render": {
                "description": "Deploy to Render with managed PostgreSQL", 
                "database": "Render PostgreSQL"
            },
            "fly_io": {
                "description": "Deploy to Fly.io with Postgres app",
                "database": "Fly Postgres app"
            },
            "docker": {
                "description": "Docker deployment with docker-compose",
                "files": ["Dockerfile", "docker-compose.yml"]
            }
        },
        "authentication_flow": {
            "1": "User authenticates with Google/Auth0/GitHub",
            "2": "Client receives access token from provider", 
            "3": "Client sends token to MCP server",
            "4": "MCP server validates token with provider",
            "5": "MCP server creates user session with tenant isolation"
        },
        "features": {
            "authentication": "External providers (Google, Auth0, GitHub)",
            "multi_tenancy": "Automatic tenant isolation by email domain",
            "vector_search": "PostgreSQL pgvector integration",
            "audit_logging": "Comprehensive security audit trails",
            "rate_limiting": "Per-tenant rate limiting",
            "https_enforcement": "Mandatory TLS in production"
        }
    }