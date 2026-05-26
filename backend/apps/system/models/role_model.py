from typing import Optional

from sqlalchemy import BigInteger, UniqueConstraint
from sqlmodel import SQLModel, Field

from common.core.models import SnowflakeBase


class SysRoleBase(SQLModel):
    name: str = Field(max_length=128, nullable=False, unique=True)
    code: str = Field(max_length=128, nullable=False, unique=True)
    description: Optional[str] = Field(max_length=512, default=None)
    origin: int = Field(nullable=False, default=0)
    create_time: int = Field(sa_type=BigInteger(), nullable=False)


class SysRole(SnowflakeBase, SysRoleBase, table=True):
    __tablename__ = "sys_role"


class SysUserRoleBase(SQLModel):
    uid: int = Field(nullable=False, sa_type=BigInteger())
    role_id: int = Field(nullable=False, sa_type=BigInteger())


class SysUserRole(SnowflakeBase, SysUserRoleBase, table=True):
    __tablename__ = "sys_user_role"
    __table_args__ = (
        UniqueConstraint('uid', 'role_id', name='uq_user_role'),
    )
