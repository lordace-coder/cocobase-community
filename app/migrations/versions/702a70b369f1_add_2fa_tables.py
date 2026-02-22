"""add_2fa_tables

Revision ID: 702a70b369f1
Revises: 5c8e4a2b1f9d
Create Date: 2026-01-10 20:50:50.127406

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '702a70b369f1'
down_revision: Union[str, None] = '5c8e4a2b1f9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create 2FA tables."""
    # Create two_factor_codes table
    op.create_table(
        'two_factor_codes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('project_id', sa.String(255), nullable=False),
        sa.Column('code', sa.String(6), nullable=False),
        sa.Column('is_used', sa.Boolean(), default=False, nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_2fa_codes_user_id', 'two_factor_codes', ['user_id'])
    op.create_index('ix_2fa_codes_project_id', 'two_factor_codes', ['project_id'])

    # Create two_factor_settings table
    op.create_table(
        'two_factor_settings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('project_id', sa.String(255), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), default=False, nullable=False),
        sa.Column('backup_email', sa.String(255), nullable=True),
        sa.Column('last_verified_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_2fa_settings_user_id', 'two_factor_settings', ['user_id'], unique=True)
    op.create_index('ix_2fa_settings_project_id', 'two_factor_settings', ['project_id'])


def downgrade() -> None:
    """Drop 2FA tables."""
    op.drop_index('ix_2fa_settings_project_id', 'two_factor_settings')
    op.drop_index('ix_2fa_settings_user_id', 'two_factor_settings')
    op.drop_table('two_factor_settings')

    op.drop_index('ix_2fa_codes_project_id', 'two_factor_codes')
    op.drop_index('ix_2fa_codes_user_id', 'two_factor_codes')
    op.drop_table('two_factor_codes')
