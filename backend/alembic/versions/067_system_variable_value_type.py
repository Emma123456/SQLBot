"""add value_type to system_variable

Revision ID: 067
Revises: 8adc3a4919be
Create Date: 2026-05-22

"""
from alembic import op
import sqlalchemy as sa

revision = '067'
down_revision = '8adc3a4919be'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('system_variable',
        sa.Column('value_type', sa.String(64), nullable=True, server_default='fixed')
    )
    op.add_column('system_variable',
        sa.Column('match_mode', sa.String(64), nullable=True, server_default='in')
    )


def downgrade() -> None:
    op.drop_column('system_variable', 'value_type')
    op.drop_column('system_variable', 'match_mode')
