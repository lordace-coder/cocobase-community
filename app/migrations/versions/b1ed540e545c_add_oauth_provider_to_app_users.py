"""add_oauth_provider_to_app_users

Revision ID: b1ed540e545c
Revises: 44aaed3981b4
Create Date: 2025-11-16 22:05:12.764855

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1ed540e545c'
down_revision: Union[str, None] = '44aaed3981b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add oauth_provider column to app_users table
    op.add_column('app_users', sa.Column('oauth_provider', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove oauth_provider column from app_users table
    op.drop_column('app_users', 'oauth_provider')
