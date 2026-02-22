"""add_oauth_id_index_to_app_users

Revision ID: 44aaed3981b4
Revises: de7ecb288920
Create Date: 2025-11-15 16:34:52.666304

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '44aaed3981b4'
down_revision: Union[str, None] = 'de7ecb288920'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add index on oauth_id for faster OAuth login lookups
    op.create_index('ix_app_users_oauth_id', 'app_users', ['oauth_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove oauth_id index
    op.drop_index('ix_app_users_oauth_id', table_name='app_users')
