"""add_storage_tracking_to_projects

Revision ID: de7ecb288920
Revises: 16c863318ea0
Create Date: 2025-11-15 16:31:53.182579

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de7ecb288920'
down_revision: Union[str, None] = '16c863318ea0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add storage tracking columns to projects table
    op.add_column('projects', sa.Column('storage_used_bytes', sa.BigInteger(), server_default='0', nullable=True))
    op.add_column('projects', sa.Column('storage_last_updated', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove storage tracking columns
    op.drop_column('projects', 'storage_last_updated')
    op.drop_column('projects', 'storage_used_bytes')
