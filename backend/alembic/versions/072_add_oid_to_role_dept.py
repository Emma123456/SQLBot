"""add oid to sys_role and sys_department

Revision ID: 072
Revises: 071
Create Date: 2026-05-28

"""
from alembic import op
import sqlalchemy as sa

revision = '072'
down_revision = '071'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── sys_role: add oid ──
    op.add_column('sys_role', sa.Column('oid', sa.BigInteger(), nullable=False, server_default='1'))

    # ── sys_department: add oid ──
    op.add_column('sys_department', sa.Column('oid', sa.BigInteger(), nullable=False, server_default='1'))

    # ── Backfill: update existing sync-originated records with oid from their datasource ──
    # Only update records where origin=10 (db_sync) and ds_id matches a sync_datasource
    op.execute("""
        UPDATE sys_role r
        SET oid = ds.oid
        FROM sync_datasource ds
        WHERE r.ds_id = ds.id AND r.origin = 10 AND r.oid = 1
    """)
    op.execute("""
        UPDATE sys_department d
        SET oid = ds.oid
        FROM sync_datasource ds
        WHERE d.ds_id = ds.id AND d.origin = 10 AND d.oid = 1
    """)


def downgrade() -> None:
    # ── sys_department: drop oid ──
    op.drop_column('sys_department', 'oid')

    # ── sys_role: drop oid ──
    op.drop_column('sys_role', 'oid')
