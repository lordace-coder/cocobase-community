"""Add analytics performance indexes

Revision ID: analytics_indexes_001
Revises:
Create Date: 2025-11-05

This migration adds critical indexes for analytics query performance.
Expected improvement: 50-70% faster analytics queries.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "analytics_indexes_001"
down_revision = None  # Replace with your latest revision
branch_labels = None
depends_on = None


def upgrade():
    """Create analytics performance indexes"""

    # Documents indexes
    op.create_index(
        "idx_documents_created_at",
        "documents",
        ["created_at"],
        postgresql_using="btree",
        if_not_exists=True,
    )

    op.create_index(
        "idx_documents_collection_created",
        "documents",
        ["collection_id", "created_at"],
        postgresql_using="btree",
        if_not_exists=True,
    )

    # App Users indexes
    op.create_index(
        "idx_app_users_client_created",
        "app_users",
        ["client_id", "created_at"],
        postgresql_using="btree",
        if_not_exists=True,
    )

    op.create_index(
        "idx_app_users_created",
        "app_users",
        ["created_at"],
        postgresql_using="btree",
        if_not_exists=True,
    )

    # Function Executions indexes
    op.create_index(
        "idx_function_executions_created",
        "function_executions",
        ["created_at"],
        postgresql_using="btree",
        if_not_exists=True,
    )

    op.create_index(
        "idx_function_executions_function_created",
        "function_executions",
        ["function_id", "created_at"],
        postgresql_using="btree",
        if_not_exists=True,
    )

    op.create_index(
        "idx_function_executions_status",
        "function_executions",
        ["status"],
        postgresql_using="btree",
        if_not_exists=True,
    )

    # Payments indexes
    op.create_index(
        "idx_payments_project_status",
        "payments",
        ["project_id", "status"],
        postgresql_using="btree",
        if_not_exists=True,
    )

    op.create_index(
        "idx_payments_paid_at",
        "payments",
        ["paid_at"],
        postgresql_using="btree",
        postgresql_where=sa.text("paid_at IS NOT NULL"),
        if_not_exists=True,
    )

    # Cloud Functions indexes
    op.create_index(
        "idx_cloud_functions_project",
        "cloud_functions",
        ["project_id"],
        postgresql_using="btree",
        if_not_exists=True,
    )

    # API Usage Counter indexes
    op.create_index(
        "idx_api_usage_project_month",
        "api_usage_counters",
        ["project_id", "month"],
        unique=True,
        if_not_exists=True,
    )

    # Project Subscriptions indexes
    op.create_index(
        "idx_project_subscriptions_project_active",
        "project_subscriptions",
        ["project_id", "is_active"],
        postgresql_using="btree",
        postgresql_where=sa.text("is_active = true"),
        if_not_exists=True,
    )

    print("✅ Analytics indexes created successfully!")


def downgrade():
    """Remove analytics performance indexes"""

    # Drop all indexes in reverse order
    op.drop_index(
        "idx_project_subscriptions_project_active",
        table_name="project_subscriptions",
        if_exists=True,
    )
    op.drop_index(
        "idx_api_usage_project_month", table_name="api_usage_counters", if_exists=True
    )
    op.drop_index(
        "idx_cloud_functions_project", table_name="cloud_functions", if_exists=True
    )
    op.drop_index("idx_payments_paid_at", table_name="payments", if_exists=True)
    op.drop_index("idx_payments_project_status", table_name="payments", if_exists=True)
    op.drop_index(
        "idx_function_executions_status",
        table_name="function_executions",
        if_exists=True,
    )
    op.drop_index(
        "idx_function_executions_function_created",
        table_name="function_executions",
        if_exists=True,
    )
    op.drop_index(
        "idx_function_executions_created",
        table_name="function_executions",
        if_exists=True,
    )
    op.drop_index("idx_app_users_created", table_name="app_users", if_exists=True)
    op.drop_index(
        "idx_app_users_client_created", table_name="app_users", if_exists=True
    )
    op.drop_index(
        "idx_documents_collection_created", table_name="documents", if_exists=True
    )
    op.drop_index("idx_documents_created_at", table_name="documents", if_exists=True)

    print("✅ Analytics indexes removed successfully!")
