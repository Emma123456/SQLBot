"""External database sync engine.

Reads data from external MySQL databases, upserts into SQLBot's
sys_user / sys_role / sys_department and their join tables,
refreshes redundant fields, and marks inactive entities.

Fixed mapping convention (external table → SQLBot columns):
  user:        id, name, email
  department:  code, name, parent_code
  role:        code, name
  user_dept:   user_id, dept_code, is_primary
  user_role:   user_id, role_code
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import create_engine, text
from sqlmodel import Session, delete, select

from apps.system.models.sync_model import (
    SyncDatasource,
    SyncTableMapping,
    SyncLog,
    ENTITY_TYPES,
)
from apps.system.models.role_model import SysRole, SysUserRole
from apps.system.models.department_model import SysDepartment, SysUserDept
from apps.system.models.user import UserModel, UserPlatformModel
from apps.system.models.system_model import UserWsModel
from apps.system.crud.user_role_dept import refresh_user_role_ids, refresh_user_dept_ids
from apps.datasource.utils.utils import aes_encrypt, aes_decrypt
from common.utils.time import get_timestamp
from common.utils.snowflake import snowflake

logger = logging.getLogger(__name__)

# ── constants ───────────────────────────────────────────────────

SYSTEM_ADMIN_UID = 1  # Built-in admin user, never modify/deactivate via sync


def _clean(val, default: str = "") -> str:
    """Convert None to empty string, strip whitespace."""
    if val is None:
        return default
    return str(val).strip()

# ── helpers ─────────────────────────────────────────────────────

DB_TYPE_SCHEMES = {
    "mysql": "mysql+pymysql://{username}:{password}@{host}:{port}/{database}",
}


def _build_uri(conf: SyncDatasource) -> str:
    """Build SQLAlchemy connection URI from a SyncDatasource config."""
    scheme = DB_TYPE_SCHEMES.get(conf.db_type)
    if not scheme:
        raise ValueError(f"Unsupported db_type: {conf.db_type}")
    decrypted_pwd = aes_decrypt(conf.password) if isinstance(conf.password, (bytes, str)) else conf.password
    # URL-encode password to handle special characters
    from urllib.parse import quote_plus
    return scheme.format(
        username=conf.username,
        password=quote_plus(str(decrypted_pwd)),
        host=conf.host,
        port=conf.port,
        database=conf.database,
    )


def get_external_engine(conf: SyncDatasource):
    """Create a SQLAlchemy engine for the external database."""
    uri = _build_uri(conf)
    return create_engine(uri, pool_pre_ping=True, connect_args={"connect_timeout": 10})


def read_external_table(engine, table_name: str) -> list[dict]:
    """Read all rows from an external table and return as list of dicts."""
    if not table_name:
        return []
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT * FROM {table_name}"))
        columns = result.keys()
        return [dict(zip(columns, row)) for row in result.fetchall()]


# ── upsert functions ────────────────────────────────────────────

def upsert_departments(
    session: Session,
    ext_rows: list[dict],
    origin: int = 10,
    ds_id: int = 0,
    oid: int = 1,
) -> tuple[dict[str, int], int, int]:
    """Upsert departments by code+ds_id. Returns (code->id map, created_count, updated_count)."""
    code_to_id: dict[str, int] = {}
    created = 0
    updated = 0

    for row in ext_rows:
        code = _clean(row.get("code"))
        name = _clean(row.get("name"))
        parent_code = _clean(row.get("parent_code"))
        if not code:
            continue

        existing = session.exec(
            select(SysDepartment).where(
                SysDepartment.code == code,
                SysDepartment.ds_id == ds_id,
            )
        ).first()

        if existing:
            existing.name = name
            # Resolve parent_id from parent_code
            if parent_code and parent_code in code_to_id:
                existing.parent_id = code_to_id[parent_code]
            elif not parent_code:
                existing.parent_id = 0
            # Datasource oid is the single source of truth
            existing.oid = oid
            session.add(existing)
            code_to_id[code] = existing.id
            updated += 1
        else:
            parent_id = 0
            if parent_code and parent_code in code_to_id:
                parent_id = code_to_id[parent_code]
            dept = SysDepartment(
                id=snowflake.generate_id(),
                name=name,
                code=code,
                parent_id=parent_id,
                origin=origin,
                ds_id=ds_id,
                oid=oid,
                status=1,  # synced data defaults to enabled
                create_time=get_timestamp(),
            )
            session.add(dept)
            session.flush()
            code_to_id[code] = dept.id
            created += 1

    return code_to_id, created, updated


def upsert_roles(
    session: Session,
    ext_rows: list[dict],
    origin: int = 10,
    ds_id: int = 0,
    oid: int = 1,
) -> tuple[dict[str, int], int, int]:
    """Upsert roles by code+ds_id. Returns (code->id map, created_count, updated_count)."""
    code_to_id: dict[str, int] = {}
    created = 0
    updated = 0

    for row in ext_rows:
        code = _clean(row.get("code"))
        name = _clean(row.get("name"))
        if not code:
            continue

        existing = session.exec(
            select(SysRole).where(
                SysRole.code == code,
                SysRole.ds_id == ds_id,
            )
        ).first()

        if existing:
            existing.name = name
            # Datasource oid is the single source of truth
            existing.oid = oid
            session.add(existing)
            code_to_id[code] = existing.id
            updated += 1
        else:
            role = SysRole(
                id=snowflake.generate_id(),
                name=name,
                code=code,
                origin=origin,
                ds_id=ds_id,
                oid=oid,
                status=1,  # synced data defaults to enabled
                create_time=get_timestamp(),
            )
            session.add(role)
            session.flush()
            code_to_id[code] = role.id
            created += 1

    return code_to_id, created, updated


def upsert_users(
    session: Session,
    ext_rows: list[dict],
    origin: int = 10,
    ds_id: int = 0,
    oid: int = 1,
) -> tuple[dict[str, int], int, int]:
    """Upsert users by platform_uid+ds_id. Returns (platform_uid->internal_id map, created_count, updated_count).

    Args:
        ds_id: Sync datasource ID for multi-source isolation.
        oid: Workspace ID to assign synced users to.
    """
    uid_map: dict[str, int] = {}
    created = 0
    updated = 0

    for row in ext_rows:
        ext_id = _clean(row.get("id"))
        name = _clean(row.get("name"), default=f"sync_user")
        email = _clean(row.get("email"))
        account = _clean(row.get("account"))
        if not account:
            account = name
        if not email:
            email = f"sync_{ext_id}@sync.local"
        if not ext_id:
            continue

        # Look up existing user via platform table (ds_id isolation)
        platform = session.exec(
            select(UserPlatformModel).where(
                UserPlatformModel.platform_uid == ext_id,
                UserPlatformModel.origin == origin,
                UserPlatformModel.ds_id == ds_id,
            )
        ).first()

        if platform:
            # Protect system admin user from being overwritten by sync
            if platform.uid == SYSTEM_ADMIN_UID:
                uid_map[ext_id] = platform.uid
                continue
            # Update existing user
            user = session.get(UserModel, platform.uid)
            if user:
                user.name = name
                user.email = email
                user.account = account
                # Datasource oid is the single source of truth
                # Remove old workspace membership before assigning new one
                if user.oid and user.oid != oid:
                    session.exec(
                        delete(UserWsModel).where(
                            UserWsModel.uid == user.id,
                            UserWsModel.oid == user.oid,
                        )
                    )
                user.oid = oid
                _ensure_user_ws(session, user.id, oid)
                session.add(user)
            uid_map[ext_id] = platform.uid
            updated += 1
        else:
            # Create new user + platform record
            from common.core.security import default_md5_pwd
            new_uid = snowflake.generate_id()
            user = UserModel(
                id=new_uid,
                account=account,
                name=name,
                email=email,
                password=default_md5_pwd(),
                origin=origin,
                oid=oid,
                status=1,  # synced data defaults to enabled
                create_time=get_timestamp(),
                role_ids=[],
                dept_ids=[],
            )
            session.add(user)
            session.flush()

            platform_record = UserPlatformModel(
                id=snowflake.generate_id(),
                uid=new_uid,
                origin=origin,
                platform_uid=ext_id,
                ds_id=ds_id,
            )
            session.add(platform_record)

            # Create sys_user_ws record for workspace membership
            _ensure_user_ws(session, new_uid, oid)

            uid_map[ext_id] = new_uid
            created += 1

    return uid_map, created, updated


# ── relation sync ───────────────────────────────────────────────

def _ensure_user_ws(session: Session, uid: int, oid: int) -> None:
    """Create sys_user_ws record if not already exists. Idempotent."""
    existing = session.exec(
        select(UserWsModel).where(
            UserWsModel.uid == uid,
            UserWsModel.oid == oid,
        )
    ).first()
    if not existing:
        ws_record = UserWsModel(
            id=snowflake.generate_id(),
            uid=uid,
            oid=oid,
            weight=0,
        )
        session.add(ws_record)


def sync_user_departments(
    session: Session,
    ext_rows: list[dict],
    user_map: dict[str, int],
    dept_map: dict[str, int],
    ds_id: int = 0,
) -> int:
    """Sync user-department relations. Uses upsert to avoid UniqueViolation.

    Only manages relations for departments belonging to the given ds_id.
    """
    synced = 0
    affected_uids: set[int] = set()

    # Collect all valid relations from external data
    valid_pairs: dict[tuple[int, int], bool] = {}  # (uid, dept_id) -> is_primary
    for row in ext_rows:
        ext_user_id = _clean(row.get("user_id"))
        dept_code = _clean(row.get("dept_code"))
        is_primary = bool(row.get("is_primary", False))

        uid = user_map.get(ext_user_id)
        dept_id = dept_map.get(dept_code)
        # Skip if uid is system admin
        if uid and uid == SYSTEM_ADMIN_UID:
            continue
        if uid and dept_id:
            valid_pairs[(uid, dept_id)] = is_primary
            affected_uids.add(uid)

    # Pre-load ALL existing (uid, dept_id) pairs for affected users to avoid UniqueViolation
    # This includes relations from any origin (local, OAuth2, etc.), not just DB Sync
    all_existing_pairs: set[tuple[int, int]] = set()
    for uid in affected_uids:
        rows = session.exec(
            select(SysUserDept.uid, SysUserDept.dept_id).where(SysUserDept.uid == uid)
        ).all()
        for r in rows:
            all_existing_pairs.add((r[0], r[1]))

    # For each affected user: upsert relations
    for uid in affected_uids:
        # Load existing user-dept relations for sync-originated depts in THIS datasource
        existing_rels = session.exec(
            select(SysUserDept).where(SysUserDept.uid == uid)
        ).all()
        existing_map: dict[tuple[int, int], SysUserDept] = {}
        to_delete: list[SysUserDept] = []
        for rel in existing_rels:
            dept = session.get(SysDepartment, rel.dept_id)
            all_existing_pairs.add((rel.uid, rel.dept_id))
            if dept and dept.origin == 10 and dept.ds_id == ds_id:
                existing_map[(rel.uid, rel.dept_id)] = rel
                # If this existing pair is NOT in new data, mark for deletion
                if (rel.uid, rel.dept_id) not in valid_pairs:
                    to_delete.append(rel)

        # Delete stale relations
        for rel in to_delete:
            session.delete(rel)
        session.flush()

        # Upsert: update existing or insert new
        for (u, d), is_primary in valid_pairs.items():
            if u == uid:
                existing = existing_map.get((u, d))
                if existing:
                    # Update is_primary if changed
                    existing.is_primary = is_primary
                    session.add(existing)
                else:
                    # Skip if relation already exists from any origin (avoid UniqueViolation)
                    if (u, d) in all_existing_pairs:
                        synced += 1
                        continue
                    new_rel = SysUserDept(
                        id=snowflake.generate_id(),
                        uid=u,
                        dept_id=d,
                        is_primary=is_primary,
                    )
                    session.add(new_rel)
                synced += 1

        # Refresh redundant field
        refresh_user_dept_ids(session, uid)

    return synced


def sync_user_roles(
    session: Session,
    ext_rows: list[dict],
    user_map: dict[str, int],
    role_map: dict[str, int],
    ds_id: int = 0,
) -> int:
    """Sync user-role relations. Uses upsert to avoid UniqueViolation.

    Only manages relations for roles belonging to the given ds_id.
    """
    synced = 0
    affected_uids: set[int] = set()

    # Collect valid relations
    valid_pairs: set[tuple[int, int]] = set()
    for row in ext_rows:
        ext_user_id = _clean(row.get("user_id"))
        role_code = _clean(row.get("role_code"))

        uid = user_map.get(ext_user_id)
        role_id = role_map.get(role_code)
        # Skip if uid is system admin
        if uid and uid == SYSTEM_ADMIN_UID:
            continue
        if uid and role_id:
            valid_pairs.add((uid, role_id))
            affected_uids.add(uid)

    # Pre-load ALL existing (uid, role_id) pairs for affected users to avoid UniqueViolation
    all_existing_role_pairs: set[tuple[int, int]] = set()
    for uid in affected_uids:
        rows = session.exec(
            select(SysUserRole.uid, SysUserRole.role_id).where(SysUserRole.uid == uid)
        ).all()
        for r in rows:
            all_existing_role_pairs.add((r[0], r[1]))

    # For each affected user: upsert relations
    for uid in affected_uids:
        existing_rels = session.exec(
            select(SysUserRole).where(SysUserRole.uid == uid)
        ).all()
        existing_pairs: set[tuple[int, int]] = set()
        to_delete: list[SysUserRole] = []
        for rel in existing_rels:
            role = session.get(SysRole, rel.role_id)
            all_existing_role_pairs.add((rel.uid, rel.role_id))
            if role and role.origin == 10 and role.ds_id == ds_id:
                existing_pairs.add((rel.uid, rel.role_id))
                if (rel.uid, rel.role_id) not in valid_pairs:
                    to_delete.append(rel)

        # Delete stale relations
        for rel in to_delete:
            session.delete(rel)
        session.flush()

        # Upsert: insert only missing pairs (role has no updatable fields)
        for (u, r) in valid_pairs:
            if u == uid and (u, r) not in existing_pairs:
                # Skip if relation already exists from any origin (avoid UniqueViolation)
                if (u, r) in all_existing_role_pairs:
                    synced += 1
                    continue
                new_rel = SysUserRole(
                    id=snowflake.generate_id(),
                    uid=u,
                    role_id=r,
                )
                session.add(new_rel)
                synced += 1

        refresh_user_role_ids(session, uid)

    return synced


# ── mark inactive ───────────────────────────────────────────────

def mark_inactive(
    session: Session,
    model_class,
    active_codes: set[str],
    origin: int = 10,
    ds_id: int = 0,
) -> int:
    """Mark entities with given origin+ds_id and code NOT in active_codes as status=9."""
    entities = session.exec(
        select(model_class).where(
            model_class.origin == origin,
            model_class.ds_id == ds_id,
        )
    ).all()
    deactivated = 0
    for entity in entities:
        if entity.code not in active_codes and entity.status != 9:
            entity.status = 9
            session.add(entity)
            deactivated += 1
    return deactivated


def mark_users_inactive(
    session: Session,
    active_ext_ids: set[str],
    origin: int = 10,
    ds_id: int = 0,
) -> int:
    """Mark sync-originated users whose platform_uid is not in active_ext_ids as status=9.
    Only affects users belonging to the given ds_id.
    Never touch the system admin user (id=1)."""
    platforms = session.exec(
        select(UserPlatformModel).where(
            UserPlatformModel.origin == origin,
            UserPlatformModel.ds_id == ds_id,
        )
    ).all()
    deactivated = 0
    for p in platforms:
        # Protect system admin
        if p.uid == SYSTEM_ADMIN_UID:
            continue
        if p.platform_uid not in active_ext_ids:
            user = session.get(UserModel, p.uid)
            if user and user.status != 9:
                user.status = 9
                session.add(user)
                deactivated += 1
    return deactivated


# ── main sync runner ────────────────────────────────────────────

def run_sync(session: Session, ds_id: int) -> dict:
    """Execute a full sync for the given datasource ID.

    Returns a summary dict:
      {created: N, updated: M, deactivated: K, ...}
    """
    # Load config
    ds = session.get(SyncDatasource, ds_id)
    if not ds:
        raise ValueError(f"SyncDatasource {ds_id} not found")
    if not ds.enabled:
        raise ValueError(f"SyncDatasource {ds_id} is disabled")

    # Load table mappings
    mappings = session.exec(
        select(SyncTableMapping).where(SyncTableMapping.ds_id == ds_id)
    ).all()
    mapping_map: dict[str, SyncTableMapping] = {m.entity_type: m for m in mappings}

    # Create sync log
    start_ts = get_timestamp()
    sync_log = SyncLog(
        ds_id=ds_id,
        status="running",
        start_time=start_ts,
    )
    session.add(sync_log)
    session.flush()

    try:
        engine = get_external_engine(ds)
        summary: dict = {"created": 0, "updated": 0, "deactivated": 0, "unchanged": 0}

        # 1. Upsert departments
        dept_map: dict[str, int] = {}
        dept_mapping = mapping_map.get("department")
        if dept_mapping and dept_mapping.enabled and dept_mapping.table_name:
            ext_depts = read_external_table(engine, dept_mapping.table_name)
            dept_map, created, updated = upsert_departments(session, ext_depts, ds_id=ds.id, oid=ds.oid)
            summary["created"] += created
            summary["updated"] += updated
            summary["dept_created"] = created
            summary["dept_updated"] = updated

        # 2. Upsert roles
        role_map: dict[str, int] = {}
        role_mapping = mapping_map.get("role")
        if role_mapping and role_mapping.enabled and role_mapping.table_name:
            ext_roles = read_external_table(engine, role_mapping.table_name)
            role_map, created, updated = upsert_roles(session, ext_roles, ds_id=ds.id, oid=ds.oid)
            summary["created"] += created
            summary["updated"] += updated
            summary["role_created"] = created
            summary["role_updated"] = updated

        # 3. Upsert users
        user_map: dict[str, int] = {}
        user_mapping = mapping_map.get("user")
        if user_mapping and user_mapping.enabled and user_mapping.table_name:
            ext_users = read_external_table(engine, user_mapping.table_name)
            user_map, created, updated = upsert_users(session, ext_users, ds_id=ds.id, oid=ds.oid)
            summary["created"] += created
            summary["updated"] += updated
            summary["user_created"] = created
            summary["user_updated"] = updated

        # 4. Sync user-department relations
        ud_mapping = mapping_map.get("user_dept")
        if ud_mapping and ud_mapping.enabled and ud_mapping.table_name and user_map and dept_map:
            ext_user_depts = read_external_table(engine, ud_mapping.table_name)
            synced = sync_user_departments(session, ext_user_depts, user_map, dept_map, ds_id=ds.id)
            summary["user_dept_synced"] = synced

        # 5. Sync user-role relations
        ur_mapping = mapping_map.get("user_role")
        if ur_mapping and ur_mapping.enabled and ur_mapping.table_name and user_map and role_map:
            ext_user_roles = read_external_table(engine, ur_mapping.table_name)
            synced = sync_user_roles(session, ext_user_roles, user_map, role_map, ds_id=ds.id)
            summary["user_role_synced"] = synced

        # 6. Mark inactive entities (scoped to this datasource)
        if dept_map:
            active_dept_codes = set(dept_map.keys())
            deactivated = mark_inactive(session, SysDepartment, active_dept_codes, ds_id=ds.id)
            summary["deactivated"] += deactivated
            summary["dept_deactivated"] = deactivated

        if role_map:
            active_role_codes = set(role_map.keys())
            deactivated = mark_inactive(session, SysRole, active_role_codes, ds_id=ds.id)
            summary["deactivated"] += deactivated
            summary["role_deactivated"] = deactivated

        if user_map:
            active_user_ids = set(user_map.keys())
            deactivated = mark_users_inactive(session, active_user_ids, ds_id=ds.id)
            summary["deactivated"] += deactivated
            summary["user_deactivated"] = deactivated

        session.commit()

        # Update sync log
        sync_log.status = "success"
        sync_log.summary = summary
        sync_log.end_time = get_timestamp()
        session.add(sync_log)
        session.commit()

        return summary

    except Exception as e:
        session.rollback()
        logger.exception(f"Sync failed for datasource {ds_id}")
        # Create a FRESH SyncLog (the old one was rolled back and its id is stale)
        try:
            error_log = SyncLog(
                ds_id=ds_id,
                status="failed",
                error_message=str(e)[:2000],
                start_time=start_ts,
                end_time=get_timestamp(),
            )
            session.add(error_log)
            session.commit()
        except Exception:
            logger.exception("Failed to save sync error log")
        raise
