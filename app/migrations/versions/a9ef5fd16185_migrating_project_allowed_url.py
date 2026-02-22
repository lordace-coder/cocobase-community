"""migrating project allowed url

Revision ID: a9ef5fd16185
Revises: d201486f3935
Create Date: 2025-11-09 01:17:44.352905

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pickle

# revision identifiers, used by Alembic.
revision: str = 'a9ef5fd16185'
down_revision: Union[str, None] = 'd201486f3935'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    # Step 1: Add temporary column for new array data
    op.add_column('projects', sa.Column('allowed_origins_new', postgresql.ARRAY(sa.String()), nullable=True))
    
    # Step 2: Migrate data from pickled bytes to array
    connection = op.get_bind()
    
    # Get all projects with allowed_origins
    result = connection.execute(sa.text("SELECT id, allowed_origins FROM projects WHERE allowed_origins IS NOT NULL"))
    
    migrated_count = 0
    error_count = 0
    
    for row in result:
        project_id, pickled_origins = row
        
        try:
            if pickled_origins:
                # Unpickle the bytes data
                origins_list = pickle.loads(bytes(pickled_origins))
                
                # Ensure it's a list
                if not isinstance(origins_list, list):
                    origins_list = [origins_list] if origins_list else []
                
                # Update the new column
                connection.execute(
                    sa.text("UPDATE projects SET allowed_origins_new = :origins WHERE id = :id"),
                    {"origins": origins_list, "id": project_id}
                )
                migrated_count += 1
                print(f"✅ Migrated project {project_id}: {origins_list}")
        except Exception as e:
            error_count += 1
            print(f"❌ Error migrating project {project_id}: {e}")
            # Set empty array on error
            connection.execute(
                sa.text("UPDATE projects SET allowed_origins_new = '{}' WHERE id = :id"),
                {"id": project_id}
            )
    
    # Step 3: Set empty arrays for NULL values
    connection.execute(sa.text("UPDATE projects SET allowed_origins_new = '{}' WHERE allowed_origins_new IS NULL"))
    
    # Step 4: Drop old column and rename new one
    op.drop_column('projects', 'allowed_origins')
    op.alter_column('projects', 'allowed_origins_new', new_column_name='allowed_origins')
    
    # Step 5: Set default for future inserts
    op.alter_column('projects', 'allowed_origins', server_default='{}')
    
    print(f"\n📊 Migration Summary:")
    print(f"   Migrated: {migrated_count}")
    print(f"   Errors: {error_count}")


def downgrade() -> None:
    """Downgrade schema."""
    
    # Step 1: Add temporary column for pickled data
    op.add_column('projects', sa.Column('allowed_origins_old', postgresql.BYTEA(), nullable=True))
    
    # Step 2: Convert array data back to pickled bytes
    connection = op.get_bind()
    
    result = connection.execute(sa.text("SELECT id, allowed_origins FROM projects WHERE allowed_origins IS NOT NULL"))
    
    for row in result:
        project_id, origins_array = row
        
        try:
            if origins_array:
                # Pickle the array data
                pickled_data = pickle.dumps(origins_array)
                
                # Update the old column
                connection.execute(
                    sa.text("UPDATE projects SET allowed_origins_old = :origins WHERE id = :id"),
                    {"origins": pickled_data, "id": project_id}
                )
                print(f"Downgraded project {project_id}: {origins_array}")
        except Exception as e:
            print(f"Error downgrading project {project_id}: {e}")
    
    # Step 3: Drop new column and rename old one
    op.drop_column('projects', 'allowed_origins')
    op.alter_column('projects', 'allowed_origins_old', new_column_name='allowed_origins')