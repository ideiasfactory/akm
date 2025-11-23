"""add_project_configurations_table

Revision ID: 0c36bd5048dc
Revises: 36af276ef713
Create Date: 2025-11-23 19:53:44.237918

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0c36bd5048dc'
down_revision: Union[str, None] = '36af276ef713'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create project configurations table
    op.create_table(
        'akm_project_configurations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('cors_origins', postgresql.JSON(astext_type=sa.Text()), nullable=True, 
                  comment='Array of allowed CORS origins'),
        sa.Column('default_rate_limit_per_minute', sa.Integer(), nullable=True, 
                  comment='Default per-minute rate limit for project keys'),
        sa.Column('default_rate_limit_per_hour', sa.Integer(), nullable=True, 
                  comment='Default per-hour rate limit for project keys'),
        sa.Column('default_rate_limit_per_day', sa.Integer(), nullable=True, 
                  comment='Default per-day rate limit for project keys'),
        sa.Column('default_rate_limit_per_month', sa.Integer(), nullable=True, 
                  comment='Default per-month rate limit for project keys'),
        sa.Column('ip_allowlist', postgresql.JSON(astext_type=sa.Text()), nullable=True, 
                  comment='Array of allowed IP addresses/CIDR ranges'),
        sa.Column('webhook_timeout_seconds', sa.Integer(), nullable=False, server_default='30', 
                  comment='Webhook request timeout'),
        sa.Column('webhook_max_retries', sa.Integer(), nullable=False, server_default='3', 
                  comment='Maximum webhook retry attempts'),
        sa.Column('custom_sensitive_fields', postgresql.JSON(astext_type=sa.Text()), nullable=True, 
                  comment='Project-specific sensitive field names'),
        sa.Column('config_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True, 
                  comment='Additional configuration metadata'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['akm_projects.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('project_id', name='uq_project_configuration')
    )
    
    # Create index for faster lookups
    op.create_index('idx_project_config_project', 'akm_project_configurations', ['project_id'])


def downgrade() -> None:
    # Drop index
    op.drop_index('idx_project_config_project', table_name='akm_project_configurations')
    
    # Drop table
    op.drop_table('akm_project_configurations')

