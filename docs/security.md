# Task: MCP Security Compliance & Configuration

## Overview
Implement OAuth 2.1 compliance and MCP authorization specification for the Personal Assistant server, with clear configuration for both local and HTTP deployment modes.

## Current State Analysis

### Local MCP Server (src/server.py)
- **Transport**: STDIO pipes
- **Authentication**: None (single-user)
- **Database**: SQLite/TinyDB (local files)
- **Status**: Production ready
- **Use Case**: Individual users, Claude Desktop integration

### HTTP MCP Server (src/http_server.py)
- **Transport**: HTTP/HTTPS
- **Authentication**: OAuth 2.0 (needs upgrade to 2.1)
- **Database**: PostgreSQL with pgvector
- **Status**: Needs security compliance
- **Use Case**: Multi-tenant cloud deployment

## Requirements

### 1. OAuth 2.1 Compliance Requirements

#### PKCE (Proof Key for Code Exchange) - MANDATORY
```
code_verifier: 43-128 characters, cryptographically random
Allowed chars: A-Z, a-z, 0-9, "-", ".", "_", "~"
code_challenge_method: "S256" (recommended) or "plain"
code_challenge: BASE64URL-ENCODE(SHA256(code_verifier))
```

#### Security Enhancements
- Remove implicit grant support
- Enforce TLS for all endpoints
- Token expiration (max 1 hour recommended)
- Client authentication for confidential clients

#### MCP-Specific Requirements
- Resource indicators for audience validation
- Bearer token in Authorization header only
- Dynamic Client Registration (RFC7591)
- Protected Resource Metadata (RFC9728)
- Authorization Server Metadata (RFC8414)

### 2. Configuration Architecture

#### Local MCP Configuration
```json
{
  "mode": "local",
  "transport": "stdio",
  "database": {
    "type": "sqlite",
    "path": "~/.config/mcp-pa/database.sqlite"
  },
  "authentication": {
    "enabled": false
  },
  "features": {
    "vector_search": false,
    "multi_tenant": false
  }
}
```

#### HTTP MCP Configuration
```json
{
  "mode": "http",
  "transport": "https",
  "server": {
    "host": "0.0.0.0",
    "port": 8000,
    "tls_required": true
  },
  "database": {
    "type": "postgresql",
    "connection_string": "postgresql://...",
    "pool_size": 10
  },
  "authentication": {
    "enabled": true,
    "oauth_version": "2.1",
    "pkce_required": true,
    "client_auth_methods": ["private_key_jwt", "tls_client_auth", "client_secret_basic"],
    "token_expiry": 3600
  },
  "features": {
    "vector_search": true,
    "multi_tenant": true,
    "dynamic_client_registration": true
  }
}
```

## Implementation Tasks

### Phase 1: OAuth 2.1 Foundation

#### 1.1 PKCE Implementation
- Create PKCEVerifier class with code challenge validation
- Support both "S256" and "plain" methods
- Generate cryptographically secure code_verifier
- Validate code_challenge against code_verifier

#### 1.2 Enhanced Token Handling
- Implement token expiration enforcement
- Add refresh token rotation
- Validate token audience (resource indicators)
- Secure token storage and transmission

#### 1.3 Client Authentication
```python
class ClientAuthenticator:
    def authenticate_private_key_jwt(self, assertion: str) -> ClientContext
    def authenticate_tls_client_auth(self, cert: X509Certificate) -> ClientContext
    def authenticate_client_secret_basic(self, credentials: str) -> ClientContext
```

### Phase 2: MCP Specification Compliance

#### 2.1 Resource Indicators
- Implement audience validation for tokens
- Add resource URI binding
- Validate token scope against requested resources

#### 2.2 Discovery Endpoints
```python
# RFC8414 - Authorization Server Metadata
GET /.well-known/oauth-authorization-server

# RFC9728 - Protected Resource Metadata  
GET /.well-known/oauth-protected-resource
```

#### 2.3 Dynamic Client Registration
```python
# RFC7591
POST /oauth/register
{
  "redirect_uris": ["https://client.example.org/callback"],
  "grant_types": ["authorization_code"],
  "response_types": ["code"],
  "token_endpoint_auth_method": "private_key_jwt"
}
```

### Phase 3: Security Hardening

#### 3.1 HTTPS Enforcement
- Reject all HTTP requests in production
- Implement HSTS headers
- Certificate validation

#### 3.2 Security Middleware
```python
@middleware
async def security_headers(request: Request, call_next):
    # Add security headers
    # Rate limiting
    # CSRF protection
    # Input validation
```

#### 3.3 Audit Logging
- Authentication events
- Authorization failures
- Token usage patterns
- Security incidents

