from typing import Optional, List

from sqlalchemy import BigInteger, Boolean, Column, Identity, Text, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import SQLModel, Field

from common.utils.time import get_timestamp


# ── SyncDatasource ──────────────────────────────────────────────

class SyncDatasourceBase(SQLModel):
    name: str = Field(max_length=128, nullable=False)
    db_type: str = Field(max_length=32, nullable=False, default="mysql")
    host: str = Field(max_length=255, nullable=False)
    port: int = Field(nullable=False, default=3306)
    username: str = Field(max_length=255, nullable=False)
    password: str = Field(sa_column=Column(Text, nullable=False))
    database: str = Field(max_length=255, nullable=False)
    db_schema: Optional[str] = Field(max_length=128, default=None, nullable=True)
    enabled: bool = Field(default=True, sa_column=Column(Boolean, nullable=False, server_default="true"))
    cron_expression: str = Field(max_length=64, nullable=False, default="")
    oid: int = Field(sa_type=BigInteger(), nullable=False, default=1)
    create_time: int = Field(sa_type=BigInteger(), nullable=False, default_factory=get_timestamp)


class SyncDatasource(SyncDatasourceBase, table=True):
    __tablename__ = "sync_datasource"
    id: Optional[int] = Field(
        sa_column=Column(BigInteger, Identity(), primary_key=True)
    )


# ── SyncTableMapping ────────────────────────────────────────────

ENTITY_TYPES = ("user", "department", "role", "user_dept", "user_role")


class SyncTableMappingBase(SQLModel):
    ds_id: int = Field(nullable=False, sa_type=BigInteger())
    entity_type: str = Field(max_length=32, nullable=False)
    table_name: str = Field(max_length=128, nullable=False, default="")
    enabled: bool = Field(default=True, sa_column=Column(Boolean, nullable=False, server_default="true"))


class SyncTableMapping(SyncTableMappingBase, table=True):
    __tablename__ = "sync_table_mapping"
    id: Optional[int] = Field(
        sa_column=Column(BigInteger, Identity(), primary_key=True)
    )


# ── SyncLog ─────────────────────────────────────────────────────

class SyncLogBase(SQLModel):
    ds_id: int = Field(nullable=False, sa_type=BigInteger())
    status: str = Field(max_length=16, nullable=False, default="running")
    summary: Optional[dict] = Field(default=None, sa_column=Column(JSONB, nullable=True))
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    start_time: int = Field(sa_type=BigInteger(), nullable=False, default_factory=get_timestamp)
    end_time: Optional[int] = Field(default=None, sa_type=BigInteger())


class SyncLog(SyncLogBase, table=True):
    __tablename__ = "sync_log"
    id: Optional[int] = Field(
        sa_column=Column(BigInteger, Identity(), primary_key=True)
    )


# ── Pydantic DTOs ───────────────────────────────────────────────

class SyncDatasourceCreate(SQLModel):
    name: str
    db_type: str = "mysql"
    host: str
    port: int = 3306
    username: str
    password: str
    database: str
    db_schema: Optional[str] = None
    enabled: bool = True
    cron_expression: str = ""
    oid: int = 1


class SyncDatasourceUpdate(SQLModel):
    id: int
    name: Optional[str] = None
    db_type: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None
    db_schema: Optional[str] = None
    enabled: Optional[bool] = None
    cron_expression: Optional[str] = None
    oid: Optional[int] = None


class SyncTableMappingUpdate(SQLModel):
    """DTO for updating a single table mapping row."""
    entity_type: str
    table_name: str = ""
    enabled: bool = True


class SyncScheduleUpdate(SQLModel):
    cron_expression: str
