"""Add sensitive fields control table

Revision ID: 004_add_sensitive_fields
Revises: 003_update_audit_logs
Create Date: 2025-11-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004_add_sensitive_fields'
down_revision: Union[str, None] = '003_update_audit_logs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create akm_sensitive_fields table for dynamic sanitization control."""
    op.create_table(
        'akm_sensitive_fields',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=False, unique=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('strategy', sa.String(length=20), nullable=True),  # redact | mask
        sa.Column('mask_show_start', sa.Integer(), nullable=True),
        sa.Column('mask_show_end', sa.Integer(), nullable=True),
        sa.Column('mask_char', sa.String(length=1), nullable=True),
        sa.Column('replacement', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index('idx_sensitive_field_name', 'akm_sensitive_fields', ['field_name'], unique=True)
    op.create_index('idx_sensitive_field_active', 'akm_sensitive_fields', ['is_active'], unique=False)


def downgrade() -> None:
    """Drop akm_sensitive_fields table."""
    op.drop_index('idx_sensitive_field_name', table_name='akm_sensitive_fields')
    op.drop_index('idx_sensitive_field_active', table_name='akm_sensitive_fields')
    op.drop_table('akm_sensitive_fields')
