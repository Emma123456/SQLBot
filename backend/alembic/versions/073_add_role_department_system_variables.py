"""073_add_role_department_system_variables

Revision ID: 073_add_role_department_system_variables
Revises: 072_add_oid_to_role_dept
Create Date: 2026-06-01 12:00:00.000000

"""
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op
from sqlalchemy import String, BigInteger, DateTime
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import table, column

# revision identifiers, used by Alembic.
revision = '073'
down_revision = '072'
branch_labels = None
depends_on = None


def upgrade():
    # Insert role and department system variables
    variable_table = table(
        "system_variable",
        column("id", BigInteger),
        column("name", String),
        column("var_type", String),
        column("type", String),
        column("value", JSONB),
        column("create_time", DateTime),
        column("create_by", BigInteger),
    )

    op.bulk_insert(
        variable_table,
        [
            {
                "name": "i18n_variable.role",
                "var_type": "list",
                "type": "system",
                "value": ["role"],
                "create_time": None,
                "create_by": None
            },
            {
                "name": "i18n_variable.department",
                "var_type": "list",
                "type": "system",
                "value": ["department"],
                "create_time": None,
                "create_by": None
            }
        ]
    )


def downgrade():
    # Remove role and department system variables
    op.execute(
        "DELETE FROM system_variable WHERE type='system' AND value IN ('[\"role\"]'::jsonb, '[\"department\"]'::jsonb)"
    )
