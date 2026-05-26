"""add role and department tables

Revision ID: 068
Revises: 067
Create Date: 2026-05-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '068'
down_revision = '067'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create sys_role table
    op.create_table('sys_role',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('code', sa.String(128), nullable=False),
        sa.Column('description', sa.String(512), nullable=True),
        sa.Column('origin', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('create_time', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('code')
    )
    
    # Create sys_department table
    op.create_table('sys_department',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('code', sa.String(128), nullable=False),
        sa.Column('parent_id', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('origin', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('create_time', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    
    # Create sys_user_role table
    op.create_table('sys_user_role',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('uid', sa.BigInteger(), nullable=False),
        sa.Column('role_id', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uid', 'role_id', name='uq_user_role')
    )
    
    # Create sys_user_dept table
    op.create_table('sys_user_dept',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('uid', sa.BigInteger(), nullable=False),
        sa.Column('dept_id', sa.BigInteger(), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uid', 'dept_id', name='uq_user_dept')
    )
    
    # Add role_list and dept_list to ds_rules table
    op.add_column('ds_rules',
        sa.Column('role_list', sa.Text(), nullable=True, server_default='[]')
    )
    op.add_column('ds_rules',
        sa.Column('dept_list', sa.Text(), nullable=True, server_default='[]')
    )
    
    # Add role_ids and dept_ids to sys_user table
    op.add_column('sys_user',
        sa.Column('role_ids', postgresql.JSONB(), nullable=True, server_default='[]')
    )
    op.add_column('sys_user',
        sa.Column('dept_ids', postgresql.JSONB(), nullable=True, server_default='[]')
    )


def downgrade() -> None:
    # Remove role_ids and dept_ids from sys_user table
    op.drop_column('sys_user', 'role_ids')
    op.drop_column('sys_user', 'dept_ids')
    
    # Remove role_list and dept_list from ds_rules table
    op.drop_column('ds_rules', 'role_list')
    op.drop_column('ds_rules', 'dept_list')
    
    # Drop tables in reverse order
    op.drop_table('sys_user_dept')
    op.drop_table('sys_user_role')
    op.drop_table('sys_department')
    op.drop_table('sys_role')
