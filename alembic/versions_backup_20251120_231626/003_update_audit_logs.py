"""Update audit logs with integrity features

Revision ID: 003_update_audit_logs
Revises: 002_create_akm_tables
Create Date: 2025-11-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_update_audit_logs'
down_revision: Union[str, None] = '002_create_akm_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade audit logs table with:
    - Correlation ID for operation tracking
    - Entry hash for integrity verification
    - Enhanced timestamps with microsecond precision
    - Project association for multi-tenancy
    - Additional context fields
    """
    
    # Drop old audit table if exists (fresh start with new schema)
    op.execute("DROP TABLE IF EXISTS akm_audit_logs CASCADE")
    
    # Create enhanced audit logs table
    op.create_table(
        'akm_audit_logs',
        
        # Primary key
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        
        # Correlation and integrity
        sa.Column('correlation_id', sa.String(length=36), nullable=False),
        sa.Column('entry_hash', sa.String(length=64), nullable=False),
        
        # Authentication context
        sa.Column('api_key_id', sa.Integer(), nullable=True),
        sa.Column('project_id', sa.Integer(), nullable=True),
        
        # Operation details
        sa.Column('operation', sa.String(length=100), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.String(length=100), nullable=True),
        
        # Request context
        sa.Column('endpoint', sa.String(length=255), nullable=False),
        sa.Column('http_method', sa.String(length=10), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        
        # Request/Response data
        sa.Column('request_payload', sa.JSON(), nullable=True),
        sa.Column('response_status', sa.Integer(), nullable=True),
        sa.Column('response_payload', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        
        # Additional metadata
        sa.Column('extra_metadata', sa.JSON(), nullable=True),
        
        # High-precision timestamps
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        # Status
        sa.Column('status', sa.String(length=20), nullable=False, server_default='success'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['api_key_id'], ['akm_api_keys.id'], name='fk_audit_api_key'),
        sa.ForeignKeyConstraint(['project_id'], ['akm_projects.id'], name='fk_audit_project'),
        
        # Primary key
        sa.PrimaryKeyConstraint('id', name='pk_akm_audit_logs')
    )
    
    # Create indexes for efficient querying
    op.create_index('idx_audit_timestamp', 'akm_audit_logs', ['timestamp'], unique=False, postgresql_using='btree', postgresql_ops={'timestamp': 'DESC'})
    op.create_index('idx_audit_project_time', 'akm_audit_logs', ['project_id', 'timestamp'], unique=False)
    op.create_index('idx_audit_key_time', 'akm_audit_logs', ['api_key_id', 'timestamp'], unique=False)
    op.create_index('idx_audit_operation', 'akm_audit_logs', ['operation', 'timestamp'], unique=False)
    op.create_index('idx_audit_resource', 'akm_audit_logs', ['resource_type', 'resource_id', 'timestamp'], unique=False)
    op.create_index('idx_audit_status', 'akm_audit_logs', ['status', 'timestamp'], unique=False)
    op.create_index('idx_audit_correlation', 'akm_audit_logs', ['correlation_id'], unique=True)
    op.create_index('idx_audit_hash', 'akm_audit_logs', ['entry_hash'], unique=False)
    op.create_index('idx_audit_api_key', 'akm_audit_logs', ['api_key_id'], unique=False)
    op.create_index('idx_audit_project', 'akm_audit_logs', ['project_id'], unique=False)
    op.create_index('idx_audit_ip', 'akm_audit_logs', ['ip_address'], unique=False)
    op.create_index('idx_audit_response_status', 'akm_audit_logs', ['response_status'], unique=False)


def downgrade() -> None:
    """
    Downgrade to previous audit logs schema.
    """
    # Drop enhanced audit table
    op.drop_table('akm_audit_logs')
    
    # Recreate simple audit table (if needed)
    op.create_table(
        'akm_audit_logs',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('api_key_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('request_payload', sa.JSON(), nullable=True),
        sa.Column('response_status', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_akm_audit_key', 'akm_audit_logs', ['api_key_id', 'created_at'], unique=False)
    op.create_index('idx_akm_audit_action', 'akm_audit_logs', ['action', 'created_at'], unique=False)
