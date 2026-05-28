"""add ds_id to role/department/user_platform + oid to sync_datasource

Revision ID: 071
Revises: 070
Create Date: 2026-05-27

"""
from alembic import op
import sqlalchemy as sa

revision = '071'
down_revision = '070'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── sys_role: add ds_id, change unique constraint from (code) to (code, ds_id) ──
    op.add_column('sys_role', sa.Column('ds_id', sa.BigInteger(), nullable=False, server_default='0'))
    op.drop_constraint('sys_role_code_key', 'sys_role', type_='unique')
    op.drop_constraint('sys_role_name_key', 'sys_role', type_='unique')
    op.create_unique_constraint('uq_role_code_ds', 'sys_role', ['code', 'ds_id'])

    # ── sys_department: add ds_id, change unique constraint from (code) to (code, ds_id) ──
    op.add_column('sys_department', sa.Column('ds_id', sa.BigInteger(), nullable=False, server_default='0'))
    op.drop_constraint('sys_department_code_key', 'sys_department', type_='unique')
    op.create_unique_constraint('uq_dept_code_ds', 'sys_department', ['code', 'ds_id'])

    # ── sys_user_platform: add ds_id ──
    op.add_column('sys_user_platform', sa.Column('ds_id', sa.BigInteger(), nullable=False, server_default='0'))

    # ── sync_datasource: add oid ──
    op.add_column('sync_datasource', sa.Column('oid', sa.BigInteger(), nullable=False, server_default='1'))


def downgrade() -> None:
    # ── sync_datasource: drop oid ──
    op.drop_column('sync_datasource', 'oid')

    # ── sys_user_platform: drop ds_id ──
    op.drop_column('sys_user_platform', 'ds_id')

    # ── sys_department: revert unique constraint, drop ds_id ──
    op.drop_constraint('uq_dept_code_ds', 'sys_department', type_='unique')
    op.create_unique_constraint('sys_department_code_key', 'sys_department', ['code'])
    op.drop_column('sys_department', 'ds_id')

    # ── sys_role: revert unique constraints, drop ds_id ──
    op.drop_constraint('uq_role_code_ds', 'sys_role', type_='unique')
    op.create_unique_constraint('sys_role_name_key', 'sys_role', ['name'])
    op.create_unique_constraint('sys_role_code_key', 'sys_role', ['code'])
    op.drop_column('sys_role', 'ds_id')
