"""update_orm_keys_and_pricing_for_rate_limits

Revision ID: c3f10ca343f3
Revises: d58bfa43b928
Create Date: 2025-12-19 07:12:38.495239

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f10ca343f3'
down_revision: Union[str, None] = 'd58bfa43b928'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add orm_rate_limit to pricing_plans and remove rate_limit from orm_api_keys.
    Rate limits will now be determined by the project's pricing plan.
    """
    # Add orm_rate_limit column to pricing_plans
    op.add_column('pricing_plans', sa.Column('orm_rate_limit', sa.Integer(), nullable=True))

    # Remove rate_limit column from orm_api_keys
    op.drop_column('orm_api_keys', 'rate_limit')


def downgrade() -> None:
    """Rollback changes."""
    # Add back rate_limit column to orm_api_keys
    op.add_column('orm_api_keys', sa.Column('rate_limit', sa.Integer(), nullable=True))

    # Remove orm_rate_limit column from pricing_plans
    op.drop_column('pricing_plans', 'orm_rate_limit')
