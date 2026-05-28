from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import Session, select
from sqlalchemy import text

from apps.system.models.sync_model import (
    SyncDatasource,
    SyncTableMapping,
    SyncLog,
    SyncDatasourceCreate,
    SyncDatasourceUpdate,
    SyncTableMappingUpdate,
    SyncScheduleUpdate,
    ENTITY_TYPES,
)
from apps.system.crud.sync_engine import run_sync, get_external_engine, read_external_table
from apps.datasource.utils.utils import aes_encrypt, aes_decrypt
from common.core.deps import CurrentUser, SessionDep
from common.utils.time import get_timestamp

router = APIRouter(tags=["system_sync"], prefix="/system/sync")


# ── Datasource CRUD ─────────────────────────────────────────────

@router.get("/datasource")
async def list_datasources(session: SessionDep, current_user: CurrentUser):
    """List all sync datasources. Admin only."""
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Only admin can list sync datasources")
    datasources = session.exec(select(SyncDatasource).order_by(SyncDatasource.create_time.desc())).all()
    # Mask passwords in list view
    result = []
    for ds in datasources:
        ds_dict = ds.model_dump()
        ds_dict["password"] = "***"
        result.append(ds_dict)
    return result


@router.post("/datasource")
async def create_datasource(
    session: SessionDep,
    current_user: CurrentUser,
    dto: SyncDatasourceCreate,
):
    """Create a new sync datasource. Admin only."""
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Only admin can create sync datasources")
    encrypted_pwd = aes_encrypt(dto.password).decode("utf-8") if isinstance(dto.password, str) else dto.password
    ds = SyncDatasource(
        name=dto.name,
        db_type=dto.db_type,
        host=dto.host,
        port=dto.port,
        username=dto.username,
        password=encrypted_pwd,
        database=dto.database,
        db_schema=dto.db_schema,
        enabled=dto.enabled,
        cron_expression=dto.cron_expression,
        oid=dto.oid,
    )
    session.add(ds)
    session.commit()
    session.refresh(ds)

    # Create default empty mappings for all 5 entity types
    for entity_type in ENTITY_TYPES:
        mapping = SyncTableMapping(
            ds_id=ds.id,
            entity_type=entity_type,
            table_name="",
            enabled=True,
        )
        session.add(mapping)
    session.commit()

    # Schedule if cron expression is set
    if ds.cron_expression:
        try:
            from apps.system.sync.scheduler import update_schedule
            update_schedule(ds.id, ds.cron_expression)
        except Exception:
            pass

    result = ds.model_dump()
    result["password"] = "***"
    return result


@router.put("/datasource")
async def update_datasource(
    session: SessionDep,
    current_user: CurrentUser,
    dto: SyncDatasourceUpdate,
):
    """Update a sync datasource. Admin only."""
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Only admin can update sync datasources")
    ds = session.get(SyncDatasource, dto.id)
    if not ds:
        raise HTTPException(status_code=404, detail="Sync datasource not found")

    update_data = dto.model_dump(exclude_unset=True, exclude={"id"})
    if "password" in update_data and update_data["password"]:
        update_data["password"] = aes_encrypt(update_data["password"]).decode("utf-8")

    for key, value in update_data.items():
        setattr(ds, key, value)
    session.add(ds)
    session.commit()
    session.refresh(ds)

    # Update scheduler if cron_expression changed
    if "cron_expression" in update_data:
        try:
            from apps.system.sync.scheduler import update_schedule
            update_schedule(ds.id, ds.cron_expression)
        except Exception:
            pass

    result = ds.model_dump()
    result["password"] = "***"
    return result


