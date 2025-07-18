"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    task_status_enum = postgresql.ENUM(
        'pending', 'processing', 'completed', 'failed', 'cancelled',
        name='taskstatusenum'
    )
    task_status_enum.create(op.get_bind())
    
    storage_policy_enum = postgresql.ENUM(
        'permanent', 'temporary',
        name='storagepolicyenum'
    )
    storage_policy_enum.create(op.get_bind())
    
    # Create tasks table
    op.create_table(
        'tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(255), nullable=False, index=True),
        sa.Column('parent_task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tasks.id', ondelete='CASCADE'), nullable=True),
        sa.Column('status', task_status_enum, nullable=False, default='pending', index=True),
        sa.Column('task_type', sa.String(50), nullable=False),
        sa.Column('file_url', sa.Text, nullable=True),
        sa.Column('original_filename', sa.String(255), nullable=True),
        sa.Column('options', postgresql.JSON, nullable=False, default=sa.text("'{}'::json")),
        sa.Column('estimated_cost', sa.DECIMAL(10, 4), nullable=True),
        sa.Column('actual_cost', sa.DECIMAL(10, 4), nullable=True),
        sa.Column('results', postgresql.JSON, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Create file_metadata table
    op.create_table(
        'file_metadata',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('file_type', sa.String(50), nullable=False),
        sa.Column('file_size', sa.BigInteger, nullable=False),
        sa.Column('storage_path', sa.Text, nullable=False),
        sa.Column('storage_policy', storage_policy_enum, nullable=False, default='temporary'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # Create indexes
    op.create_index('idx_tasks_parent_task_id', 'tasks', ['parent_task_id'])
    
    # Create trigger function for updating updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Create trigger
    op.execute("""
        CREATE TRIGGER update_tasks_updated_at 
            BEFORE UPDATE ON tasks 
            FOR EACH ROW 
            EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    # Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS update_tasks_updated_at ON tasks;")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
    
    # Drop indexes
    op.drop_index('idx_tasks_parent_task_id', 'tasks')
    
    # Drop tables
    op.drop_table('file_metadata')
    op.drop_table('tasks')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS storagepolicyenum;")
    op.execute("DROP TYPE IF EXISTS taskstatusenum;")