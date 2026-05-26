"""API endpoints for managing role_list and dept_list on ds_rules.

Since DsRules is defined in the compiled xpack package and cannot be extended
with new fields, these endpoints use raw SQL to read/write role_list and dept_list
on the ds_rules table.
"""

import json
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from common.core.deps import CurrentUser, SessionDep

router = APIRouter(tags=["permission_rule"], prefix="/permission-rule")


class RuleTargetsUpdate(BaseModel):
    """Request body for updating role and department targets of a rule."""
    roles: List[int] = []
    departments: List[int] = []


class RuleTargetsResponse(BaseModel):
    """Response body for rule targets."""
    rule_id: int
    roles: List[int] = []
    departments: List[int] = []


class AllRuleTargetsResponse(BaseModel):
    """Response body for all rules' targets."""
    rules: List[RuleTargetsResponse] = []


@router.put("/{rule_id}/targets")
async def update_rule_targets(
    session: SessionDep,
    current_user: CurrentUser,
    rule_id: int,
    dto: RuleTargetsUpdate,
):
    """Update role_list and dept_list for a specific rule. Admin only."""
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Only admin can update rule targets")

    # Verify the rule exists
    result = session.execute(
        text("SELECT id FROM ds_rules WHERE id = :id"),
        {"id": rule_id}
    ).first()
    if not result:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Update role_list and dept_list using raw SQL
    session.execute(
        text("UPDATE ds_rules SET role_list = :role_list, dept_list = :dept_list WHERE id = :id"),
        {
            "role_list": json.dumps(dto.roles),
            "dept_list": json.dumps(dto.departments),
            "id": rule_id,
        }
    )
    session.commit()

    return {"message": "Rule targets updated successfully", "rule_id": rule_id}


@router.get("/targets")
async def get_all_rule_targets(
    session: SessionDep,
    current_user: CurrentUser,
):
    """Get role_list and dept_list for all rules."""
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Only admin can view rule targets")

    results = session.execute(
        text("SELECT id, role_list, dept_list FROM ds_rules")
    ).all()

    rules = []
    for row in results:
        role_list = json.loads(row.role_list) if row.role_list else []
        dept_list = json.loads(row.dept_list) if row.dept_list else []
        rules.append(RuleTargetsResponse(
            rule_id=row.id,
            roles=role_list,
            departments=dept_list,
        ))

    return AllRuleTargetsResponse(rules=rules)


@router.get("/{rule_id}/targets")
async def get_rule_targets(
    session: SessionDep,
    current_user: CurrentUser,
    rule_id: int,
):
    """Get role_list and dept_list for a specific rule."""
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Only admin can view rule targets")

    result = session.execute(
        text("SELECT id, role_list, dept_list FROM ds_rules WHERE id = :id"),
        {"id": rule_id}
    ).first()
    if not result:
        raise HTTPException(status_code=404, detail="Rule not found")

    role_list = json.loads(result.role_list) if result.role_list else []
    dept_list = json.loads(result.dept_list) if result.dept_list else []

    return RuleTargetsResponse(
        rule_id=result.id,
        roles=role_list,
        departments=dept_list,
    )
