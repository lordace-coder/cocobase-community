"""migrating user roles

Revision ID: d201486f3935
Revises: 7d178b12f129
Create Date: 2025-11-09 00:24:41.171060

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pickle

# revision identifiers, used by Alembic.
revision: str = 'd201486f3935'
down_revision: Union[str, None] = '7d178b12f129'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    # Step 1: Add temporary column for new array data
    op.add_column('app_users', sa.Column('roles_new', postgresql.ARRAY(sa.String()), nullable=True))
    
    # Step 2: Migrate data from pickled bytes to array
    connection = op.get_bind()
    
    # Get all users with roles
    result = connection.execute(sa.text("SELECT id, roles FROM app_users WHERE roles IS NOT NULL"))
    
    for row in result:
        user_id, pickled_roles = row
        
        try:
            # Unpickle the bytes data
            if pickled_roles:
                roles_list = pickle.loads(bytes(pickled_roles))
                
                # Ensure it's a list
                if not isinstance(roles_list, list):
                    roles_list = [roles_list]
                
                # Update the new column
                connection.execute(
                    sa.text("UPDATE app_users SET roles_new = :roles WHERE id = :id"),
                    {"roles": roles_list, "id": user_id}
                )
                print(f"Migrated user {user_id}: {roles_list}")
        except Exception as e:
            print(f"Error migrating user {user_id}: {e}")
            # Set empty array on error
            connection.execute(
                sa.text("UPDATE app_users SET roles_new = '{}' WHERE id = :id"),
                {"id": user_id}
            )
    
    # Step 3: Set empty arrays for NULL values
    connection.execute(sa.text("UPDATE app_users SET roles_new = '{}' WHERE roles_new IS NULL"))
    
    # Step 4: Drop old column and rename new one
    op.drop_column('app_users', 'roles')
    op.alter_column('app_users', 'roles_new', new_column_name='roles')
    
    # Step 5: Set default for future inserts
    op.alter_column('app_users', 'roles', server_default='{}')


def downgrade() -> None:
    """Downgrade schema."""
    
    # Step 1: Add temporary column for pickled data
    op.add_column('app_users', sa.Column('roles_old', postgresql.BYTEA(), nullable=True))
    
    # Step 2: Convert array data back to pickled bytes
    connection = op.get_bind()
    
    result = connection.execute(sa.text("SELECT id, roles FROM app_users WHERE roles IS NOT NULL"))
    
    for row in result:
        user_id, roles_array = row
        
        try:
            if roles_array:
                # Pickle the array data
                pickled_data = pickle.dumps(roles_array)
                
                # Update the old column
                connection.execute(
                    sa.text("UPDATE app_users SET roles_old = :roles WHERE id = :id"),
                    {"roles": pickled_data, "id": user_id}
                )
                print(f"Downgraded user {user_id}: {roles_array}")
        except Exception as e:
            print(f"Error downgrading user {user_id}: {e}")
    
    # Step 3: Drop new column and rename old one
    op.drop_column('app_users', 'roles')
    op.alter_column('app_users', 'roles_old', new_column_name='roles')