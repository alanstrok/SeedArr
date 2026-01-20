"""System API routes."""
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.config import settings
from app.models import Torrent, Tracker, Rule, ActionLog, Settings, Connection
from app.models.settings import DEFAULT_SETTINGS
from app.schemas.system import (
    StatsResponse,
    StatsHistoryResponse,
    ScanResult,
    LogResponse,
    LogListResponse,
    SettingsResponse,
    SettingsUpdate,
    HealthResponse,
    BackupData,
)
from app.services.scheduler import scheduler
from app.services.qbittorrent import QBittorrentService
from app.services.rule_engine import RuleEngine
from app.core.security import decrypt_password

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint."""
    # Check database
    try:
        await db.execute(select(func.count()).select_from(Settings))
        db_status = "connected"
    except Exception:
        db_status = "error"

    # Check qBittorrent
    qbt_status = None
    result = await db.execute(
        select(Connection).where(
            Connection.type == "qbittorrent",
            Connection.enabled == True,
        )
    )
    connection = result.scalar_one_or_none()
    if connection:
        qbt = QBittorrentService(
            url=connection.url,
            username=connection.username or "",
            password=decrypt_password(connection.password) if connection.password else "",
        )
        if await qbt.connect():
            qbt_status = "connected"
            await qbt.disconnect()
        else:
            qbt_status = "error"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "unhealthy",
        version=settings.app_version,
        database=db_status,
        qbittorrent=qbt_status,
        scheduler="running" if scheduler.is_running else "stopped",
        uptime_seconds=scheduler.uptime_seconds,
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get global statistics for dashboard."""
    # Torrent stats
    result = await db.execute(select(Torrent))
    torrents = result.scalars().all()

    total_torrents = len(torrents)
    active_states = ["uploading", "stalledUP", "forcedUP", "queuedUP"]
    paused_states = ["pausedUP", "pausedDL"]
    active_torrents = len([t for t in torrents if t.state in active_states])
    paused_torrents = len([t for t in torrents if t.state in paused_states])

    total_upload = sum(t.uploaded_bytes for t in torrents)
    total_download = sum(t.downloaded_bytes for t in torrents)
    average_ratio = sum(t.ratio for t in torrents) / max(len(torrents), 1)
    total_size = sum(t.size_bytes for t in torrents)
    protected_count = len([t for t in torrents if t.protected])

    # Actions today and this week
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)

    result = await db.execute(
        select(func.count())
        .select_from(ActionLog)
        .where(ActionLog.created_at >= today, ActionLog.dry_run == False)
    )
    actions_today = result.scalar() or 0

    result = await db.execute(
        select(func.count())
        .select_from(ActionLog)
        .where(ActionLog.created_at >= week_ago, ActionLog.dry_run == False)
    )
    actions_this_week = result.scalar() or 0

    # Counts
    result = await db.execute(select(func.count()).select_from(Tracker))
    trackers_count = result.scalar() or 0

    result = await db.execute(select(func.count()).select_from(Rule))
    rules_count = result.scalar() or 0

    return StatsResponse(
        total_torrents=total_torrents,
        active_torrents=active_torrents,
        paused_torrents=paused_torrents,
        total_upload_bytes=total_upload,
        total_download_bytes=total_download,
        average_ratio=average_ratio,
        total_size_bytes=total_size,
        actions_today=actions_today,
        actions_this_week=actions_this_week,
        protected_count=protected_count,
        trackers_count=trackers_count,
        rules_count=rules_count,
        last_scan=scheduler.last_scan,
    )


@router.get("/stats/history", response_model=StatsHistoryResponse)
async def get_stats_history(days: int = Query(30, ge=1, le=90), db: AsyncSession = Depends(get_db)):
    """Get statistics history for graphs."""
    # This would typically come from a separate stats table
    # For now, return mock data structure
    dates = []
    upload = []
    download = []
    ratio = []
    torrent_count = []

    # Generate dates for the past N days
    for i in range(days, -1, -1):
        date = datetime.utcnow() - timedelta(days=i)
        dates.append(date.strftime("%Y-%m-%d"))
        # Placeholder values - in a real implementation, these would come from a history table
        upload.append(0)
        download.append(0)
        ratio.append(0.0)
        torrent_count.append(0)

    return StatsHistoryResponse(
        dates=dates,
        upload=upload,
        download=download,
        ratio=ratio,
        torrent_count=torrent_count,
    )


