from sqlmodel import Session, select

from apps.system.models.user import UserModel
from apps.system.models.role_model import SysUserRole
from apps.system.models.department_model import SysUserDept


def refresh_user_role_ids(session: Session, uid: int) -> None:
    """Refresh user's role_ids redundant field from sys_user_role table."""
    # Query all role IDs for this user
    stmt = select(SysUserRole.role_id).where(SysUserRole.uid == uid)
    result = session.exec(stmt)
    role_ids_list = list(result.all())
    
    # Get user and update role_ids
    user = session.get(UserModel, uid)
    if user:
        user.role_ids = role_ids_list
        session.add(user)
        # Note: commit is responsibility of caller


def refresh_user_dept_ids(session: Session, uid: int) -> None:
    """Refresh user's dept_ids redundant field from sys_user_dept table."""
    # Query all department IDs for this user
    stmt = select(SysUserDept.dept_id).where(SysUserDept.uid == uid)
    result = session.exec(stmt)
    dept_ids_list = list(result.all())
    
    # Get user and update dept_ids
    user = session.get(UserModel, uid)
    if user:
        user.dept_ids = dept_ids_list
        session.add(user)
        # Note: commit is responsibility of caller


def refresh_user_ids_batch(session: Session, uid_list: list[int]) -> None:
    """Batch refresh multiple users' role_ids and dept_ids."""
    for uid in uid_list:
        refresh_user_role_ids(session, uid)
        refresh_user_dept_ids(session, uid)
