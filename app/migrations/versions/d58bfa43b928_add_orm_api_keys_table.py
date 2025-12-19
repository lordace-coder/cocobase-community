"""add_orm_api_keys_table

Revision ID: d58bfa43b928
Revises: b1ed540e545c
Create Date: 2025-12-19 06:51:54.574502

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd58bfa43b928'
down_revision: Union[str, None] = 'b1ed540e545c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create orm_api_keys table."""
    op.create_table(
        'orm_api_keys',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('key_hash', sa.String(), nullable=False),
        sa.Column('key_prefix', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('permissions', postgresql.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_by', sa.String(), nullable=False),
        sa.Column('rate_limit', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
    )

    # Create indexes
    op.create_index('idx_orm_keys_project', 'orm_api_keys', ['project_id'])
    op.create_index('idx_orm_keys_prefix', 'orm_api_keys', ['key_prefix'])
    op.create_index('idx_orm_keys_active', 'orm_api_keys', ['is_active', 'project_id'])


def downgrade() -> None:
    """Drop orm_api_keys table."""
    op.drop_index('idx_orm_keys_active', table_name='orm_api_keys')
    op.drop_index('idx_orm_keys_prefix', table_name='orm_api_keys')
    op.drop_index('idx_orm_keys_project', table_name='orm_api_keys')
    op.drop_table('orm_api_keys')
