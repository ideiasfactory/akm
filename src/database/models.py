"""
Database models for API Key Management.

SQLAlchemy ORM models for multi-project API key management with scopes,
rate limiting, webhooks, and alerting capabilities.
"""

from datetime import datetime, time
from typing import Optional
import hashlib
import json

from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    Index,
    String,
    Boolean,
    Text,
    ForeignKey,
    Date,
    Time,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class AKMProject(Base):
    """
    Model for projects in multi-tenant API key management.
    
    Each project can have multiple API keys, scopes, and configurations.
    The prefix field ensures unique namespacing for multi-tenant scopes.
    """
    __tablename__ = "akm_projects"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    prefix = Column(String(20), nullable=False, unique=True, index=True)  # e.g., "akm", "proj1"
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Relationships
    api_keys = relationship("AKMAPIKey", back_populates="project", cascade="all, delete-orphan")
    scopes = relationship("AKMScope", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<AKMProject(id={self.id}, name='{self.name}', prefix='{self.prefix}')>"


class AKMScope(Base):
    """
    Model for permission scopes with project isolation.
    
    Scopes are now project-specific for true multi-tenancy.
    Scope names must start with the project's prefix (e.g., akm:projects:read).
    """
    __tablename__ = "akm_scopes"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("akm_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    scope_name = Column(String(100), nullable=False)  # Not globally unique anymore
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    project = relationship("AKMProject", back_populates="scopes")
    
    # Constraints - scope_name is unique per project, not globally
    __table_args__ = (
        UniqueConstraint("project_id", "scope_name", name="uq_project_scope"),
        Index("idx_scopes_project_active", "project_id", "is_active"),
    )
    
    def __repr__(self) -> str:
        return f"<AKMScope(project_id={self.project_id}, scope_name='{self.scope_name}')>"


class AKMAPIKey(Base):
    """
    Model for API keys with project association and scope-based permissions.
    """
    __tablename__ = "akm_api_keys"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Project association
    project_id = Column(Integer, ForeignKey("akm_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # API Key (hashed with SHA-256)
    key_hash = Column(String(64), unique=True, nullable=False, index=True)
    
    # Key metadata
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Usage tracking
    request_count = Column(Integer, default=0, nullable=False)
    
    # Relationships
    project = relationship("AKMProject", back_populates="api_keys")
    scopes = relationship("AKMAPIKeyScope", back_populates="api_key", cascade="all, delete-orphan")
    config = relationship("AKMAPIKeyConfig", back_populates="api_key", uselist=False, cascade="all, delete-orphan")
    webhooks = relationship("AKMWebhook", back_populates="api_key", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_akm_key_hash_active", key_hash, is_active),
        Index("idx_akm_key_project", project_id, is_active),
    )
    
    def __repr__(self) -> str:
        return f"<AKMAPIKey(id={self.id}, name='{self.name}', project_id={self.project_id})>"
    
    def is_expired(self) -> bool:
        """Check if the API key is expired."""
        if self.expires_at is None:
            return False
        return bool(datetime.now(self.expires_at.tzinfo) > self.expires_at)
    
    def is_valid(self) -> bool:
        """Check if the API key is valid (active and not expired)."""
        return bool(self.is_active) and not self.is_expired()


class AKMAPIKeyScope(Base):
    """
    Model for API key scope assignments (many-to-many relationship).
    Now uses scope_id instead of scope_name for proper FK relationship.
    """
    __tablename__ = "akm_api_key_scopes"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    api_key_id = Column(Integer, ForeignKey("akm_api_keys.id", ondelete="CASCADE"), nullable=False)
    scope_id = Column(Integer, ForeignKey("akm_scopes.id", ondelete="CASCADE"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    api_key = relationship("AKMAPIKey", back_populates="scopes")
    scope = relationship("AKMScope")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("api_key_id", "scope_id", name="uq_api_key_scope"),
        Index("idx_akm_key_scope", api_key_id, scope_id),
    )
    
    def __repr__(self) -> str:
        return f"<AKMAPIKeyScope(api_key_id={self.api_key_id}, scope_id={self.scope_id})>"


class AKMAPIKeyConfig(Base):
    """
    Model for API key configuration (rate limits, IP whitelist, time restrictions).
    """
    __tablename__ = "akm_api_key_configs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    api_key_id = Column(Integer, ForeignKey("akm_api_keys.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Rate limiting
    rate_limit_enabled = Column(Boolean, default=False, nullable=False)
    rate_limit_requests = Column(Integer, nullable=True)  # Requests per window
    rate_limit_window_seconds = Column(Integer, default=60, nullable=True)  # Window size
    
    # Daily/Monthly limits
    daily_request_limit = Column(Integer, nullable=True)
    monthly_request_limit = Column(Integer, nullable=True)
    
    # IP Whitelist
    ip_whitelist_enabled = Column(Boolean, default=False, nullable=False)
    allowed_ips = Column(JSON, nullable=True)  # List of IPs or CIDR blocks
    
    # Time restrictions
    allowed_time_start = Column(Time, nullable=True)  # Start time (e.g., 08:00)
    allowed_time_end = Column(Time, nullable=True)  # End time (e.g., 18:00)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Relationships
    api_key = relationship("AKMAPIKey", back_populates="config")
    
    def __repr__(self) -> str:
        return f"<AKMAPIKeyConfig(api_key_id={self.api_key_id})>"


class AKMRateLimitBucket(Base):
    """
    Model for tracking rate limit buckets (sliding window).
    """
    __tablename__ = "akm_rate_limit_buckets"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    api_key_id = Column(Integer, ForeignKey("akm_api_keys.id", ondelete="CASCADE"), nullable=False)
    
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    request_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("api_key_id", "window_start", name="uq_rate_bucket"),
        Index("idx_akm_rate_bucket_window", api_key_id, window_start, window_end),
    )
    
    def __repr__(self) -> str:
        return f"<AKMRateLimitBucket(api_key_id={self.api_key_id}, count={self.request_count})>"


class AKMUsageMetric(Base):
    """
    Model for tracking API usage metrics (hourly aggregation).
    """
    __tablename__ = "akm_usage_metrics"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    api_key_id = Column(Integer, ForeignKey("akm_api_keys.id", ondelete="CASCADE"), nullable=False)
    
    date = Column(Date, nullable=False)
    hour = Column(Integer, nullable=False)  # 0-23
    
    request_count = Column(Integer, default=0, nullable=False)
    successful_requests = Column(Integer, default=0, nullable=False)
    failed_requests = Column(Integer, default=0, nullable=False)
    avg_response_time_ms = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("api_key_id", "date", "hour", name="uq_usage_metric"),
        Index("idx_akm_usage_key_date", api_key_id, date),
    )
    
    def __repr__(self) -> str:
        return f"<AKMUsageMetric(api_key_id={self.api_key_id}, date={self.date}, hour={self.hour})>"


class AKMWebhook(Base):
    """
    Model for webhook configurations.
    """
    __tablename__ = "akm_webhooks"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    api_key_id = Column(Integer, ForeignKey("akm_api_keys.id", ondelete="CASCADE"), nullable=False, index=True)
    
    url = Column(String(500), nullable=False)
    secret = Column(String(255), nullable=True)  # For HMAC signature
    is_active = Column(Boolean, default=True, nullable=False)
    
    retry_policy = Column(JSON, default={"max_retries": 3, "backoff_seconds": [1, 5, 15]}, nullable=False)
    timeout_seconds = Column(Integer, default=30, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Relationships
    api_key = relationship("AKMAPIKey", back_populates="webhooks")
    subscriptions = relationship("AKMWebhookSubscription", back_populates="webhook", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<AKMWebhook(id={self.id}, api_key_id={self.api_key_id}, url='{self.url}')>"


class AKMWebhookEvent(Base):
    """
    Model for available webhook event types.
    """
    __tablename__ = "akm_webhook_events"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_type = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    payload_schema = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self) -> str:
        return f"<AKMWebhookEvent(event_type='{self.event_type}')>"


class AKMWebhookSubscription(Base):
    """
    Model for webhook event subscriptions (many-to-many).
    """
    __tablename__ = "akm_webhook_subscriptions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    webhook_id = Column(Integer, ForeignKey("akm_webhooks.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(100), ForeignKey("akm_webhook_events.event_type", ondelete="CASCADE"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    webhook = relationship("AKMWebhook", back_populates="subscriptions")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("webhook_id", "event_type", name="uq_webhook_event"),
        Index("idx_akm_webhook_sub", webhook_id, event_type),
    )
    
    def __repr__(self) -> str:
        return f"<AKMWebhookSubscription(webhook_id={self.webhook_id}, event='{self.event_type}')>"


class AKMWebhookDelivery(Base):
    """
    Model for webhook delivery logs.
    """
    __tablename__ = "akm_webhook_deliveries"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    webhook_id = Column(Integer, ForeignKey("akm_webhooks.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(100), nullable=False)
    
    payload = Column(JSON, nullable=False)
    status = Column(String(50), nullable=False, index=True)  # pending, success, failed, retrying
    
    http_status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    
    attempt_count = Column(Integer, default=0, nullable=False)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_akm_delivery_webhook", webhook_id, created_at),
        Index("idx_akm_delivery_retry", status, next_retry_at),
    )
    
    def __repr__(self) -> str:
        return f"<AKMWebhookDelivery(id={self.id}, webhook_id={self.webhook_id}, status='{self.status}')>"


class AKMAlertRule(Base):
    """
    Model for alert rules based on thresholds.
    """
    __tablename__ = "akm_alert_rules"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    api_key_id = Column(Integer, ForeignKey("akm_api_keys.id", ondelete="CASCADE"), nullable=False, index=True)
    
    rule_name = Column(String(100), nullable=False)
    metric_type = Column(String(50), nullable=False)  # rate_limit, daily_limit, error_rate
    
    threshold_value = Column(Integer, nullable=False)
    threshold_percentage = Column(Integer, nullable=True)  # For percentage-based alerts
    comparison_operator = Column(String(10), nullable=False)  # >=, >, ==, <, <=
    
    window_minutes = Column(Integer, default=60, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    cooldown_minutes = Column(Integer, default=60, nullable=False)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_akm_alert_key", api_key_id, is_active),
    )
    
    def __repr__(self) -> str:
        return f"<AKMAlertRule(id={self.id}, rule_name='{self.rule_name}')>"


class AKMAlertHistory(Base):
    """
    Model for alert trigger history.
    """
    __tablename__ = "akm_alert_history"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    alert_rule_id = Column(Integer, ForeignKey("akm_alert_rules.id", ondelete="CASCADE"), nullable=False)
    api_key_id = Column(Integer, nullable=False, index=True)
    
    metric_value = Column(Integer, nullable=False)
    threshold_value = Column(Integer, nullable=False)
    message = Column(Text, nullable=True)
    
    webhook_delivery_id = Column(Integer, ForeignKey("akm_webhook_deliveries.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_akm_alert_hist_rule", alert_rule_id, created_at),
    )
    
    def __repr__(self) -> str:
        return f"<AKMAlertHistory(id={self.id}, alert_rule_id={self.alert_rule_id})>"


class AKMAuditLog(Base):
    """
    Model for audit logging of all sensitive operations with integrity protection.
    
    Features:
    - Immutable audit trail with hash integrity verification
    - Correlation ID for tracking related operations
    - Microsecond precision timestamps
    - Complete request/response context
    - Project association for multi-tenancy
    """
    __tablename__ = "akm_audit_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Correlation and integrity
    correlation_id = Column(String(36), nullable=False, unique=True, index=True)  # UUID
    entry_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash for integrity
    
    # Authentication context
    api_key_id = Column(Integer, ForeignKey("akm_api_keys.id"), nullable=True, index=True)  # Nullable for unauthenticated attempts
    project_id = Column(Integer, ForeignKey("akm_projects.id"), nullable=True, index=True)  # For multi-tenancy filtering
    
    # Operation details
    operation = Column(String(100), nullable=False, index=True)  # e.g., "create_api_key", "delete_project"
    action = Column(String(50), nullable=False, index=True)  # HTTP method or action type
    resource_type = Column(String(50), nullable=False, index=True)  # e.g., "api_key", "project", "scope"
    resource_id = Column(String(100), nullable=True)  # Can be numeric or UUID
    
    # Request context
    endpoint = Column(String(255), nullable=False)  # Full endpoint path
    http_method = Column(String(10), nullable=False)  # GET, POST, PUT, DELETE, PATCH
    ip_address = Column(String(45), nullable=True, index=True)  # IPv6 support
    user_agent = Column(String(500), nullable=True)
    
    # Request/Response data
    request_payload = Column(JSON, nullable=True)  # Sanitized request body
    response_status = Column(Integer, nullable=True, index=True)  # HTTP status code
    response_payload = Column(JSON, nullable=True)  # Sanitized response body
    error_message = Column(Text, nullable=True)  # Error details if operation failed
    
    # Additional metadata
    extra_metadata = Column(JSON, nullable=True)  # Extra context (scopes used, rate limit info, etc.)
    
    # High-precision timestamps
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)  # Microsecond precision
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Status
    status = Column(String(20), nullable=False, default="success", index=True)  # success, failure, denied
    
    # Relationships
    api_key = relationship("AKMAPIKey", foreign_keys=[api_key_id])
    project = relationship("AKMProject", foreign_keys=[project_id])
    
    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_audit_timestamp", timestamp.desc()),  # Most common: recent first
        Index("idx_audit_project_time", project_id, timestamp.desc()),
        Index("idx_audit_key_time", api_key_id, timestamp.desc()),
        Index("idx_audit_operation", operation, timestamp.desc()),
        Index("idx_audit_resource", resource_type, resource_id, timestamp.desc()),
        Index("idx_audit_status", status, timestamp.desc()),
        Index("idx_audit_correlation", correlation_id),
        Index("idx_audit_hash", entry_hash),  # For integrity verification
    )
    
    def __repr__(self) -> str:
        return f"<AKMAuditLog(id={self.id}, correlation_id='{self.correlation_id}', operation='{self.operation}', status='{self.status}')>"
    
    def calculate_hash(self) -> str:
        """
        Calculate SHA-256 hash of audit entry for integrity verification.
        
        Hash includes all immutable fields to detect tampering.
        """
        hash_data = {
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "operation": self.operation,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "endpoint": self.endpoint,
            "http_method": self.http_method,
            "api_key_id": self.api_key_id,
            "project_id": self.project_id,
            "ip_address": self.ip_address,
            "request_payload": self.request_payload,
            "response_status": self.response_status,
            "status": self.status,
        }
        
        # Create deterministic JSON string
        hash_string = json.dumps(hash_data, sort_keys=True, default=str)
        
        # Calculate SHA-256 hash
        return hashlib.sha256(hash_string.encode('utf-8')).hexdigest()
    
    def verify_integrity(self) -> bool:
        """
        Verify the integrity of this audit log entry.
        
        Returns:
            bool: True if hash matches calculated hash, False if tampered
        """
        return self.entry_hash == self.calculate_hash()


class AKMSensitiveField(Base):
    """
    Control table for dynamic sensitive field sanitization.
    
    Supports global (project_id=NULL) and project-specific fields:
    - Global fields apply to ALL projects by default
    - Project-specific fields override or complement global fields
    - If a project defines the same field_name as global, project config takes precedence
    
    Fields allow configuring per-field sanitization strategy:
    - redact (replace entirely with replacement string)
    - mask (show only leading/trailing characters, mask middle with mask_char)
    If strategy-specific columns are NULL the global configuration is used.
    """
    __tablename__ = "akm_sensitive_fields"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("akm_projects.id", ondelete="CASCADE"), nullable=True, index=True)  # NULL = global
    field_name = Column(String(100), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    # Strategy override ("redact" | "mask")
    strategy = Column(String(20), nullable=True)
    
    # Masking configuration overrides
    mask_show_start = Column(Integer, nullable=True)
    mask_show_end = Column(Integer, nullable=True)
    mask_char = Column(String(1), nullable=True)
    
    # Replacement override for redact strategy
    replacement = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    project = relationship("AKMProject", backref="sensitive_fields")

    __table_args__ = (
        # Global fields: field_name must be unique when project_id IS NULL
        # Project fields: field_name must be unique per project
        UniqueConstraint("project_id", "field_name", name="uq_project_sensitive_field"),
        Index("idx_sensitive_field_active", "is_active"),
        Index("idx_sensitive_field_project", "project_id", "field_name"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        scope = "global" if self.project_id is None else f"project_{self.project_id}"
        return f"<AKMSensitiveField({scope}, field='{self.field_name}', strategy='{self.strategy}')>"


class AKMProjectConfiguration(Base):
    """
    Model for dynamic project configurations.
    
    Stores CORS origins, rate limits, IP allowlists, and other 
    runtime configurations that can be updated without code deployment.
    """
    __tablename__ = "akm_project_configurations"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("akm_projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # CORS Configuration (JSON array of allowed origins)
    cors_origins = Column(JSON, nullable=True, comment="Array of allowed CORS origins")
    
    # Rate Limiting Overrides
    default_rate_limit_per_minute = Column(Integer, nullable=True, comment="Default per-minute rate limit for project keys")
    default_rate_limit_per_hour = Column(Integer, nullable=True, comment="Default per-hour rate limit for project keys")
    default_rate_limit_per_day = Column(Integer, nullable=True, comment="Default per-day rate limit for project keys")
    default_rate_limit_per_month = Column(Integer, nullable=True, comment="Default per-month rate limit for project keys")
    
    # IP Allowlist (JSON array of CIDR ranges)
    ip_allowlist = Column(JSON, nullable=True, comment="Array of allowed IP addresses/CIDR ranges")
    
    # Webhook Configuration
    webhook_timeout_seconds = Column(Integer, default=30, nullable=False, comment="Webhook request timeout")
    webhook_max_retries = Column(Integer, default=3, nullable=False, comment="Maximum webhook retry attempts")
    
    # Custom Sensitive Fields (JSON array)
    custom_sensitive_fields = Column(JSON, nullable=True, comment="Project-specific sensitive field names")
    
    # Metadata
    config_metadata = Column(JSON, nullable=True, comment="Additional configuration metadata")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Relationships
    project = relationship("AKMProject", backref="configuration", uselist=False)
    
    def __repr__(self) -> str:
        return f"<AKMProjectConfiguration(project_id={self.project_id})>"

