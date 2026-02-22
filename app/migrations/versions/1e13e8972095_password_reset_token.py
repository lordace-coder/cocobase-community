"""password reset token

Revision ID: 1e13e8972095
Revises: c3f10ca343f3
Create Date: 2026-01-06 11:39:12.482392

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1e13e8972095'
down_revision: Union[str, None] = 'c3f10ca343f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    
    # COMPREHENSIVE DUPLICATE CLEANUP
    # (keep all the duplicate cleanup from before)
    
    # api_usage_counters: (project_id, month)
    op.execute("""
        DELETE FROM api_usage_counters a USING api_usage_counters b
        WHERE a.id < b.id AND a.project_id = b.project_id AND a.month = b.month
    """)
    
    # ai_usage_counters: (project_id, hour_bucket)
    op.execute("""
        DELETE FROM ai_usage_counters a USING ai_usage_counters b
        WHERE a.id < b.id AND a.project_id = b.project_id AND a.hour_bucket = b.hour_bucket
    """)
    
    # app_users: (client_id, email)
    op.execute("""
        DELETE FROM app_users a USING app_users b
        WHERE a.id < b.id AND a.client_id = b.client_id AND a.email = b.email
    """)
    
    # app_users: oauth_id
    op.execute("""
        DELETE FROM app_users a USING app_users b
        WHERE a.id < b.id AND a.oauth_id = b.oauth_id AND a.oauth_id IS NOT NULL
    """)
    
    # users: email
    op.execute("""
        DELETE FROM users a USING users b
        WHERE a.id < b.id AND a.email = b.email
    """)
    
    # users: google_id
    op.execute("""
        DELETE FROM users a USING users b
        WHERE a.id < b.id AND a.google_id = b.google_id AND a.google_id IS NOT NULL
    """)
    
    # projects: api_key
    op.execute("""
        DELETE FROM projects a USING projects b
        WHERE a.id < b.id AND a.api_key = b.api_key
    """)
    
    # pricing_plans: name
    op.execute("""
        DELETE FROM pricing_plans a USING pricing_plans b
        WHERE a.id < b.id AND a.name = b.name
    """)
    
    # integrations: name
    op.execute("""
        DELETE FROM integrations a USING integrations b
        WHERE a.id < b.id AND a.name = b.name
    """)
    
    # payments: reference
    op.execute("""
        DELETE FROM payments a USING payments b
        WHERE a.id < b.id AND a.reference = b.reference
    """)
    
    # cloud_functions: (project_id, name)
    op.execute("""
        DELETE FROM cloud_functions a USING cloud_functions b
        WHERE a.id < b.id AND a.project_id = b.project_id AND a.name = b.name
    """)
    
    # project_integrations: (project_id, integration_id)
    op.execute("""
        DELETE FROM project_integrations a USING project_integrations b
        WHERE a.id < b.id AND a.project_id = b.project_id AND a.integration_id = b.integration_id
    """)
    
    # route_hits: (route, created)
    op.execute("""
        DELETE FROM route_hits a USING route_hits b
        WHERE a.id < b.id AND a.route = b.route AND a.created = b.created
    """)
    
    # suggestion_likes: (user_id, suggestion_id)
    op.execute("""
        DELETE FROM suggestion_likes a USING suggestion_likes b
        WHERE a.id < b.id AND a.user_id = b.user_id AND a.suggestion_id = b.suggestion_id
    """)
    
    # ORPHANED DATA CLEANUP - Remove records referencing non-existent foreign keys
    
    # app_users -> projects (client_id)
    op.execute("""
        DELETE FROM app_users 
        WHERE client_id NOT IN (SELECT id FROM projects)
    """)
    
    # ai_conversations -> projects
    op.execute("""
        DELETE FROM ai_conversations 
        WHERE project_id NOT IN (SELECT id FROM projects)
    """)
    
    # ai_conversations -> users
    op.execute("""
        DELETE FROM ai_conversations 
        WHERE user_id NOT IN (SELECT id FROM users)
    """)
    
    # ai_usage_counters -> projects
    op.execute("""
        DELETE FROM ai_usage_counters 
        WHERE project_id NOT IN (SELECT id FROM projects)
    """)
    
    # api_usage_counters -> projects
    op.execute("""
        DELETE FROM api_usage_counters 
        WHERE project_id NOT IN (SELECT id FROM projects)
    """)
    
    # collections -> projects
    op.execute("""
        DELETE FROM collections 
        WHERE project_id NOT IN (SELECT id FROM projects)
    """)
    
    # documents -> collections
    op.execute("""
        DELETE FROM documents 
        WHERE collection_id NOT IN (SELECT id FROM collections)
    """)
    
    # cloud_functions -> projects
    op.execute("""
        DELETE FROM cloud_functions 
        WHERE project_id NOT IN (SELECT id FROM projects)
    """)
    
    # function_executions -> cloud_functions
    op.execute("""
        DELETE FROM function_executions 
        WHERE function_id NOT IN (SELECT id FROM cloud_functions)
    """)
    
    # payments -> users
    op.execute("""
        DELETE FROM payments 
        WHERE user_id NOT IN (SELECT id FROM users)
    """)
    
    # payments -> projects
    op.execute("""
        DELETE FROM payments 
        WHERE project_id NOT IN (SELECT id FROM projects)
    """)
    
    # payments -> pricing_plans
    op.execute("""
        DELETE FROM payments 
        WHERE plan_id NOT IN (SELECT id FROM pricing_plans)
    """)
    
    # payments -> project_subscriptions
    op.execute("""
        DELETE FROM payments 
        WHERE subscription_id IS NOT NULL 
        AND subscription_id NOT IN (SELECT id FROM project_subscriptions)
    """)
    
    # project_integrations -> projects
    op.execute("""
        DELETE FROM project_integrations 
        WHERE project_id NOT IN (SELECT id FROM projects)
    """)
    
    # project_integrations -> integrations
    op.execute("""
        DELETE FROM project_integrations 
        WHERE integration_id NOT IN (SELECT id FROM integrations)
    """)
    
    # project_shares -> users
    op.execute("""
        DELETE FROM project_shares 
        WHERE user_id NOT IN (SELECT id FROM users)
    """)
    
    # project_shares -> projects
    op.execute("""
        DELETE FROM project_shares 
        WHERE project_id NOT IN (SELECT id FROM projects)
    """)
    
    # project_subscriptions -> projects
    op.execute("""
        DELETE FROM project_subscriptions 
        WHERE project_id NOT IN (SELECT id FROM projects)
    """)
    
    # project_subscriptions -> pricing_plans
    op.execute("""
        DELETE FROM project_subscriptions 
        WHERE plan_id NOT IN (SELECT id FROM pricing_plans)
    """)
    
    # projects -> users
    op.execute("""
        DELETE FROM projects 
        WHERE user_id NOT IN (SELECT id FROM users)
    """)
    
    # suggestion_likes -> users
    op.execute("""
        DELETE FROM suggestion_likes 
        WHERE user_id NOT IN (SELECT id FROM users)
    """)
    
    # suggestion_likes -> suggestions
    op.execute("""
        DELETE FROM suggestion_likes 
        WHERE suggestion_id NOT IN (SELECT id FROM suggestions)
    """)
    
    # ### commands auto generated by Alembic - please adjust! ###
    # ... rest of migration
    op.create_table('app_users_password_reset_tokens',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('user_id', sa.String(), nullable=True),
    sa.Column('token', sa.String(), nullable=True),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.Column('is_used', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_app_users_password_reset_tokens_token'), 'app_users_password_reset_tokens', ['token'], unique=True)
    op.create_index(op.f('ix_app_users_password_reset_tokens_user_id'), 'app_users_password_reset_tokens', ['user_id'], unique=False)
    op.drop_index('idx_orm_keys_active', table_name='orm_api_keys')
    op.drop_index('idx_orm_keys_prefix', table_name='orm_api_keys')
    op.drop_index('idx_orm_keys_project', table_name='orm_api_keys')
    op.drop_table('orm_api_keys')
    op.create_index('idx_project_created', 'ai_conversations', ['project_id', 'created_at'], unique=False)
    op.create_index('idx_project_session', 'ai_conversations', ['project_id', 'session_id'], unique=False)
    op.create_index(op.f('ix_ai_conversations_created_at'), 'ai_conversations', ['created_at'], unique=False)
    op.create_index(op.f('ix_ai_conversations_id'), 'ai_conversations', ['id'], unique=False)
    op.create_index(op.f('ix_ai_conversations_project_id'), 'ai_conversations', ['project_id'], unique=False)
    op.create_index(op.f('ix_ai_conversations_session_id'), 'ai_conversations', ['session_id'], unique=False)
    op.create_index(op.f('ix_ai_conversations_user_id'), 'ai_conversations', ['user_id'], unique=False)
    op.create_foreign_key(None, 'ai_conversations', 'projects', ['project_id'], ['id'])
    op.create_foreign_key(None, 'ai_conversations', 'users', ['user_id'], ['id'])
    op.create_index('idx_project_hour', 'ai_usage_counters', ['project_id', 'hour_bucket'], unique=True)
    op.create_index(op.f('ix_ai_usage_counters_hour_bucket'), 'ai_usage_counters', ['hour_bucket'], unique=False)
    op.create_index(op.f('ix_ai_usage_counters_project_id'), 'ai_usage_counters', ['project_id'], unique=False)
    op.create_foreign_key(None, 'ai_usage_counters', 'projects', ['project_id'], ['id'])
    op.create_index('idx_project_month', 'api_usage_counters', ['project_id', 'month'], unique=True)
    op.create_index(op.f('ix_api_usage_counters_project_id'), 'api_usage_counters', ['project_id'], unique=False)
    op.alter_column('app_users', 'roles',
               existing_type=postgresql.ARRAY(sa.TEXT()),
               type_=postgresql.ARRAY(sa.String()),
               existing_nullable=True,
               existing_server_default=sa.text("'{}'::character varying[]"))
    op.create_index(op.f('ix_app_users_client_id'), 'app_users', ['client_id'], unique=False)
    op.create_index('ix_app_users_created_at', 'app_users', ['created_at'], unique=False)
    op.create_index('ix_app_users_data_gin', 'app_users', ['data'], unique=False, postgresql_using='gin', postgresql_ops={'data': 'jsonb_path_ops'})
    op.create_index('ix_app_users_oauth_id', 'app_users', ['oauth_id'], unique=False)
    op.create_unique_constraint('uq_client_email', 'app_users', ['client_id', 'email'])
    op.create_unique_constraint(None, 'app_users', ['oauth_id'])
    op.create_foreign_key(None, 'app_users', 'projects', ['client_id'], ['id'])
    op.create_unique_constraint('uq_project_function_name', 'cloud_functions', ['project_id', 'name'])
    op.create_foreign_key(None, 'cloud_functions', 'projects', ['project_id'], ['id'])
    op.create_index('idx_collection_project_id_name', 'collections', ['name', 'project_id'], unique=False)
    op.create_index(op.f('ix_collections_project_id'), 'collections', ['project_id'], unique=False)
    op.create_foreign_key(None, 'collections', 'projects', ['project_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_documents_collection_created', 'documents', ['collection_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_documents_collection_id'), 'documents', ['collection_id'], unique=False)
    op.create_index('ix_documents_created_at', 'documents', ['created_at'], unique=False)
    op.create_index('ix_documents_data_gin', 'documents', ['data'], unique=False, postgresql_using='gin', postgresql_ops={'data': 'jsonb_ops'})
    op.create_foreign_key(None, 'documents', 'collections', ['collection_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'function_executions', 'cloud_functions', ['function_id'], ['id'])
    op.create_unique_constraint(None, 'integrations', ['name'])
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
    op.create_index(op.f('ix_payments_id'), 'payments', ['id'], unique=False)
    op.create_index(op.f('ix_payments_reference'), 'payments', ['reference'], unique=True)
    op.create_index(op.f('ix_payments_status'), 'payments', ['status'], unique=False)
    op.create_foreign_key(None, 'payments', 'project_subscriptions', ['subscription_id'], ['id'])
    op.create_foreign_key(None, 'payments', 'pricing_plans', ['plan_id'], ['id'])
    op.create_foreign_key(None, 'payments', 'users', ['user_id'], ['id'])
    op.create_foreign_key(None, 'payments', 'projects', ['project_id'], ['id'])
    op.create_index(op.f('ix_pricing_plans_id'), 'pricing_plans', ['id'], unique=False)
    op.create_unique_constraint(None, 'pricing_plans', ['name'])
    op.create_index(op.f('ix_project_integrations_integration_id'), 'project_integrations', ['integration_id'], unique=False)
    op.create_index(op.f('ix_project_integrations_project_id'), 'project_integrations', ['project_id'], unique=False)
    op.create_unique_constraint('uq_project_integration', 'project_integrations', ['project_id', 'integration_id'])
    op.create_foreign_key(None, 'project_integrations', 'integrations', ['integration_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'project_integrations', 'projects', ['project_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'project_shares', 'users', ['user_id'], ['id'])
    op.create_foreign_key(None, 'project_shares', 'projects', ['project_id'], ['id'])
    op.create_index(op.f('ix_project_subscriptions_id'), 'project_subscriptions', ['id'], unique=False)
    op.create_foreign_key(None, 'project_subscriptions', 'pricing_plans', ['plan_id'], ['id'])
    op.create_foreign_key(None, 'project_subscriptions', 'projects', ['project_id'], ['id'])
    op.alter_column('projects', 'allowed_origins',
               existing_type=postgresql.ARRAY(sa.TEXT()),
               type_=postgresql.ARRAY(sa.String()),
               existing_nullable=True,
               existing_server_default=sa.text("'{}'::character varying[]"))
    op.create_index(op.f('ix_projects_user_id'), 'projects', ['user_id'], unique=False)
    op.create_unique_constraint(None, 'projects', ['api_key'])
    op.create_foreign_key(None, 'projects', 'users', ['user_id'], ['id'])
    op.create_unique_constraint('uq_route_created', 'route_hits', ['route', 'created'])
    op.create_unique_constraint('uq_user_suggestion', 'suggestion_likes', ['user_id', 'suggestion_id'])
    op.create_foreign_key(None, 'suggestion_likes', 'users', ['user_id'], ['id'])
    op.create_foreign_key(None, 'suggestion_likes', 'suggestions', ['suggestion_id'], ['id'])
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=False)
    op.create_unique_constraint(None, 'users', ['google_id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'users', type_='unique')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_constraint(None, 'suggestion_likes', type_='foreignkey')
    op.drop_constraint(None, 'suggestion_likes', type_='foreignkey')
    op.drop_constraint('uq_user_suggestion', 'suggestion_likes', type_='unique')
    op.drop_constraint('uq_route_created', 'route_hits', type_='unique')
    op.drop_constraint(None, 'projects', type_='foreignkey')
    op.drop_constraint(None, 'projects', type_='unique')
    op.drop_index(op.f('ix_projects_user_id'), table_name='projects')
    op.alter_column('projects', 'allowed_origins',
               existing_type=postgresql.ARRAY(sa.String()),
               type_=postgresql.ARRAY(sa.TEXT()),
               existing_nullable=True,
               existing_server_default=sa.text("'{}'::character varying[]"))
    op.drop_constraint(None, 'project_subscriptions', type_='foreignkey')
    op.drop_constraint(None, 'project_subscriptions', type_='foreignkey')
    op.drop_index(op.f('ix_project_subscriptions_id'), table_name='project_subscriptions')
    op.drop_constraint(None, 'project_shares', type_='foreignkey')
    op.drop_constraint(None, 'project_shares', type_='foreignkey')
    op.drop_constraint(None, 'project_integrations', type_='foreignkey')
    op.drop_constraint(None, 'project_integrations', type_='foreignkey')
    op.drop_constraint('uq_project_integration', 'project_integrations', type_='unique')
    op.drop_index(op.f('ix_project_integrations_project_id'), table_name='project_integrations')
    op.drop_index(op.f('ix_project_integrations_integration_id'), table_name='project_integrations')
    op.drop_constraint(None, 'pricing_plans', type_='unique')
    op.drop_index(op.f('ix_pricing_plans_id'), table_name='pricing_plans')
    op.drop_constraint(None, 'payments', type_='foreignkey')
    op.drop_constraint(None, 'payments', type_='foreignkey')
    op.drop_constraint(None, 'payments', type_='foreignkey')
    op.drop_constraint(None, 'payments', type_='foreignkey')
    op.drop_index(op.f('ix_payments_status'), table_name='payments')
    op.drop_index(op.f('ix_payments_reference'), table_name='payments')
    op.drop_index(op.f('ix_payments_id'), table_name='payments')
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_constraint(None, 'integrations', type_='unique')
    op.drop_constraint(None, 'function_executions', type_='foreignkey')
    op.drop_constraint(None, 'documents', type_='foreignkey')
    op.drop_index('ix_documents_data_gin', table_name='documents', postgresql_using='gin', postgresql_ops={'data': 'jsonb_ops'})
    op.drop_index('ix_documents_created_at', table_name='documents')
    op.drop_index(op.f('ix_documents_collection_id'), table_name='documents')
    op.drop_index('ix_documents_collection_created', table_name='documents')
    op.drop_constraint(None, 'collections', type_='foreignkey')
    op.drop_index(op.f('ix_collections_project_id'), table_name='collections')
    op.drop_index('idx_collection_project_id_name', table_name='collections')
    op.drop_constraint(None, 'cloud_functions', type_='foreignkey')
    op.drop_constraint('uq_project_function_name', 'cloud_functions', type_='unique')
    op.drop_constraint(None, 'app_users', type_='foreignkey')
    op.drop_constraint(None, 'app_users', type_='unique')
    op.drop_constraint('uq_client_email', 'app_users', type_='unique')
    op.drop_index('ix_app_users_oauth_id', table_name='app_users')
    op.drop_index('ix_app_users_data_gin', table_name='app_users', postgresql_using='gin', postgresql_ops={'data': 'jsonb_path_ops'})
    op.drop_index('ix_app_users_created_at', table_name='app_users')
    op.drop_index(op.f('ix_app_users_client_id'), table_name='app_users')
    op.alter_column('app_users', 'roles',
               existing_type=postgresql.ARRAY(sa.String()),
               type_=postgresql.ARRAY(sa.TEXT()),
               existing_nullable=True,
               existing_server_default=sa.text("'{}'::character varying[]"))
    op.drop_index(op.f('ix_api_usage_counters_project_id'), table_name='api_usage_counters')
    op.drop_index('idx_project_month', table_name='api_usage_counters')
    op.drop_constraint(None, 'ai_usage_counters', type_='foreignkey')
    op.drop_index(op.f('ix_ai_usage_counters_project_id'), table_name='ai_usage_counters')
    op.drop_index(op.f('ix_ai_usage_counters_hour_bucket'), table_name='ai_usage_counters')
    op.drop_index('idx_project_hour', table_name='ai_usage_counters')
    op.drop_constraint(None, 'ai_conversations', type_='foreignkey')
    op.drop_constraint(None, 'ai_conversations', type_='foreignkey')
    op.drop_index(op.f('ix_ai_conversations_user_id'), table_name='ai_conversations')
    op.drop_index(op.f('ix_ai_conversations_session_id'), table_name='ai_conversations')
    op.drop_index(op.f('ix_ai_conversations_project_id'), table_name='ai_conversations')
    op.drop_index(op.f('ix_ai_conversations_id'), table_name='ai_conversations')
    op.drop_index(op.f('ix_ai_conversations_created_at'), table_name='ai_conversations')
    op.drop_index('idx_project_session', table_name='ai_conversations')
    op.drop_index('idx_project_created', table_name='ai_conversations')
    op.create_table('orm_api_keys',
    sa.Column('id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('project_id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('key_hash', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('key_prefix', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('permissions', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('last_used_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('expires_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('is_active', sa.BOOLEAN(), server_default=sa.text('true'), autoincrement=False, nullable=True),
    sa.Column('created_by', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='orm_api_keys_created_by_fkey'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name='orm_api_keys_project_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='orm_api_keys_pkey')
    )
    op.create_index('idx_orm_keys_project', 'orm_api_keys', ['project_id'], unique=False)
    op.create_index('idx_orm_keys_prefix', 'orm_api_keys', ['key_prefix'], unique=False)
    op.create_index('idx_orm_keys_active', 'orm_api_keys', ['is_active', 'project_id'], unique=False)
    op.drop_index(op.f('ix_app_users_password_reset_tokens_user_id'), table_name='app_users_password_reset_tokens')
    op.drop_index(op.f('ix_app_users_password_reset_tokens_token'), table_name='app_users_password_reset_tokens')
    op.drop_table('app_users_password_reset_tokens')
    # ### end Alembic commands ###
