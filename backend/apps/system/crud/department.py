from typing import List, Optional
from sqlmodel import Session, select, func, delete as sqlmodel_delete
from apps.system.models.department_model import SysDepartment, SysUserDept
from apps.system.models.user import UserModel
from apps.system.crud.user_role_dept import refresh_user_dept_ids
from apps.system.crud.user import clean_user_cache
from common.utils.time import get_timestamp
from common.utils.utils import SQLBotLogUtil


def build_department_tree(departments: list[SysDepartment]) -> list[dict]:
    """Build a tree structure from a flat list of departments."""
    children_map: dict[int, list[SysDepartment]] = {}
    roots: list[SysDepartment] = []
    
    for dept in departments:
        if dept.parent_id == 0:
            roots.append(dept)
        else:
            if dept.parent_id not in children_map:
                children_map[dept.parent_id] = []
            children_map[dept.parent_id].append(dept)
    
    def dept_to_dict(dept: SysDepartment) -> dict:
        result = {
            "id": str(dept.id) if isinstance(dept.id, int) and dept.id > (2**53 - 1) else dept.id,
            "name": dept.name,
            "code": dept.code,
            "parent_id": str(dept.parent_id) if isinstance(dept.parent_id, int) and dept.parent_id > (2**53 - 1) else dept.parent_id,
            "origin": dept.origin,
            "create_time": dept.create_time,
            "children": []
        }
        if dept.id in children_map:
            for child in children_map[dept.id]:
                result["children"].append(dept_to_dict(child))
        return result
    
    return [dept_to_dict(dept) for dept in roots]


def get_department_tree(session: Session) -> list[dict]:
    """Get all departments as a tree structure."""
    stmt = select(SysDepartment).order_by(SysDepartment.create_time)
    departments = session.exec(stmt).all()
    return build_department_tree(list(departments))


def get_all_departments(session: Session) -> list[SysDepartment]:
    """Get all departments as a flat list."""
    stmt = select(SysDepartment).order_by(SysDepartment.create_time)
    return list(session.exec(stmt).all())


def get_department(session: Session, dept_id: int) -> Optional[SysDepartment]:
    """Get a single department by ID."""
    return session.get(SysDepartment, dept_id)


def check_code_exists(session: Session, code: str, exclude_id: Optional[int] = None) -> bool:
    """Check if department code already exists."""
    stmt = select(func.count()).select_from(SysDepartment).where(SysDepartment.code == code)
    if exclude_id:
        stmt = stmt.where(SysDepartment.id != exclude_id)
    return session.exec(stmt).one() > 0


def _is_descendant(session: Session, ancestor_id: int, node_id: int) -> bool:
    """Check if node_id is a descendant of ancestor_id by walking up the tree."""
    current_id = node_id
    visited = set()
    while current_id != 0:
        if current_id in visited:
            return False
        visited.add(current_id)
        if current_id == ancestor_id:
            return True
        dept = session.get(SysDepartment, current_id)
        if not dept:
            return False
        current_id = dept.parent_id
    return False


def create_department(session: Session, name: str, code: str, parent_id: int = 0) -> SysDepartment:
    """Create a new department."""
    if check_code_exists(session, code):
        raise ValueError(f"Department code '{code}' already exists")
    
    if parent_id != 0:
        parent = session.get(SysDepartment, parent_id)
        if not parent:
            raise ValueError(f"Parent department with ID {parent_id} does not exist")
    
    dept = SysDepartment(
        name=name,
        code=code,
        parent_id=parent_id,
        origin=0,
        create_time=get_timestamp()
    )
    session.add(dept)
    session.flush()
    session.refresh(dept)
    SQLBotLogUtil.info(f"Created department: {name} (ID: {dept.id})")
    return dept