## File Structure Changes

```
src/
├── auth/
│   ├── __init__.py
│   ├── oauth21_provider.py      # OAuth 2.1 implementation
│   ├── pkce_verifier.py         # PKCE validation
│   ├── client_authenticator.py  # Client authentication
│   ├── token_manager.py         # Token lifecycle
│   └── discovery.py             # Metadata endpoints
├── config/
│   ├── __init__.py
│   ├── local_config.py          # Local MCP configuration
│   ├── http_config.py           # HTTP MCP configuration
│   └── security_config.py       # Security settings
├── security/
│   ├── __init__.py
│   ├── middleware.py            # Security middleware
│   ├── validators.py            # Input validation
│   └── audit_logger.py          # Security logging
└── servers/
    ├── __init__.py
    ├── local_server.py          # STDIO MCP server
    └── http_server.py           # HTTP MCP server
```

## Configuration Examples

### Local Development
```bash
# Run local MCP server
python -m src.servers.local_server

# Claude Desktop config
{
  "mcpServers": {
    "personal-assistant": {
      "command": "python",
      "args": ["-m", "src.servers.local_server"],
      "cwd": "/path/to/mcp-pa"
    }
  }
}
```

### HTTP Production
```bash
# Environment variables
export MCP_MODE=http
export MCP_DATABASE_TYPE=postgresql
export MCP_DATABASE_URL=postgresql://...
export MCP_OAUTH_ISSUER=https://auth.example.com
export MCP_TLS_CERT=/path/to/cert.pem
export MCP_TLS_KEY=/path/to/key.pem

# Run HTTP server
python -m src.servers.http_server
```

### Client Configuration (Future)
```json
{
  "mcpServers": {
    "personal-assistant": {
      "transport": "https",
      "url": "https://mcp-pa.example.com",
      "auth": {
        "type": "oauth2.1",
        "client_id": "mcp-client-123",
        "authorization_endpoint": "https://auth.example.com/oauth/authorize",
        "token_endpoint": "https://auth.example.com/oauth/token",
        "pkce": true
      }
    }
  }
}
```

## Security Checklist

### OAuth 2.1 Compliance
- [ ] PKCE implementation with S256 method
- [ ] Remove implicit grant type
- [ ] Enforce TLS for all endpoints
- [ ] Token expiration (≤ 1 hour)
- [ ] Client authentication for confidential clients
- [ ] Proper error handling and responses

### MCP Specification
- [ ] Resource indicators support
- [ ] Bearer token validation only
- [ ] Dynamic Client Registration (RFC7591)
- [ ] Authorization Server Metadata (RFC8414)
- [ ] Protected Resource Metadata (RFC9728)
- [ ] Canonical server URI handling

### Security Hardening
- [ ] HTTPS enforcement with HSTS
- [ ] Rate limiting implementation
- [ ] Input validation and sanitization
- [ ] CSRF protection
- [ ] Security audit logging
- [ ] Token theft protection

## Testing Requirements

### Unit Tests
- PKCE code challenge validation
- Token expiration handling
- Client authentication methods
- Resource indicator validation

### Integration Tests
- Full OAuth 2.1 authorization flow
- Multi-tenant database isolation
- Security middleware functionality
- Discovery endpoint responses

### Security Tests
- Token replay attacks
- Code injection attempts
- CSRF attack simulation
- TLS configuration validation

## Documentation Updates

### User Documentation
- Local vs HTTP setup guides
- OAuth 2.1 client configuration
- Security best practices
- Troubleshooting guide

### Developer Documentation
- Architecture decision records
- Security model documentation
- API reference with examples
- Migration guide from OAuth 2.0

## Success Criteria

1. **OAuth 2.1 Compliance**: Full implementation of OAuth 2.1 with PKCE
2. **MCP Specification**: 100% compliance with MCP authorization spec
3. **Security**: Pass security audit with no critical vulnerabilities
4. **Usability**: Clear setup documentation for both deployment modes
5. **Performance**: No significant performance degradation from security features
6. **Maintainability**: Clean, testable code with comprehensive test coverage

## Timeline

- **Phase 1** (OAuth 2.1): 3-5 days
- **Phase 2** (MCP Compliance): 2-3 days
- **Phase 3** (Security Hardening): 2-3 days
- **Testing & Documentation**: 2-3 days

**Total Estimated Time**: 9-14 days

## Dependencies

- `authlib` - OAuth 2.1 implementation
- `cryptography` - PKCE and JWT handling
- `pydantic` - Configuration validation
- `pytest-asyncio` - Async testing
- `httpx` - HTTP client for testing