@router.get("/logs", response_model=LogListResponse)
async def get_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    tracker_id: Optional[int] = None,
    rule_id: Optional[int] = None,
    action: Optional[str] = None,
    dry_run: Optional[bool] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get action logs with pagination and filters."""
    query = select(ActionLog)

    # Apply filters
    if tracker_id:
        query = query.where(ActionLog.tracker_id == tracker_id)
    if rule_id:
        query = query.where(ActionLog.rule_id == rule_id)
    if action:
        query = query.where(ActionLog.action == action)
    if dry_run is not None:
        query = query.where(ActionLog.dry_run == dry_run)
    if start_date:
        query = query.where(ActionLog.created_at >= start_date)
    if end_date:
        query = query.where(ActionLog.created_at <= end_date)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply sorting and pagination
    query = query.order_by(ActionLog.created_at.desc())
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    logs = result.scalars().all()

    pages = (total + per_page - 1) // per_page

    return LogListResponse(
        items=[
            LogResponse(
                id=log.id,
                torrent_hash=log.torrent_hash,
                torrent_name=log.torrent_name,
                tracker_id=log.tracker_id,
                tracker_name=log.tracker.name if log.tracker else None,
                rule_id=log.rule_id,
                rule_name=log.rule.name if log.rule else None,
                action=log.action,
                reason=log.reason,
                dry_run=log.dry_run,
                created_at=log.created_at,
            )
            for log in logs
        ],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.post("/scan")
async def trigger_scan(dry_run: bool = False, db: AsyncSession = Depends(get_db)):
    """Trigger a manual scan."""
    from app.database import async_session_maker

    if not scheduler._db_session_factory:
        scheduler.set_db_session_factory(async_session_maker)

    try:
        result = await scheduler.trigger_scan(dry_run=dry_run)
        return {
            "dry_run": result.dry_run,
            "started_at": result.started_at.isoformat(),
            "completed_at": result.completed_at.isoformat(),
            "duration_seconds": (result.completed_at - result.started_at).total_seconds(),
            "torrents_scanned": result.torrents_scanned,
            "actions_taken": result.actions_taken,
            "deleted": result.deleted,
            "paused": result.paused,
            "tagged": result.tagged,
            "protected_skipped": result.protected_skipped,
            "items": result.items,
        }
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/scan/dry-run")
async def trigger_dry_run(db: AsyncSession = Depends(get_db)):
    """Trigger a dry-run scan."""
    return await trigger_scan(dry_run=True, db=db)


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    """Get all settings."""
    result = await db.execute(select(Settings))
    settings_list = result.scalars().all()

    # Build settings dict from database, falling back to defaults
    settings_dict = dict(DEFAULT_SETTINGS)
    for setting in settings_list:
        settings_dict[setting.key] = setting.value

    return SettingsResponse(**settings_dict)


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(data: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    """Update settings."""
    update_data = data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        result = await db.execute(select(Settings).where(Settings.key == key))
        setting = result.scalar_one_or_none()

        if setting:
            setting.value = value
        else:
            setting = Settings(key=key, value=value)
            db.add(setting)

    await db.commit()

    # Update scheduler interval if changed
    if "scan_interval_minutes" in update_data:
        await scheduler.update_interval(update_data["scan_interval_minutes"])

    return await get_settings(db)


@router.post("/backup/export")
async def export_backup(db: AsyncSession = Depends(get_db)):
    """Export configuration as JSON backup."""
    # Get all connections (without passwords)
    result = await db.execute(select(Connection))
    connections = [
        {
            "type": c.type,
            "name": c.name,
            "url": c.url,
            "api_key": c.api_key,
            "username": c.username,
            "enabled": c.enabled,
        }
        for c in result.scalars().all()
    ]

    # Get all trackers
    result = await db.execute(select(Tracker))
    trackers = [
        {
            "name": t.name,
            "patterns": t.patterns,
            "prowlarr_indexer_id": t.prowlarr_indexer_id,
        }
        for t in result.scalars().all()
    ]

    # Get all rules
    result = await db.execute(select(Rule))
    rules = [
        {
            "name": r.name,
            "priority": r.priority,
            "enabled": r.enabled,
            "conditions": r.conditions,
            "criteria": r.criteria,
            "exceptions": r.exceptions,
            "action": r.action,
            "action_params": r.action_params,
            "notify": r.notify,
            "notify_connections": r.notify_connections,
        }
        for r in result.scalars().all()
    ]

    # Get all settings
    result = await db.execute(select(Settings))
    settings_dict = {s.key: s.value for s in result.scalars().all()}

    backup = {
        "version": settings.app_version,
        "exported_at": datetime.utcnow().isoformat(),
        "connections": connections,
        "trackers": trackers,
        "rules": rules,
        "settings": settings_dict,
    }

    return JSONResponse(
        content=backup,
        headers={"Content-Disposition": "attachment; filename=seedarr_backup.json"},
    )


@router.post("/backup/import")
async def import_backup(backup: BackupData, db: AsyncSession = Depends(get_db)):
    """Import configuration from JSON backup."""
    imported = {"connections": 0, "trackers": 0, "rules": 0, "settings": 0}

    # Import connections
    for conn_data in backup.connections:
        connection = Connection(**conn_data)
        db.add(connection)
        imported["connections"] += 1

    # Import trackers
    for tracker_data in backup.trackers:
        tracker = Tracker(**tracker_data)
        db.add(tracker)
        imported["trackers"] += 1

    # Import rules
    for rule_data in backup.rules:
        rule = Rule(**rule_data)
        db.add(rule)
        imported["rules"] += 1

    # Import settings
    for key, value in backup.settings.items():
        result = await db.execute(select(Settings).where(Settings.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = value
        else:
            setting = Settings(key=key, value=value)
            db.add(setting)
        imported["settings"] += 1

    await db.commit()

    return {"message": "Backup imported successfully", "imported": imported}
