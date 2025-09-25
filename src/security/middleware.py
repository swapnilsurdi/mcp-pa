"""
Security Middleware for OAuth 2.1 and MCP Compliance

Implements comprehensive security middleware including:
- HTTPS enforcement with HSTS
- Security headers (CSP, CSRF protection)
- Rate limiting with tenant isolation
- Request validation and sanitization
"""

import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Set, Callable, Awaitable
from collections import defaultdict
import hashlib
import secrets

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

class HTTPSEnforcementMiddleware(BaseHTTPMiddleware):
    """
    Enforce HTTPS connections with HSTS headers
    
    OAuth 2.1 and MCP security requirement: All connections must use TLS
    """
    
    def __init__(self, 
                 app: ASGIApp,
                 enforce_https: bool = True,
                 hsts_max_age: int = 31536000,  # 1 year
                 hsts_include_subdomains: bool = True,
                 redirect_http_to_https: bool = True):
        super().__init__(app)
        self.enforce_https = enforce_https
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.redirect_http_to_https = redirect_http_to_https
        
        logger.info(f"HTTPSEnforcement initialized: enforce={enforce_https}")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip HTTPS enforcement for health checks and local development
        if not self.enforce_https:
            response = await call_next(request)
            return self._add_security_headers(response)
        
        # Check if request is using HTTPS
        is_https = (
            request.url.scheme == "https" or 
            request.headers.get("x-forwarded-proto") == "https" or
            request.headers.get("x-forwarded-ssl") == "on"
        )
        
        if not is_https:
            if self.redirect_http_to_https and request.method == "GET":
                # Redirect HTTP GET requests to HTTPS
                https_url = str(request.url).replace("http://", "https://", 1)
                logger.info(f"Redirecting HTTP to HTTPS: {request.url}")
                return RedirectResponse(url=https_url, status_code=status.HTTP_301_MOVED_PERMANENTLY)
            else:
                # Reject non-HTTPS requests
                logger.warning(f"Rejecting non-HTTPS request: {request.url}")
                raise HTTPException(
                    status_code=status.HTTP_426_UPGRADE_REQUIRED,
                    detail="HTTPS required for OAuth 2.1 and MCP compliance"
                )
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        return self._add_security_headers(response)
    
    def _add_security_headers(self, response: Response) -> Response:
        """Add security headers to response"""
        
        # HSTS (HTTP Strict Transport Security)
        hsts_value = f"max-age={self.hsts_max_age}"
        if self.hsts_include_subdomains:
            hsts_value += "; includeSubDomains"
        hsts_value += "; preload"
        response.headers["Strict-Transport-Security"] = hsts_value
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "font-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'none'"
        )
        response.headers["Content-Security-Policy"] = csp_policy
        
        # Cache control for sensitive endpoints
        if any(path in str(response.headers.get("content-location", "")) 
               for path in ["/oauth/", "/mcp/"]):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with tenant isolation
    
    Prevents abuse and DoS attacks against OAuth and MCP endpoints
    """
    
    def __init__(self,
                 app: ASGIApp,
                 default_rate_limit: int = 100,  # requests per minute
                 oauth_rate_limit: int = 20,     # OAuth endpoints
                 mcp_rate_limit: int = 200,      # MCP tool calls
                 window_size: int = 60,          # seconds
                 enable_tenant_isolation: bool = True):
        super().__init__(app)
        self.default_rate_limit = default_rate_limit
        self.oauth_rate_limit = oauth_rate_limit
        self.mcp_rate_limit = mcp_rate_limit
        self.window_size = window_size
        self.enable_tenant_isolation = enable_tenant_isolation
        
        # In-memory rate limit store (use Redis in production)
        self.request_counts: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        logger.info("RateLimitMiddleware initialized")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Determine rate limit key
        rate_limit_key = self._get_rate_limit_key(request)
        
        # Get appropriate rate limit
        rate_limit = self._get_rate_limit_for_path(str(request.url.path))
        
        # Check rate limit
        if not self._check_rate_limit(rate_limit_key, rate_limit):
            logger.warning(f"Rate limit exceeded for key: {rate_limit_key}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={
                    "Retry-After": str(self.window_size),
                    "X-RateLimit-Limit": str(rate_limit),
                    "X-RateLimit-Window": str(self.window_size)
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self._get_remaining_requests(rate_limit_key, rate_limit)
        response.headers["X-RateLimit-Limit"] = str(rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + self.window_size)
        
        return response
    
    def _get_rate_limit_key(self, request: Request) -> str:
        """Generate rate limit key with tenant isolation"""
        
        # Try to get tenant from authenticated user
        if hasattr(request.state, "user") and hasattr(request.state.user, "tenant_id"):
            tenant_id = request.state.user.tenant_id
            return f"tenant:{tenant_id}"
        
        # Fall back to IP-based rate limiting
        client_ip = self._get_client_ip(request)
        return f"ip:{client_ip}"
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        # Check for forwarded headers (proxy/load balancer)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to direct connection
        return request.client.host if request.client else "unknown"
    
    def _get_rate_limit_for_path(self, path: str) -> int:
        """Get appropriate rate limit for request path"""
        if path.startswith("/oauth/"):
            return self.oauth_rate_limit
        elif path.startswith("/mcp/"):
            return self.mcp_rate_limit
        else:
            return self.default_rate_limit
    
    def _check_rate_limit(self, key: str, limit: int) -> bool:
        """Check if request is within rate limit"""
        now = time.time()
        window_start = now - self.window_size
        
        # Clean old entries
        if key in self.request_counts:
            self.request_counts[key] = {
                timestamp: count for timestamp, count in self.request_counts[key].items()
                if float(timestamp) > window_start
            }
        
        # Count current requests in window
        current_count = sum(self.request_counts[key].values())
        
        if current_count >= limit:
            return False
        
        # Record this request
        timestamp_key = str(now)
        self.request_counts[key][timestamp_key] = self.request_counts[key].get(timestamp_key, 0) + 1
        
        return True
    
    def _get_remaining_requests(self, key: str, limit: int) -> int:
        """Get remaining requests for the current window"""
        current_count = sum(self.request_counts.get(key, {}).values())
        return max(0, limit - current_count)

class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive security middleware for MCP and OAuth 2.1
    
    Combines multiple security features:
    - Request validation
    - CSRF protection
    - Input sanitization
    - Security logging
    """
    
    def __init__(self,
                 app: ASGIApp,
                 enable_csrf_protection: bool = True,
                 csrf_token_expiry: int = 3600,
                 max_request_size: int = 16 * 1024 * 1024,  # 16MB
                 blocked_user_agents: Optional[Set[str]] = None):
        super().__init__(app)
        self.enable_csrf_protection = enable_csrf_protection
        self.csrf_token_expiry = csrf_token_expiry
        self.max_request_size = max_request_size
        self.blocked_user_agents = blocked_user_agents or set()
        
        # CSRF token store (use Redis in production)
        self.csrf_tokens: Dict[str, Dict[str, Any]] = {}
        
        logger.info("SecurityMiddleware initialized")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Validate request size
        if hasattr(request, "headers"):
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_request_size:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Request too large. Max size: {self.max_request_size} bytes"
                )
        
        # Check blocked user agents
        user_agent = request.headers.get("user-agent", "")
        if any(blocked in user_agent.lower() for blocked in self.blocked_user_agents):
            logger.warning(f"Blocked user agent: {user_agent}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # CSRF protection for state-changing operations
        if self.enable_csrf_protection and request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            # Skip CSRF for API endpoints with Bearer tokens
            auth_header = request.headers.get("authorization", "")
            if not auth_header.startswith("Bearer "):
                await self._validate_csrf_token(request)
        
        # Log security events
        self._log_request(request)
        
        # Process request
        response = await call_next(request)
        
        # Add CSRF token to response if needed
        if self.enable_csrf_protection and request.method == "GET":
            csrf_token = self._generate_csrf_token()
            response.headers["X-CSRF-Token"] = csrf_token
        
        return response
    
    async def _validate_csrf_token(self, request: Request) -> None:
        """Validate CSRF token for state-changing requests"""
        csrf_token = (
            request.headers.get("x-csrf-token") or
            request.headers.get("x-xsrf-token")
        )
        
        if not csrf_token:
            # Try to get from form data
            if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
                form_data = await request.form()
                csrf_token = form_data.get("csrf_token")
        
        if not csrf_token or not self._verify_csrf_token(csrf_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or missing CSRF token"
            )
    
    def _generate_csrf_token(self) -> str:
        """Generate CSRF token"""
        token = secrets.token_urlsafe(32)
        
        self.csrf_tokens[token] = {
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=self.csrf_token_expiry)
        }
        
        return token
    
    def _verify_csrf_token(self, token: str) -> bool:
        """Verify CSRF token"""
        token_data = self.csrf_tokens.get(token)
        if not token_data:
            return False
        
        if datetime.now(timezone.utc) > token_data["expires_at"]:
            del self.csrf_tokens[token]
            return False
        
        return True
    
    def _log_request(self, request: Request) -> None:
        """Log security-relevant request information"""
        log_data = {
            "method": request.method,
            "path": str(request.url.path),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Add user info if available
        if hasattr(request.state, "user"):
            log_data["user_id"] = getattr(request.state.user, "user_id", "unknown")
            log_data["tenant_id"] = getattr(request.state.user, "tenant_id", "unknown")
        
        # Log security events
        if any(suspicious in str(request.url.path).lower() 
               for suspicious in ["../", ".env", "passwd", "admin", "config"]):
            logger.warning(f"Suspicious request: {log_data}")
        else:
            logger.debug(f"Request logged: {log_data}")
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        return request.client.host if request.client else "unknown"

# Convenience functions

def create_security_middleware_stack(
    app: ASGIApp,
    enforce_https: bool = True,
    enable_rate_limiting: bool = True,
    enable_csrf: bool = True
) -> ASGIApp:
    """Create complete security middleware stack"""
    
    # Add middleware in reverse order (innermost first)
    if enable_csrf:
        app = SecurityMiddleware(app, enable_csrf_protection=True)
    
    if enable_rate_limiting:
        app = RateLimitMiddleware(app)
    
    if enforce_https:
        app = HTTPSEnforcementMiddleware(app, enforce_https=True)
    
    logger.info("Security middleware stack created")
    return app