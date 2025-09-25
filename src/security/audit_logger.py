"""
Security Audit Logging for OAuth 2.1 and MCP Compliance

Provides comprehensive audit logging for security events:
- Authentication attempts and failures
- Authorization decisions
- Token lifecycle events
- Suspicious activity detection
- Compliance audit trails
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib

# Configure security logger separately from main application logger
security_logger = logging.getLogger("security_audit")
security_logger.setLevel(logging.INFO)

class AuditEventType(Enum):
    """Types of security audit events"""
    
    # Authentication events
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    AUTH_INVALID_CLIENT = "auth_invalid_client"
    AUTH_RATE_LIMITED = "auth_rate_limited"
    
    # Authorization events
    AUTHZ_TOKEN_ISSUED = "authz_token_issued"
    AUTHZ_TOKEN_REFRESHED = "authz_token_refreshed"
    AUTHZ_TOKEN_REVOKED = "authz_token_revoked"
    AUTHZ_ACCESS_GRANTED = "authz_access_granted"
    AUTHZ_ACCESS_DENIED = "authz_access_denied"
    
    # OAuth specific events
    OAUTH_CODE_ISSUED = "oauth_code_issued"
    OAUTH_CODE_EXCHANGED = "oauth_code_exchanged"
    OAUTH_PKCE_FAILURE = "oauth_pkce_failure"
    OAUTH_INVALID_REDIRECT = "oauth_invalid_redirect"
    
    # MCP specific events
    MCP_TOOL_CALL = "mcp_tool_call"
    MCP_RESOURCE_ACCESS = "mcp_resource_access"
    MCP_INVALID_REQUEST = "mcp_invalid_request"
    
    # Security events
    SECURITY_SUSPICIOUS_REQUEST = "security_suspicious_request"
    SECURITY_RATE_LIMIT_EXCEEDED = "security_rate_limit_exceeded"
    SECURITY_INVALID_INPUT = "security_invalid_input"
    SECURITY_CSRF_FAILURE = "security_csrf_failure"
    SECURITY_HTTPS_VIOLATION = "security_https_violation"

@dataclass
class AuditEvent:
    """Security audit event data structure"""
    
    event_type: AuditEventType
    timestamp: datetime
    user_id: Optional[str] = None
    client_id: Optional[str] = None
    tenant_id: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    resource: Optional[str] = None
    scope: Optional[str] = None
    success: bool = True
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    risk_score: int = 0  # 0-100, higher = more suspicious
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
        
        # Set timestamp to UTC if not provided
        if not self.timestamp.tzinfo:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)

class SecurityAuditLogger:
    """
    Comprehensive security audit logger for OAuth 2.1 and MCP compliance
    
    Features:
    - Structured logging with consistent format
    - Risk scoring for anomaly detection
    - PII hashing for privacy compliance
    - Configurable log retention and filtering
    """
    
    def __init__(self,
                 logger_name: str = "security_audit",
                 enable_pii_hashing: bool = True,
                 hash_salt: str = "mcp-audit-salt",
                 max_details_length: int = 2048):
        """
        Initialize security audit logger
        
        Args:
            logger_name: Logger instance name
            enable_pii_hashing: Whether to hash PII data
            hash_salt: Salt for PII hashing
            max_details_length: Maximum length for details field
        """
        self.logger = logging.getLogger(logger_name)
        self.enable_pii_hashing = enable_pii_hashing
        self.hash_salt = hash_salt
        self.max_details_length = max_details_length
        
        # Risk scoring patterns
        self.high_risk_patterns = [
            r"\.\.\/",  # Path traversal
            r"<script",  # XSS attempts
            r"union\s+select",  # SQL injection
            r"admin",  # Admin access attempts
            r"config",  # Config file access
            r"passwd",  # Password files
        ]
        
        self.logger.info("SecurityAuditLogger initialized")
    
    def log_event(self, event: AuditEvent) -> None:
        """
        Log security audit event
        
        Args:
            event: AuditEvent to log
        """
        try:
            # Calculate risk score if not set
            if event.risk_score == 0:
                event.risk_score = self._calculate_risk_score(event)
            
            # Hash PII if enabled
            if self.enable_pii_hashing:
                event = self._hash_pii(event)
            
            # Prepare log entry
            log_entry = self._format_log_entry(event)
            
            # Log at appropriate level based on event
            if event.success and event.risk_score < 30:
                self.logger.info(log_entry)
            elif not event.success or event.risk_score >= 70:
                self.logger.error(log_entry)
            else:
                self.logger.warning(log_entry)
                
        except Exception as e:
            # Never let audit logging break the application
            self.logger.error(f"Failed to log audit event: {e}")
    
    def log_authentication_success(self,
                                 user_id: str,
                                 client_id: str,
                                 tenant_id: str = None,
                                 client_ip: str = None,
                                 auth_method: str = None,
                                 **kwargs) -> None:
        """Log successful authentication"""
        event = AuditEvent(
            event_type=AuditEventType.AUTH_SUCCESS,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            client_id=client_id,
            tenant_id=tenant_id,
            client_ip=client_ip,
            success=True,
            details={
                "auth_method": auth_method,
                **kwargs
            }
        )
        self.log_event(event)
    
    def log_authentication_failure(self,
                                 client_id: str = None,
                                 client_ip: str = None,
                                 error_code: str = None,
                                 error_message: str = None,
                                 **kwargs) -> None:
        """Log authentication failure"""
        event = AuditEvent(
            event_type=AuditEventType.AUTH_FAILURE,
            timestamp=datetime.now(timezone.utc),
            client_id=client_id,
            client_ip=client_ip,
            success=False,
            error_code=error_code,
            error_message=error_message,
            risk_score=50,  # Auth failures are medium risk
            details=kwargs
        )
        self.log_event(event)
    
    def log_token_issued(self,
                        user_id: str,
                        client_id: str,
                        tenant_id: str = None,
                        scope: str = None,
                        resource: str = None,
                        token_type: str = "access_token",
                        **kwargs) -> None:
        """Log token issuance"""
        event = AuditEvent(
            event_type=AuditEventType.AUTHZ_TOKEN_ISSUED,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            client_id=client_id,
            tenant_id=tenant_id,
            scope=scope,
            resource=resource,
            success=True,
            details={
                "token_type": token_type,
                **kwargs
            }
        )
        self.log_event(event)
    
    def log_access_denied(self,
                         user_id: str = None,
                         client_id: str = None,
                         tenant_id: str = None,
                         resource: str = None,
                         required_scope: str = None,
                         reason: str = None,
                         **kwargs) -> None:
        """Log access denied events"""
        event = AuditEvent(
            event_type=AuditEventType.AUTHZ_ACCESS_DENIED,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            client_id=client_id,
            tenant_id=tenant_id,
            resource=resource,
            scope=required_scope,
            success=False,
            error_message=reason,
            risk_score=40,  # Access denials are medium risk
            details=kwargs
        )
        self.log_event(event)
    
    def log_mcp_tool_call(self,
                         user_id: str,
                         client_id: str,
                         tenant_id: str,
                         tool_name: str,
                         client_ip: str = None,
                         success: bool = True,
                         **kwargs) -> None:
        """Log MCP tool call"""
        event = AuditEvent(
            event_type=AuditEventType.MCP_TOOL_CALL,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            client_id=client_id,
            tenant_id=tenant_id,
            client_ip=client_ip,
            success=success,
            details={
                "tool_name": tool_name,
                **kwargs
            }
        )
        self.log_event(event)
    
    def log_suspicious_activity(self,
                              event_type: AuditEventType,
                              client_ip: str = None,
                              user_agent: str = None,
                              request_path: str = None,
                              risk_score: int = 80,
                              details: Dict[str, Any] = None) -> None:
        """Log suspicious activity"""
        event = AuditEvent(
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            client_ip=client_ip,
            user_agent=user_agent,
            success=False,
            risk_score=risk_score,
            details={
                "request_path": request_path,
                **(details or {})
            }
        )
        self.log_event(event)
    
    def _calculate_risk_score(self, event: AuditEvent) -> int:
        """
        Calculate risk score for event (0-100)
        
        Args:
            event: AuditEvent to score
            
        Returns:
            Risk score (0 = low risk, 100 = high risk)
        """
        score = 0
        
        # Base score by event type
        risk_scores = {
            AuditEventType.AUTH_FAILURE: 30,
            AuditEventType.AUTH_INVALID_CLIENT: 50,
            AuditEventType.AUTHZ_ACCESS_DENIED: 40,
            AuditEventType.OAUTH_PKCE_FAILURE: 60,
            AuditEventType.SECURITY_SUSPICIOUS_REQUEST: 80,
            AuditEventType.SECURITY_RATE_LIMIT_EXCEEDED: 70,
            AuditEventType.SECURITY_CSRF_FAILURE: 75,
        }
        
        score = risk_scores.get(event.event_type, 10)
        
        # Increase score for failures
        if not event.success:
            score += 20
        
        # Check for suspicious patterns
        details_str = json.dumps(event.details or {}).lower()
        for pattern in self.high_risk_patterns:
            import re
            if re.search(pattern, details_str):
                score += 30
                break
        
        # Unknown/suspicious user agents
        if event.user_agent:
            suspicious_agents = ["curl", "wget", "scanner", "bot"]
            if any(agent in event.user_agent.lower() for agent in suspicious_agents):
                score += 20
        
        return min(score, 100)  # Cap at 100
    
    def _hash_pii(self, event: AuditEvent) -> AuditEvent:
        """
        Hash PII data for privacy compliance
        
        Args:
            event: Original event
            
        Returns:
            Event with PII hashed
        """
        # Create copy to avoid modifying original
        hashed_event = AuditEvent(**asdict(event))
        
        # Hash user-identifiable information
        if hashed_event.user_id:
            hashed_event.user_id = self._hash_value(hashed_event.user_id)
        
        if hashed_event.client_ip:
            hashed_event.client_ip = self._hash_value(hashed_event.client_ip)
        
        # Hash email addresses in details
        if hashed_event.details:
            for key, value in hashed_event.details.items():
                if isinstance(value, str) and "@" in value:
                    hashed_event.details[key] = self._hash_value(value)
        
        return hashed_event
    
    def _hash_value(self, value: str) -> str:
        """Hash a value with salt"""
        salted_value = f"{value}{self.hash_salt}"
        return hashlib.sha256(salted_value.encode()).hexdigest()[:16]  # First 16 chars
    
    def _format_log_entry(self, event: AuditEvent) -> str:
        """
        Format audit event for logging
        
        Args:
            event: AuditEvent to format
            
        Returns:
            Formatted log entry string
        """
        # Base log data
        log_data = {
            "event_type": event.event_type.value,
            "timestamp": event.timestamp.isoformat(),
            "success": event.success,
            "risk_score": event.risk_score
        }
        
        # Add optional fields if present
        optional_fields = [
            "user_id", "client_id", "tenant_id", "client_ip", 
            "user_agent", "request_id", "resource", "scope",
            "error_code", "error_message"
        ]
        
        for field in optional_fields:
            value = getattr(event, field)
            if value:
                log_data[field] = value
        
        # Add details if present
        if event.details:
            details_str = json.dumps(event.details)
            if len(details_str) > self.max_details_length:
                details_str = details_str[:self.max_details_length] + "..."
            log_data["details"] = details_str
        
        return json.dumps(log_data, separators=(',', ':'))

# Convenience functions

def get_security_audit_logger(logger_name: str = "security_audit") -> SecurityAuditLogger:
    """Get or create security audit logger instance"""
    return SecurityAuditLogger(logger_name=logger_name)

def log_auth_success(user_id: str, client_id: str, **kwargs) -> None:
    """Convenience function to log authentication success"""
    logger = get_security_audit_logger()
    logger.log_authentication_success(user_id, client_id, **kwargs)

def log_auth_failure(client_id: str = None, error: str = None, **kwargs) -> None:
    """Convenience function to log authentication failure"""
    logger = get_security_audit_logger()
    logger.log_authentication_failure(client_id=client_id, error_message=error, **kwargs)