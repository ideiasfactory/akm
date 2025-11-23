"""create akm tables

Revision ID: 002
Revises: 001
Create Date: 2025-11-20

Creates all tables for multi-project API key management:
- Projects, Scopes, API Keys with scopes
- Configurations (rate limits, IP whitelist, time restrictions)
- Rate limit buckets and usage metrics
- Webhooks, webhook events, subscriptions, deliveries
- Alert rules and alert history
- Audit logs
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_create_akm_tables'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create akm_projects table
    op.create_table(
        'akm_projects',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_akm_projects_id'), 'akm_projects', ['id'], unique=False)
    op.create_index(op.f('ix_akm_projects_is_active'), 'akm_projects', ['is_active'], unique=False)
    
    # Create akm_scopes table
    op.create_table(
        'akm_scopes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('scope_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('scope_name')
    )
    op.create_index(op.f('ix_akm_scopes_id'), 'akm_scopes', ['id'], unique=False)
    op.create_index(op.f('ix_akm_scopes_scope_name'), 'akm_scopes', ['scope_name'], unique=False)
    
    # Create akm_api_keys table
    op.create_table(
        'akm_api_keys',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('key_hash', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('request_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.ForeignKeyConstraint(['project_id'], ['akm_projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash')
    )
    op.create_index(op.f('ix_akm_api_keys_id'), 'akm_api_keys', ['id'], unique=False)
    op.create_index(op.f('ix_akm_api_keys_key_hash'), 'akm_api_keys', ['key_hash'], unique=False)
    op.create_index(op.f('ix_akm_api_keys_project_id'), 'akm_api_keys', ['project_id'], unique=False)
    op.create_index('idx_akm_key_hash_active', 'akm_api_keys', ['key_hash', 'is_active'], unique=False)
    op.create_index('idx_akm_key_project', 'akm_api_keys', ['project_id', 'is_active'], unique=False)
    
    # Create akm_api_key_scopes table
    op.create_table(
        'akm_api_key_scopes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('api_key_id', sa.Integer(), nullable=False),
        sa.Column('scope_name', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['api_key_id'], ['akm_api_keys.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['scope_name'], ['akm_scopes.scope_name'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('api_key_id', 'scope_name', name='uq_api_key_scope')
    )
    op.create_index(op.f('ix_akm_api_key_scopes_id'), 'akm_api_key_scopes', ['id'], unique=False)
    op.create_index('idx_akm_key_scope', 'akm_api_key_scopes', ['api_key_id', 'scope_name'], unique=False)
    
    # Create akm_api_key_configs table
    op.create_table(
        'akm_api_key_configs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('api_key_id', sa.Integer(), nullable=False),
        sa.Column('rate_limit_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('rate_limit_requests', sa.Integer(), nullable=True),
        sa.Column('rate_limit_window_seconds', sa.Integer(), nullable=True, server_default=sa.text('60')),
        sa.Column('daily_request_limit', sa.Integer(), nullable=True),
        sa.Column('monthly_request_limit', sa.Integer(), nullable=True),
        sa.Column('ip_whitelist_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('allowed_ips', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('allowed_time_start', sa.Time(), nullable=True),
        sa.Column('allowed_time_end', sa.Time(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['api_key_id'], ['akm_api_keys.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('api_key_id')
    )
    op.create_index(op.f('ix_akm_api_key_configs_id'), 'akm_api_key_configs', ['id'], unique=False)
    op.create_index(op.f('ix_akm_api_key_configs_api_key_id'), 'akm_api_key_configs', ['api_key_id'], unique=False)
    
    # Create akm_rate_limit_buckets table
    op.create_table(
        'akm_rate_limit_buckets',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('api_key_id', sa.Integer(), nullable=False),
        sa.Column('window_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('window_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('request_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['api_key_id'], ['akm_api_keys.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('api_key_id', 'window_start', name='uq_rate_bucket')
    )
    op.create_index(op.f('ix_akm_rate_limit_buckets_id'), 'akm_rate_limit_buckets', ['id'], unique=False)
    op.create_index('idx_akm_rate_bucket_window', 'akm_rate_limit_buckets', ['api_key_id', 'window_start', 'window_end'], unique=False)
    
    # Create akm_usage_metrics table
    op.create_table(
        'akm_usage_metrics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('api_key_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('hour', sa.Integer(), nullable=False),
        sa.Column('request_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('successful_requests', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('failed_requests', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('avg_response_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['api_key_id'], ['akm_api_keys.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('api_key_id', 'date', 'hour', name='uq_usage_metric')
    )
    op.create_index(op.f('ix_akm_usage_metrics_id'), 'akm_usage_metrics', ['id'], unique=False)
    op.create_index('idx_akm_usage_key_date', 'akm_usage_metrics', ['api_key_id', 'date'], unique=False)
    
    # Create akm_webhooks table
    op.create_table(
        'akm_webhooks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('api_key_id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('secret', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('retry_policy', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{"max_retries": 3, "backoff_seconds": [1, 5, 15]}'),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default=sa.text('30')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['api_key_id'], ['akm_api_keys.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_akm_webhooks_id'), 'akm_webhooks', ['id'], unique=False)
    op.create_index(op.f('ix_akm_webhooks_api_key_id'), 'akm_webhooks', ['api_key_id'], unique=False)
    
    # Create akm_webhook_events table
    op.create_table(
        'akm_webhook_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('payload_schema', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_type')
    )
    op.create_index(op.f('ix_akm_webhook_events_id'), 'akm_webhook_events', ['id'], unique=False)
    op.create_index(op.f('ix_akm_webhook_events_event_type'), 'akm_webhook_events', ['event_type'], unique=False)
    
    # Create akm_webhook_subscriptions table
    op.create_table(
        'akm_webhook_subscriptions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('webhook_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['event_type'], ['akm_webhook_events.event_type'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['webhook_id'], ['akm_webhooks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('webhook_id', 'event_type', name='uq_webhook_event')
    )
    op.create_index(op.f('ix_akm_webhook_subscriptions_id'), 'akm_webhook_subscriptions', ['id'], unique=False)
    op.create_index('idx_akm_webhook_sub', 'akm_webhook_subscriptions', ['webhook_id', 'event_type'], unique=False)
    
    # Create akm_webhook_deliveries table
    op.create_table(
        'akm_webhook_deliveries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('webhook_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('payload', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('http_status_code', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['webhook_id'], ['akm_webhooks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_akm_webhook_deliveries_id'), 'akm_webhook_deliveries', ['id'], unique=False)
    op.create_index(op.f('ix_akm_webhook_deliveries_status'), 'akm_webhook_deliveries', ['status'], unique=False)
    op.create_index('idx_akm_delivery_webhook', 'akm_webhook_deliveries', ['webhook_id', 'created_at'], unique=False)
    op.create_index('idx_akm_delivery_retry', 'akm_webhook_deliveries', ['status', 'next_retry_at'], unique=False)
    
    # Create akm_alert_rules table
    op.create_table(
        'akm_alert_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('api_key_id', sa.Integer(), nullable=False),
        sa.Column('rule_name', sa.String(length=100), nullable=False),
        sa.Column('metric_type', sa.String(length=50), nullable=False),
        sa.Column('threshold_value', sa.Integer(), nullable=False),
        sa.Column('threshold_percentage', sa.Integer(), nullable=True),
        sa.Column('comparison_operator', sa.String(length=10), nullable=False),
        sa.Column('window_minutes', sa.Integer(), nullable=False, server_default=sa.text('60')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('cooldown_minutes', sa.Integer(), nullable=False, server_default=sa.text('60')),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['api_key_id'], ['akm_api_keys.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_akm_alert_rules_id'), 'akm_alert_rules', ['id'], unique=False)
    op.create_index(op.f('ix_akm_alert_rules_api_key_id'), 'akm_alert_rules', ['api_key_id'], unique=False)
    op.create_index('idx_akm_alert_key', 'akm_alert_rules', ['api_key_id', 'is_active'], unique=False)
    
    # Create akm_webhook_deliveries foreign key to itself for alert history
    # Create akm_alert_history table
    op.create_table(
        'akm_alert_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('alert_rule_id', sa.Integer(), nullable=False),
        sa.Column('api_key_id', sa.Integer(), nullable=False),
        sa.Column('metric_value', sa.Integer(), nullable=False),
        sa.Column('threshold_value', sa.Integer(), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('webhook_delivery_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['alert_rule_id'], ['akm_alert_rules.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['webhook_delivery_id'], ['akm_webhook_deliveries.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_akm_alert_history_id'), 'akm_alert_history', ['id'], unique=False)
    op.create_index(op.f('ix_akm_alert_history_api_key_id'), 'akm_alert_history', ['api_key_id'], unique=False)
    op.create_index('idx_akm_alert_hist_rule', 'akm_alert_history', ['alert_rule_id', 'created_at'], unique=False)
    
    # Create akm_audit_logs table
    op.create_table(
        'akm_audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('api_key_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('request_payload', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('response_status', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_akm_audit_logs_id'), 'akm_audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_akm_audit_logs_api_key_id'), 'akm_audit_logs', ['api_key_id'], unique=False)
    op.create_index(op.f('ix_akm_audit_logs_action'), 'akm_audit_logs', ['action'], unique=False)
    op.create_index('idx_akm_audit_key', 'akm_audit_logs', ['api_key_id', 'created_at'], unique=False)
    op.create_index('idx_akm_audit_action', 'akm_audit_logs', ['action', 'created_at'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('idx_akm_audit_action', table_name='akm_audit_logs')
    op.drop_index('idx_akm_audit_key', table_name='akm_audit_logs')
    op.drop_index(op.f('ix_akm_audit_logs_action'), table_name='akm_audit_logs')
    op.drop_index(op.f('ix_akm_audit_logs_api_key_id'), table_name='akm_audit_logs')
    op.drop_index(op.f('ix_akm_audit_logs_id'), table_name='akm_audit_logs')
    op.drop_table('akm_audit_logs')
    
    op.drop_index('idx_akm_alert_hist_rule', table_name='akm_alert_history')
    op.drop_index(op.f('ix_akm_alert_history_api_key_id'), table_name='akm_alert_history')
    op.drop_index(op.f('ix_akm_alert_history_id'), table_name='akm_alert_history')
    op.drop_table('akm_alert_history')
    
    op.drop_index('idx_akm_alert_key', table_name='akm_alert_rules')
    op.drop_index(op.f('ix_akm_alert_rules_api_key_id'), table_name='akm_alert_rules')
    op.drop_index(op.f('ix_akm_alert_rules_id'), table_name='akm_alert_rules')
    op.drop_table('akm_alert_rules')
    
    op.drop_index('idx_akm_delivery_retry', table_name='akm_webhook_deliveries')
    op.drop_index('idx_akm_delivery_webhook', table_name='akm_webhook_deliveries')
    op.drop_index(op.f('ix_akm_webhook_deliveries_status'), table_name='akm_webhook_deliveries')
    op.drop_index(op.f('ix_akm_webhook_deliveries_id'), table_name='akm_webhook_deliveries')
    op.drop_table('akm_webhook_deliveries')
    
    op.drop_index('idx_akm_webhook_sub', table_name='akm_webhook_subscriptions')
    op.drop_index(op.f('ix_akm_webhook_subscriptions_id'), table_name='akm_webhook_subscriptions')
    op.drop_table('akm_webhook_subscriptions')
    
    op.drop_index(op.f('ix_akm_webhook_events_event_type'), table_name='akm_webhook_events')
    op.drop_index(op.f('ix_akm_webhook_events_id'), table_name='akm_webhook_events')
    op.drop_table('akm_webhook_events')
    
    op.drop_index(op.f('ix_akm_webhooks_api_key_id'), table_name='akm_webhooks')
    op.drop_index(op.f('ix_akm_webhooks_id'), table_name='akm_webhooks')
    op.drop_table('akm_webhooks')
    
    op.drop_index('idx_akm_usage_key_date', table_name='akm_usage_metrics')
    op.drop_index(op.f('ix_akm_usage_metrics_id'), table_name='akm_usage_metrics')
    op.drop_table('akm_usage_metrics')
    
    op.drop_index('idx_akm_rate_bucket_window', table_name='akm_rate_limit_buckets')
    op.drop_index(op.f('ix_akm_rate_limit_buckets_id'), table_name='akm_rate_limit_buckets')
    op.drop_table('akm_rate_limit_buckets')
    
    op.drop_index(op.f('ix_akm_api_key_configs_api_key_id'), table_name='akm_api_key_configs')
    op.drop_index(op.f('ix_akm_api_key_configs_id'), table_name='akm_api_key_configs')
    op.drop_table('akm_api_key_configs')
    
    op.drop_index('idx_akm_key_scope', table_name='akm_api_key_scopes')
    op.drop_index(op.f('ix_akm_api_key_scopes_id'), table_name='akm_api_key_scopes')
    op.drop_table('akm_api_key_scopes')
    
    op.drop_index('idx_akm_key_project', table_name='akm_api_keys')
    op.drop_index('idx_akm_key_hash_active', table_name='akm_api_keys')
    op.drop_index(op.f('ix_akm_api_keys_project_id'), table_name='akm_api_keys')
    op.drop_index(op.f('ix_akm_api_keys_key_hash'), table_name='akm_api_keys')
    op.drop_index(op.f('ix_akm_api_keys_id'), table_name='akm_api_keys')
    op.drop_table('akm_api_keys')
    
    op.drop_index(op.f('ix_akm_scopes_scope_name'), table_name='akm_scopes')
    op.drop_index(op.f('ix_akm_scopes_id'), table_name='akm_scopes')
    op.drop_table('akm_scopes')
    
    op.drop_index(op.f('ix_akm_projects_is_active'), table_name='akm_projects')
    op.drop_index(op.f('ix_akm_projects_id'), table_name='akm_projects')
    op.drop_table('akm_projects')
