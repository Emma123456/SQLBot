from typing import Optional

from sqlalchemy import BigInteger, Boolean, Integer, UniqueConstraint
from sqlmodel import SQLModel, Field

from common.core.models import SnowflakeBase


class SysDepartmentBase(SQLModel):
    name: str = Field(max_length=128, nullable=False)
    code: str = Field(max_length=128, nullable=False)
    parent_id: int = Field(nullable=False, default=0, sa_type=BigInteger())
    origin: int = Field(nullable=False, default=0)
    ds_id: int = Field(default=0, sa_type=BigInteger())
    oid: int = Field(default=1, sa_type=BigInteger())
    status: int = Field(sa_type=Integer(), nullable=False, default=0)
    create_time: int = Field(sa_type=BigInteger(), nullable=False)


class SysDepartment(SnowflakeBase, SysDepartmentBase, table=True):
    __tablename__ = "sys_department"
    __table_args__ = (
        UniqueConstraint('code', 'ds_id', name='uq_dept_code_ds'),
    )


class SysUserDeptBase(SQLModel):
    uid: int = Field(nullable=False, sa_type=BigInteger())
    dept_id: int = Field(nullable=False, sa_type=BigInteger())
    is_primary: bool = Field(nullable=False, default=False, sa_type=Boolean())


class SysUserDept(SnowflakeBase, SysUserDeptBase, table=True):
    __tablename__ = "sys_user_dept"
    __table_args__ = (
        UniqueConstraint('uid', 'dept_id', name='uq_user_dept'),
    )
