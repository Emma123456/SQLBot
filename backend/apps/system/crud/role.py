from typing import Optional
from sqlmodel import Session, select, func
from apps.system.models.role_model import SysRole, SysUserRole
from apps.system.models.user import UserModel
from apps.system.crud.user_role_dept import refresh_user_role_ids
from apps.system.crud.user import clean_user_cache
from common.utils.time import get_timestamp
from common.utils.utils import SQLBotLogUtil


def list_roles(session: Session, page: int = 1, page_size: int = 20, keyword: Optional[str] = None, ds_id: Optional[int] = None, oid: Optional[int] = None) -> dict:
    """List roles with pagination and optional keyword search."""
    base_stmt = select(SysRole)
    count_stmt = select(func.count()).select_from(SysRole)
    
    if keyword:
        filter_clause = (SysRole.name.contains(keyword)) | (SysRole.code.contains(keyword))
        base_stmt = base_stmt.where(filter_clause)
        count_stmt = count_stmt.where(filter_clause)
    
    if ds_id is not None:
        base_stmt = base_stmt.where(SysRole.ds_id == ds_id)
        count_stmt = count_stmt.where(SysRole.ds_id == ds_id)
    
    if oid is not None:
        base_stmt = base_stmt.where(SysRole.oid == oid)
        count_stmt = count_stmt.where(SysRole.oid == oid)
    
    total = session.exec(count_stmt).one()
    
    offset = (page - 1) * page_size
    stmt = base_stmt.order_by(SysRole.create_time.desc()).offset(offset).limit(page_size)
    roles = list(session.exec(stmt).all())
    
    return {"items": roles, "total": total, "page": page, "page_size": page_size}


def get_all_roles(session: Session, oid: Optional[int] = None) -> list[SysRole]:
    """Get all roles as a flat list, optionally filtered by oid."""
    stmt = select(SysRole).order_by(SysRole.create_time)
    if oid is not None:
        stmt = stmt.where(SysRole.oid == oid)
    return list(session.exec(stmt).all())


def get_role(session: Session, role_id: int) -> Optional[SysRole]:
    """Get a single role by ID."""
    return session.get(SysRole, role_id)


def check_name_exists(session: Session, name: str, exclude_id: Optional[int] = None) -> bool:
    """Check if role name already exists."""
    stmt = select(func.count()).select_from(SysRole).where(SysRole.name == name)
    if exclude_id:
        stmt = stmt.where(SysRole.id != exclude_id)
    return session.exec(stmt).one() > 0


def check_code_exists(session: Session, code: str, exclude_id: Optional[int] = None) -> bool:
    """Check if role code already exists."""
    stmt = select(func.count()).select_from(SysRole).where(SysRole.code == code)
    if exclude_id:
        stmt = stmt.where(SysRole.id != exclude_id)
    return session.exec(stmt).one() > 0


def create_role(session: Session, name: str, code: str, description: Optional[str] = None, oid: int = 1) -> SysRole:
    """Create a new role."""
    if check_name_exists(session, name):
        raise ValueError(f"Role name '{name}' already exists")
    if check_code_exists(session, code):
        raise ValueError(f"Role code '{code}' already exists")
    
    role = SysRole(
        name=name,
        code=code,
        description=description,
        origin=0,
        oid=oid,
        create_time=get_timestamp()
    )
    session.add(role)
    session.flush()
    session.refresh(role)
    SQLBotLogUtil.info(f"Created role: {name} (ID: {role.id})")
    return role


def update_role(
    session: Session,
    role_id: int,
    name: Optional[str] = None,
    code: Optional[str] = None,
    description: Optional[str] = None,
    oid: Optional[int] = None
) -> SysRole:
    """Update a role."""
    role = session.get(SysRole, role_id)
    if not role:
        raise ValueError(f"Role with ID {role_id} does not exist")
    
    if name is not None and name != role.name:
        if check_name_exists(session, name, exclude_id=role_id):
            raise ValueError(f"Role name '{name}' already exists")
    
    if code is not None and code != role.code:
        if check_code_exists(session, code, exclude_id=role_id):
            raise ValueError(f"Role code '{code}' already exists")
    
    if name is not None:
        role.name = name
    if code is not None:
        role.code = code
    if description is not None:
        role.description = description
    if oid is not None:
        role.oid = oid
    
    session.add(role)
    session.flush()
    session.refresh(role)
    SQLBotLogUtil.info(f"Updated role: {role.name} (ID: {role.id})")
    return role


def delete_role(session: Session, role_id: int) -> list[int]:
    """Delete a role and its user associations, then refresh affected users' role_ids.
    Returns list of affected user IDs."""
    role = session.get(SysRole, role_id)
    if not role:
        raise ValueError(f"Role with ID {role_id} does not exist")
    
    # Find all affected user IDs before deleting associations
    affected_uids = list(session.exec(
        select(SysUserRole.uid).where(SysUserRole.role_id == role_id)
    ).all())
    
    # Delete user-role associations
    for ur in session.exec(select(SysUserRole).where(SysUserRole.role_id == role_id)).all():
        session.delete(ur)
    session.flush()
    
    # Delete the role
    session.delete(role)
    session.flush()
    
    # Refresh affected users' role_ids
    for uid in affected_uids:
        refresh_user_role_ids(session, uid)
    
    SQLBotLogUtil.info(f"Deleted role: {role.name} (ID: {role_id}), affected {len(affected_uids)} user(s)")
    return affected_uids


def get_role_users(session: Session, role_id: int) -> list[dict]:
    """Get all users assigned to a role."""
    role = session.get(SysRole, role_id)
    if not role:
        raise ValueError(f"Role with ID {role_id} does not exist")
    
    stmt = (
        select(SysUserRole, UserModel)
        .join(UserModel, UserModel.id == SysUserRole.uid)
        .where(SysUserRole.role_id == role_id)
    )
    results = session.exec(stmt).all()
    
    return [
        {
            "id": user.id,
            "name": user.name,
            "account": user.account,
            "email": user.email,
        }
        for ur, user in results
    ]


def assign_users_to_role(
    session: Session,
    role_id: int,
    user_ids: list[int]
) -> list[int]:
    """Assign users to a role. Adds new associations (does not remove existing).
    Returns list of affected user IDs."""
    role = session.get(SysRole, role_id)
    if not role:
        raise ValueError(f"Role with ID {role_id} does not exist")
    
    affected_uids = []
    for uid in user_ids:
        # Check if already assigned
        existing = session.exec(
            select(SysUserRole).where(
                SysUserRole.uid == uid,
                SysUserRole.role_id == role_id
            )
        ).first()
        if not existing:
            user_role = SysUserRole(
                uid=uid,
                role_id=role_id
            )
            session.add(user_role)
            affected_uids.append(uid)
    
    session.flush()
    
    # Refresh redundant fields for affected users
    for uid in affected_uids:
        refresh_user_role_ids(session, uid)

    return affected_uids


def remove_users_from_role(
    session: Session,
    role_id: int,
    user_ids: list[int]
) -> list[int]:
    """Remove users from a role.
    Returns list of affected user IDs."""
    affected_uids = []
    for uid in user_ids:
        ur = session.exec(
            select(SysUserRole).where(
                SysUserRole.uid == uid,
                SysUserRole.role_id == role_id
            )
        ).first()
        if ur:
            session.delete(ur)
            affected_uids.append(uid)
    
    session.flush()
    
    # Refresh redundant fields for affected users
    for uid in affected_uids:
        refresh_user_role_ids(session, uid)

    return affected_uids
