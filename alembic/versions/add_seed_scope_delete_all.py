"""
Alembic seed migration to add akm:scopes:delete_all scope to all projects.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String, Integer, Boolean

# revision identifiers, used by Alembic.
revision = 'add_seed_scope_delete_all'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    connection = op.get_bind()
    akm_scopes = table(
        'akm_scopes',
        column('project_id', Integer),
        column('scope_name', String),
        column('description', String),
        column('is_active', Boolean)
    )
    # Insert for all projects
    projects = connection.execute(sa.text('SELECT id FROM akm_projects')).fetchall()
    for project in projects:
        connection.execute(
            akm_scopes.insert().values(
                project_id=project.id,
                scope_name='akm:scopes:delete_all',
                description='Bulk delete all scopes for a project',
                is_active=True
            )
        )

def downgrade():
    connection = op.get_bind()
    connection.execute(
        sa.text("DELETE FROM akm_scopes WHERE scope_name = 'akm:scopes:delete_all'")
    )
