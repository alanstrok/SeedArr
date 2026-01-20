"""Torrents API routes."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.database import get_db
from app.models import Torrent, Tracker, Rule, ActionLog, Connection
from app.schemas.torrent import (
    TorrentResponse,
    TorrentListResponse,
    TorrentHistoryResponse,
    TorrentProtectRequest,
)
from app.services.qbittorrent import QBittorrentService
from app.core.security import decrypt_password

router = APIRouter()


def _torrent_to_response(torrent: Torrent) -> dict:
    """Convert torrent model to response dict."""
    return {
        "hash": torrent.hash,
        "name": torrent.name,
        "tracker_id": torrent.tracker_id,
        "tracker_name": torrent.tracker.name if torrent.tracker else None,
        "category": torrent.category,
        "tags": torrent.tags or [],
        "size_bytes": torrent.size_bytes,
        "ratio": torrent.ratio,
        "uploaded_bytes": torrent.uploaded_bytes,
        "downloaded_bytes": torrent.downloaded_bytes,
        "seed_time_seconds": torrent.seed_time_seconds,
        "added_on": torrent.added_on,
        "completion_on": torrent.completion_on,
        "last_activity": torrent.last_activity,
        "num_seeds": torrent.num_seeds,
        "num_leeches": torrent.num_leeches,
        "state": torrent.state,
        "save_path": torrent.save_path,
        "protected": torrent.protected,
        "matched_rule_id": torrent.matched_rule_id,
        "matched_rule_name": torrent.matched_rule.name if torrent.matched_rule else None,
        "last_scanned": torrent.last_scanned,
        "created_at": torrent.created_at,
        "updated_at": torrent.updated_at,
    }


@router.get("", response_model=TorrentListResponse)
async def list_torrents(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    tracker_id: Optional[int] = None,
    category: Optional[str] = None,
    state: Optional[str] = None,
    protected: Optional[bool] = None,
    search: Optional[str] = None,
    sort_by: str = Query("added_on", regex="^(name|ratio|size_bytes|seed_time_seconds|added_on)$"),
    sort_desc: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """List all torrents with pagination and filters."""
    query = select(Torrent)

    # Apply filters
    if tracker_id:
        query = query.where(Torrent.tracker_id == tracker_id)
    if category:
        query = query.where(Torrent.category == category)
    if state:
        query = query.where(Torrent.state == state)
    if protected is not None:
        query = query.where(Torrent.protected == protected)
    if search:
        query = query.where(Torrent.name.ilike(f"%{search}%"))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply sorting
    sort_column = getattr(Torrent, sort_by)
    if sort_desc:
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    torrents = result.scalars().all()

    pages = (total + per_page - 1) // per_page

    return TorrentListResponse(
        items=[TorrentResponse(**_torrent_to_response(t)) for t in torrents],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/{torrent_hash}", response_model=TorrentResponse)
async def get_torrent(torrent_hash: str, db: AsyncSession = Depends(get_db)):
    """Get a torrent by hash."""
    result = await db.execute(
        select(Torrent).where(Torrent.hash == torrent_hash.lower())
    )
    torrent = result.scalar_one_or_none()
    if not torrent:
        raise HTTPException(status_code=404, detail="Torrent not found")
    return TorrentResponse(**_torrent_to_response(torrent))


@router.put("/{torrent_hash}/protect", response_model=TorrentResponse)
async def protect_torrent(
    torrent_hash: str,
    data: TorrentProtectRequest,
    db: AsyncSession = Depends(get_db),
):
    """Protect or unprotect a torrent."""
    result = await db.execute(
        select(Torrent).where(Torrent.hash == torrent_hash.lower())
    )
    torrent = result.scalar_one_or_none()
    if not torrent:
        raise HTTPException(status_code=404, detail="Torrent not found")

    torrent.protected = data.protected
    await db.commit()
    await db.refresh(torrent)

    # Log the action
    action = "protected" if data.protected else "unprotected"
    log = ActionLog(
        torrent_hash=torrent.hash,
        torrent_name=torrent.name,
        tracker_id=torrent.tracker_id,
        rule_id=None,
        action=action,
        reason=f"Manually {action} by user",
        dry_run=False,
    )
    db.add(log)
    await db.commit()

    return TorrentResponse(**_torrent_to_response(torrent))


@router.delete("/{torrent_hash}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_torrent(
    torrent_hash: str,
    delete_files: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Force delete a torrent."""
    result = await db.execute(
        select(Torrent).where(Torrent.hash == torrent_hash.lower())
    )
    torrent = result.scalar_one_or_none()
    if not torrent:
        raise HTTPException(status_code=404, detail="Torrent not found")

    # Get qBittorrent connection
    result = await db.execute(
        select(Connection).where(
            Connection.type == "qbittorrent",
            Connection.enabled == True,
        )
    )
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=400, detail="No qBittorrent connection")

    qbt = QBittorrentService(
        url=connection.url,
        username=connection.username or "",
        password=decrypt_password(connection.password) if connection.password else "",
    )

    if not await qbt.connect():
        raise HTTPException(status_code=400, detail="Failed to connect to qBittorrent")

    try:
        success = await qbt.delete_torrent(torrent_hash, delete_files=delete_files)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete torrent")

        # Log the action
        log = ActionLog(
            torrent_hash=torrent.hash,
            torrent_name=torrent.name,
            tracker_id=torrent.tracker_id,
            rule_id=None,
            action="deleted",
            reason="Manually deleted by user",
            dry_run=False,
        )
        db.add(log)

        # Remove from cache
        await db.delete(torrent)
        await db.commit()
    finally:
        await qbt.disconnect()


@router.get("/{torrent_hash}/history", response_model=List[TorrentHistoryResponse])
async def get_torrent_history(torrent_hash: str, db: AsyncSession = Depends(get_db)):
    """Get action history for a torrent."""
    result = await db.execute(
        select(ActionLog)
        .where(ActionLog.torrent_hash == torrent_hash.lower())
        .order_by(ActionLog.created_at.desc())
    )
    logs = result.scalars().all()

    return [
        TorrentHistoryResponse(
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
    ]


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_torrents(db: AsyncSession = Depends(get_db)):
    """Force refresh torrents from qBittorrent."""
    from app.services.scheduler import scheduler

    if not scheduler._db_session_factory:
        # Set up db factory if not already done
        from app.database import async_session_maker
        scheduler.set_db_session_factory(async_session_maker)

    synced = await scheduler._sync_torrents(db)
    return {"message": f"Synced {synced} torrents", "count": synced}


@router.get("/categories/list")
async def list_categories(db: AsyncSession = Depends(get_db)):
    """Get list of unique categories."""
    result = await db.execute(
        select(Torrent.category).distinct().where(Torrent.category != "")
    )
    categories = [row[0] for row in result.all()]
    return {"categories": sorted(categories)}


@router.get("/states/list")
async def list_states(db: AsyncSession = Depends(get_db)):
    """Get list of unique states."""
    result = await db.execute(select(Torrent.state).distinct())
    states = [row[0] for row in result.all()]
    return {"states": sorted(states)}
