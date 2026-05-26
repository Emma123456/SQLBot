from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.system.crud.department import (
    create_department,
    delete_department,
    get_department,
    get_department_tree,
    get_department_users,
    assign_users_to_department,
    remove_users_from_department,
    update_department,
)
from apps.system.schemas.system_schema import DepartmentCreate, DepartmentUpdate
from common.core.deps import CurrentUser, SessionDep

router = APIRouter(tags=["system_department"], prefix="/system/department")


class DepartmentUserAssign(BaseModel):
    user_ids: List[int]
    is_primary: bool = False


class DepartmentUserRemove(BaseModel):
    user_ids: List[int]


@router.get("/tree")
async def tree(session: SessionDep, current_user: CurrentUser):
    """Get department tree structure."""
    return get_department_tree(session)


@router.get("/{dept_id}")
async def detail(session: SessionDep, current_user: CurrentUser, dept_id: int):
    """Get department detail by ID."""
    dept = get_department(session, dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept


@router.post("")
async def create(session: SessionDep, current_user: CurrentUser, dto: DepartmentCreate):
    """Create a new department. Admin only."""
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Only admin can create departments")
    try:
        dept = create_department(session, name=dto.name, code=dto.code, parent_id=dto.parent_id)
        session.commit()
        return dept
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("")
async def update(session: SessionDep, current_user: CurrentUser, dto: DepartmentUpdate):
    """Update a department. Admin only."""
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Only admin can update departments")
    try:
        dept = update_department(
            session,
            dept_id=dto.id,
            name=dto.name,
            code=dto.code,
            parent_id=dto.parent_id,
        )
        session.commit()
        return dept
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{dept_id}")
async def delete(session: SessionDep, current_user: CurrentUser, dept_id: int):
    """Delete a department. Admin only. Only leaf departments without users can be deleted."""
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Only admin can delete departments")
    try:
        delete_department(session, dept_id)
        session.commit()
        return {"message": "Department deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{dept_id}/users")
async def users(session: SessionDep, current_user: CurrentUser, dept_id: int):
    """Get all users in a department."""
    try:
        return get_department_users(session, dept_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{dept_id}/users")
async def assign_users(
    session: SessionDep,
    current_user: CurrentUser,
    dept_id: int,
    dto: DepartmentUserAssign,
):
    """Assign users to a department. Admin only."""
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Only admin can assign users to departments")
    try:
        assign_users_to_department(session, dept_id, dto.user_ids, dto.is_primary)
        session.commit()
        return {"message": "Users assigned successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{dept_id}/users")
async def remove_users(
    session: SessionDep,
    current_user: CurrentUser,
    dept_id: int,
    dto: DepartmentUserRemove,
):
    """Remove users from a department. Admin only."""
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Only admin can remove users from departments")
    try:
        remove_users_from_department(session, dept_id, dto.user_ids)
        session.commit()
        return {"message": "Users removed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
