"""add sync tables and status column to sys_role/sys_department

Revision ID: 069
Revises: 068
Create Date: 2026-05-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '069'
down_revision = '068'
branch_labels = None
depends_on = None


def upgrade():
    # ── sync_datasource ─────────────────────────────────────────
    op.create_table(
        'sync_datasource',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('db_type', sa.String(32), nullable=False, server_default='mysql'),
        sa.Column('host', sa.String(255), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False, server_default='3306'),
        sa.Column('username', sa.String(255), nullable=False),
        sa.Column('password', sa.Text(), nullable=False),
        sa.Column('database', sa.String(255), nullable=False),
        sa.Column('db_schema', sa.String(128), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('cron_expression', sa.String(64), nullable=False, server_default=''),
        sa.Column('create_time', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── sync_table_mapping ──────────────────────────────────────
    op.create_table(
        'sync_table_mapping',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('ds_id', sa.BigInteger(), nullable=False),
        sa.Column('entity_type', sa.String(32), nullable=False),
        sa.Column('table_name', sa.String(128), nullable=False, server_default=''),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── sync_log ────────────────────────────────────────────────
    op.create_table(
        'sync_log',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('ds_id', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.String(16), nullable=False, server_default='running'),
        sa.Column('summary', JSONB(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('start_time', sa.BigInteger(), nullable=False),
        sa.Column('end_time', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── Add status column to sys_role ───────────────────────────
    op.add_column(
        'sys_role',
        sa.Column('status', sa.Integer(), nullable=False, server_default='0'),
    )

    # ── Add status column to sys_department ─────────────────────
    op.add_column(
        'sys_department',
        sa.Column('status', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade():
    # Remove status columns
    op.drop_column('sys_department', 'status')
    op.drop_column('sys_role', 'status')

    # Drop sync tables
    op.drop_table('sync_log')
    op.drop_table('sync_table_mapping')
    op.drop_table('sync_datasource')