def update_department(
    session: Session,
    dept_id: int,
    name: Optional[str] = None,
    code: Optional[str] = None,
    parent_id: Optional[int] = None
) -> SysDepartment:
    """Update a department."""
    dept = session.get(SysDepartment, dept_id)
    if not dept:
        raise ValueError(f"Department with ID {dept_id} does not exist")
    
    if code is not None and code != dept.code:
        if check_code_exists(session, code, exclude_id=dept_id):
            raise ValueError(f"Department code '{code}' already exists")
    
    if parent_id is not None and parent_id != dept.parent_id:
        if parent_id == dept_id:
            raise ValueError("Department cannot be its own parent")
        if parent_id != 0:
            parent = session.get(SysDepartment, parent_id)
            if not parent:
                raise ValueError(f"Parent department with ID {parent_id} does not exist")
            if _is_descendant(session, dept_id, parent_id):
                raise ValueError("Cannot set a descendant as parent (would create circular reference)")
    
    if name is not None:
        dept.name = name
    if code is not None:
        dept.code = code
    if parent_id is not None:
        dept.parent_id = parent_id
    
    session.add(dept)
    session.flush()
    session.refresh(dept)
    SQLBotLogUtil.info(f"Updated department: {dept.name} (ID: {dept.id})")
    return dept


def delete_department(session: Session, dept_id: int) -> bool:
    """Delete a department. Only leaf departments without users can be deleted."""
    dept = session.get(SysDepartment, dept_id)
    if not dept:
        raise ValueError(f"Department with ID {dept_id} does not exist")
    
    child_count = session.exec(
        select(func.count()).select_from(SysDepartment).where(SysDepartment.parent_id == dept_id)
    ).one()
    if child_count > 0:
        raise ValueError(f"Cannot delete department '{dept.name}' because it has {child_count} child department(s)")
    
    user_count = session.exec(
        select(func.count()).select_from(SysUserDept).where(SysUserDept.dept_id == dept_id)
    ).one()
    if user_count > 0:
        raise ValueError(f"Cannot delete department '{dept.name}' because it has {user_count} user(s) assigned")
    
    session.delete(dept)
    session.flush()
    SQLBotLogUtil.info(f"Deleted department: {dept.name} (ID: {dept_id})")
    return True


def get_department_users(session: Session, dept_id: int) -> list[dict]:
    """Get all users in a department with is_primary flag."""
    dept = session.get(SysDepartment, dept_id)
    if not dept:
        raise ValueError(f"Department with ID {dept_id} does not exist")
    
    stmt = (
        select(SysUserDept, UserModel)
        .join(UserModel, UserModel.id == SysUserDept.uid)
        .where(SysUserDept.dept_id == dept_id)
    )
    results = session.exec(stmt).all()
    
    return [
        {
            "id": user.id,
            "name": user.name,
            "account": user.account,
            "email": user.email,
            "is_primary": ud.is_primary,
        }
        for ud, user in results
    ]


def assign_users_to_department(
    session: Session,
    dept_id: int,
    user_ids: list[int],
    is_primary: bool = False
) -> list[int]:
    """Assign users to a department. Adds new associations (does not remove existing).
    Returns list of affected user IDs."""
    dept = session.get(SysDepartment, dept_id)
    if not dept:
        raise ValueError(f"Department with ID {dept_id} does not exist")
    
    affected_uids = []
    for uid in user_ids:
        # Check if already assigned
        existing = session.exec(
            select(SysUserDept).where(
                SysUserDept.uid == uid,
                SysUserDept.dept_id == dept_id
            )
        ).first()
        if not existing:
            user_dept = SysUserDept(
                uid=uid,
                dept_id=dept_id,
                is_primary=is_primary
            )
            session.add(user_dept)
            affected_uids.append(uid)
    
    session.flush()
    
    # Refresh redundant fields for affected users
    for uid in affected_uids:
        refresh_user_dept_ids(session, uid)

    return affected_uids


def remove_users_from_department(
    session: Session,
    dept_id: int,
    user_ids: list[int]
) -> list[int]:
    """Remove users from a department.
    Returns list of affected user IDs."""
    affected_uids = []
    for uid in user_ids:
        ud = session.exec(
            select(SysUserDept).where(
                SysUserDept.uid == uid,
                SysUserDept.dept_id == dept_id
            )
        ).first()
        if ud:
            session.delete(ud)
            affected_uids.append(uid)
    
    session.flush()
    
    # Refresh redundant fields for affected users
    for uid in affected_uids:
        refresh_user_dept_ids(session, uid)

    return affected_uids