@router.delete("/datasource/{ds_id}")
async def delete_datasource(
    session: SessionDep,
    current_user: CurrentUser,
    ds_id: int,
):
    """Delete a sync datasource and its mappings. Admin only."""
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Only admin can delete sync datasources")
    ds = session.get(SyncDatasource, ds_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Sync datasource not found")

    # Remove mappings
    mappings = session.exec(
        select(SyncTableMapping).where(SyncTableMapping.ds_id == ds_id)
    ).all()
    for m in mappings:
        session.delete(m)

    # Remove logs
    logs = session.exec(
        select(SyncLog).where(SyncLog.ds_id == ds_id)
    ).all()
    for log in logs:
        session.delete(log)

    session.delete(ds)
    session.commit()

    # Remove scheduler job
    try:
        from apps.system.sync.scheduler import remove_schedule
        remove_schedule(ds_id)
    except Exception:
        pass

    return {"message": "Sync datasource deleted successfully"}


# ── Connection test ─────────────────────────────────────────────

@router.post("/datasource/{ds_id}/test")
async def test_connection(
    session: SessionDep,
    current_user: CurrentUser,
    ds_id: int,
):
    """Test connection to external database. Admin only."""
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Only admin can test sync connections")
    ds = session.get(SyncDatasource, ds_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Sync datasource not found")

    try:
        engine = get_external_engine(ds)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"success": True, "message": "Connection successful"}
    except Exception as e:
        return {"success": False, "message": f"Connection failed: {str(e)}"}


# ── Table mapping ───────────────────────────────────────────────

@router.get("/datasource/{ds_id}/mapping")
async def get_mappings(
    session: SessionDep,
    current_user: CurrentUser,
    ds_id: int,
):
    """Get table mappings for a datasource. Admin only."""
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Only admin can view sync mappings")
    mappings = session.exec(
        select(SyncTableMapping).where(SyncTableMapping.ds_id == ds_id)
    ).all()

    # Ensure all 5 entity types exist
    existing_types = {m.entity_type for m in mappings}
    for entity_type in ENTITY_TYPES:
        if entity_type not in existing_types:
            new_mapping = SyncTableMapping(
                ds_id=ds_id,
                entity_type=entity_type,
                table_name="",
                enabled=True,
            )
            session.add(new_mapping)
    session.commit()

    mappings = session.exec(
        select(SyncTableMapping).where(SyncTableMapping.ds_id == ds_id)
    ).all()
    return list(mappings)


@router.put("/datasource/{ds_id}/mapping")
async def update_mappings(
    session: SessionDep,
    current_user: CurrentUser,
    ds_id: int,
    dto_list: List[SyncTableMappingUpdate],
):
    """Update table mappings for a datasource. Admin only."""
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Only admin can update sync mappings")

    for dto in dto_list:
        existing = session.exec(
            select(SyncTableMapping).where(
                SyncTableMapping.ds_id == ds_id,
                SyncTableMapping.entity_type == dto.entity_type,
            )
        ).first()
        if existing:
            existing.table_name = dto.table_name
            existing.enabled = dto.enabled
            session.add(existing)
        else:
            new_mapping = SyncTableMapping(
                ds_id=ds_id,
                entity_type=dto.entity_type,
                table_name=dto.table_name,
                enabled=dto.enabled,
            )
            session.add(new_mapping)

    session.commit()
    return {"message": "Mappings updated successfully"}


# ── Execute sync ────────────────────────────────────────────────

@router.post("/datasource/{ds_id}/execute")
async def execute_sync(
    session: SessionDep,
    current_user: CurrentUser,
    ds_id: int,
):
    """Execute sync immediately. Admin only."""
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Only admin can execute sync")
    try:
        summary = run_sync(session, ds_id)
        return {"success": True, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


# ── Sync logs ───────────────────────────────────────────────────

@router.get("/datasource/{ds_id}/logs")
async def get_sync_logs(
    session: SessionDep,
    current_user: CurrentUser,
    ds_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Get sync logs for a datasource. Admin only."""
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Only admin can view sync logs")

    from sqlmodel import func
    count_stmt = select(func.count()).select_from(SyncLog).where(SyncLog.ds_id == ds_id)
    total = session.exec(count_stmt).one()

    offset = (page - 1) * page_size
    logs = session.exec(
        select(SyncLog)
        .where(SyncLog.ds_id == ds_id)
        .order_by(SyncLog.start_time.desc())
        .offset(offset)
        .limit(page_size)
    ).all()

    return {"items": list(logs), "total": total, "page": page, "page_size": page_size}


# ── Schedule ────────────────────────────────────────────────────

@router.put("/datasource/{ds_id}/schedule")
async def update_sync_schedule(
    session: SessionDep,
    current_user: CurrentUser,
    ds_id: int,
    dto: SyncScheduleUpdate,
):
    """Update sync schedule (cron expression). Admin only."""
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Only admin can update sync schedule")

    ds = session.get(SyncDatasource, ds_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Sync datasource not found")

    ds.cron_expression = dto.cron_expression
    session.add(ds)
    session.commit()

    # Update scheduler
    try:
        from apps.system.sync.scheduler import update_schedule
        update_schedule(ds_id, dto.cron_expression)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update scheduler: {str(e)}")

    return {"message": "Schedule updated successfully"}
