from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from apps.system.crud.role import (
    list_roles,
    create_role,
    delete_role,
    get_role,
    get_role_users,
    assign_users_to_role,
    remove_users_from_role,
    update_role,
)
from apps.system.schemas.system_schema import RoleCreate, RoleUpdate
from common.core.deps import CurrentUser, SessionDep

router = APIRouter(tags=["system_role"], prefix="/system/role")


class RoleUserAssign(BaseModel):
    user_ids: List[int]


class RoleUserRemove(BaseModel):
    user_ids: List[int]


@router.get("")
async def list_endpoint(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
):
    """List roles with pagination. Admin only."""
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Only admin can list roles")
    return list_roles(session, page=page, page_size=page_size, keyword=keyword)


@router.get("/all")
async def list_all(session: SessionDep, current_user: CurrentUser):
    """Get all roles as flat list (for dropdowns). Admin only."""
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Only admin can list roles")
    from apps.system.crud.role import get_all_roles
    return get_all_roles(session)


@router.get("/{role_id}")
async def detail(session: SessionDep, current_user: CurrentUser, role_id: int):
    """Get role detail by ID."""
    role = get_role(session, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.post("")
async def create(session: SessionDep, current_user: CurrentUser, dto: RoleCreate):
    """Create a new role. Admin only."""
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Only admin can create roles")
    try:
        role = create_role(session, name=dto.name, code=dto.code, description=dto.description)
        session.commit()
        return role
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("")
async def update(session: SessionDep, current_user: CurrentUser, dto: RoleUpdate):
    """Update a role. Admin only."""
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Only admin can update roles")
    try:
        role = update_role(
            session,
            role_id=dto.id,
            name=dto.name,
            code=dto.code,
            description=dto.description,
        )
        session.commit()
        return role
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{role_id}")
async def delete(session: SessionDep, current_user: CurrentUser, role_id: int):
    """Delete a role. Admin only. Also removes user associations and refreshes role_ids."""
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Only admin can delete roles")
    try:
        delete_role(session, role_id)
        session.commit()
        return {"message": "Role deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{role_id}/users")
async def users(session: SessionDep, current_user: CurrentUser, role_id: int):
    """Get all users assigned to a role."""
    try:
        return get_role_users(session, role_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{role_id}/users")
async def assign_users(
    session: SessionDep,
    current_user: CurrentUser,
    role_id: int,
    dto: RoleUserAssign,
):
    """Assign users to a role. Admin only."""
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Only admin can assign users to roles")
    try:
        assign_users_to_role(session, role_id, dto.user_ids)
        session.commit()
        return {"message": "Users assigned successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{role_id}/users")
async def remove_users(
    session: SessionDep,
    current_user: CurrentUser,
    role_id: int,
    dto: RoleUserRemove,
):
    """Remove users from a role. Admin only."""
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Only admin can remove users from roles")
    try:
        remove_users_from_role(session, role_id, dto.user_ids)
        session.commit()
        return {"message": "Users removed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
