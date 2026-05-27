"""APScheduler integration for periodic database sync.

- init_scheduler(): called during FastAPI startup, loads all enabled
  SyncDatasources that have a non-empty cron_expression.
- update_schedule(ds_id, cron_expression): dynamically add/modify/remove a job.
- remove_schedule(ds_id): remove a scheduled job.
"""

from __future__ import annotations

import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import Session, select

from apps.system.models.sync_model import SyncDatasource
from common.core.db import engine as db_engine

logger = logging.getLogger(__name__)

scheduler: Optional[AsyncIOScheduler] = None


def _get_scheduler() -> AsyncIOScheduler:
    global scheduler
    if scheduler is None:
        scheduler = AsyncIOScheduler()
    return scheduler


def parse_cron(expr: str) -> dict:
    """Parse a cron expression into APScheduler CronTrigger kwargs.

    Supports both 5-field (min hour day month dow) and 6-field (sec min hour day month dow).
    """
    parts = expr.strip().split()
    if len(parts) == 5:
        # Standard 5-field cron: min hour day month dow
        return {
            "minute": parts[0],
            "hour": parts[1],
            "day": parts[2],
            "month": parts[3],
            "day_of_week": parts[4],
        }
    elif len(parts) == 6:
        # 6-field cron: sec min hour day month dow
        return {
            "second": parts[0],
            "minute": parts[1],
            "hour": parts[2],
            "day": parts[3],
            "month": parts[4],
            "day_of_week": parts[5],
        }
    else:
        raise ValueError(f"Invalid cron expression (expected 5 or 6 fields): {expr}")


def _run_sync_job(ds_id: int) -> None:
    """Synchronous wrapper for running a sync job (called by APScheduler)."""
    from apps.system.crud.sync_engine import run_sync
    with Session(db_engine) as session:
        try:
            summary = run_sync(session, ds_id)
            logger.info(f"Sync job for datasource {ds_id} completed: {summary}")
        except Exception as e:
            logger.error(f"Sync job for datasource {ds_id} failed: {e}")


def init_scheduler() -> None:
    """Initialize the scheduler and register all active sync jobs."""
    sched = _get_scheduler()

    with Session(db_engine) as session:
        datasources = session.exec(
            select(SyncDatasource).where(
                SyncDatasource.enabled == True,  # noqa: E712
                SyncDatasource.cron_expression != "",
            )
        ).all()

        for ds in datasources:
            try:
                cron_kwargs = parse_cron(ds.cron_expression)
                job_id = f"sync_{ds.id}"
                sched.add_job(
                    _run_sync_job,
                    trigger=CronTrigger(**cron_kwargs),
                    id=job_id,
                    args=[ds.id],
                    replace_existing=True,
                )
                logger.info(f"Registered sync job: {job_id} with cron '{ds.cron_expression}'")
            except Exception as e:
                logger.error(f"Failed to register sync job for datasource {ds.id}: {e}")

    if not sched.running:
        sched.start()
        logger.info("APScheduler started for database sync")


def update_schedule(ds_id: int, cron_expression: str) -> None:
    """Add or update a scheduled sync job."""
    sched = _get_scheduler()
    job_id = f"sync_{ds_id}"

    if not cron_expression.strip():
        # Remove the job if cron is empty
        remove_schedule(ds_id)
        return

    cron_kwargs = parse_cron(cron_expression)
    sched.add_job(
        _run_sync_job,
        trigger=CronTrigger(**cron_kwargs),
        id=job_id,
        args=[ds_id],
        replace_existing=True,
    )
    logger.info(f"Updated sync job: {job_id} with cron '{cron_expression}'")

    if not sched.running:
        sched.start()


def remove_schedule(ds_id: int) -> None:
    """Remove a scheduled sync job."""
    sched = _get_scheduler()
    job_id = f"sync_{ds_id}"
    try:
        sched.remove_job(job_id)
        logger.info(f"Removed sync job: {job_id}")
    except Exception:
        pass  # Job may not exist


def shutdown_scheduler() -> None:
    """Shutdown the scheduler gracefully."""
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler shutdown")
