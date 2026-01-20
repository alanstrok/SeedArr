"""Trackers API routes."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import Tracker, Torrent
from app.schemas.tracker import (
    TrackerCreate,
    TrackerUpdate,
    TrackerResponse,
    TrackerStatsResponse,
    DiscoveredTracker,
)
from app.services.tracker_discovery import TrackerDiscoveryService

router = APIRouter()


@router.get("", response_model=List[TrackerResponse])
async def list_trackers(db: AsyncSession = Depends(get_db)):
    """List all trackers."""
    result = await db.execute(select(Tracker).order_by(Tracker.name))
    trackers = result.scalars().all()
    return trackers


@router.post("", response_model=TrackerResponse, status_code=status.HTTP_201_CREATED)
async def create_tracker(data: TrackerCreate, db: AsyncSession = Depends(get_db)):
    """Create a new tracker."""
    tracker = Tracker(
        name=data.name,
        patterns=data.patterns,
        prowlarr_indexer_id=data.prowlarr_indexer_id,
        default_rule_id=data.default_rule_id,
    )
    db.add(tracker)
    await db.commit()
    await db.refresh(tracker)
    return tracker


@router.get("/{tracker_id}", response_model=TrackerResponse)
async def get_tracker(tracker_id: int, db: AsyncSession = Depends(get_db)):
    """Get a tracker by ID."""
    result = await db.execute(select(Tracker).where(Tracker.id == tracker_id))
    tracker = result.scalar_one_or_none()
    if not tracker:
        raise HTTPException(status_code=404, detail="Tracker not found")
    return tracker


@router.put("/{tracker_id}", response_model=TrackerResponse)
async def update_tracker(
    tracker_id: int, data: TrackerUpdate, db: AsyncSession = Depends(get_db)
):
    """Update a tracker."""
    result = await db.execute(select(Tracker).where(Tracker.id == tracker_id))
    tracker = result.scalar_one_or_none()
    if not tracker:
        raise HTTPException(status_code=404, detail="Tracker not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(tracker, key, value)

    await db.commit()
    await db.refresh(tracker)
    return tracker


@router.delete("/{tracker_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tracker(tracker_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a tracker."""
    result = await db.execute(select(Tracker).where(Tracker.id == tracker_id))
    tracker = result.scalar_one_or_none()
    if not tracker:
        raise HTTPException(status_code=404, detail="Tracker not found")

    await db.delete(tracker)
    await db.commit()


@router.post("/discover", response_model=List[DiscoveredTracker])
async def discover_trackers(db: AsyncSession = Depends(get_db)):
    """Auto-discover trackers from qBittorrent and Prowlarr."""
    service = TrackerDiscoveryService(db)
    discovered = await service.merge_discoveries()
    return [DiscoveredTracker(**d) for d in discovered]


@router.get("/{tracker_id}/stats", response_model=TrackerStatsResponse)
async def get_tracker_stats(tracker_id: int, db: AsyncSession = Depends(get_db)):
    """Get detailed stats for a tracker."""
    result = await db.execute(select(Tracker).where(Tracker.id == tracker_id))
    tracker = result.scalar_one_or_none()
    if not tracker:
        raise HTTPException(status_code=404, detail="Tracker not found")

    # Get torrent stats
    result = await db.execute(
        select(Torrent).where(Torrent.tracker_id == tracker_id)
    )
    torrents = result.scalars().all()

    total_torrents = len(torrents)
    active_states = ["uploading", "stalledUP", "forcedUP", "queuedUP"]
    active_torrents = len([t for t in torrents if t.state in active_states])
    total_upload = sum(t.uploaded_bytes for t in torrents)
    total_download = sum(t.downloaded_bytes for t in torrents)
    average_ratio = sum(t.ratio for t in torrents) / max(len(torrents), 1)
    seed_time_avg = sum(t.seed_time_seconds for t in torrents) / max(len(torrents), 1) / 3600

    # Get top categories
    category_counts = {}
    for t in torrents:
        cat = t.category or "uncategorized"
        category_counts[cat] = category_counts.get(cat, 0) + 1

    top_categories = [
        {"name": name, "count": count}
        for name, count in sorted(category_counts.items(), key=lambda x: -x[1])[:5]
    ]

    return TrackerStatsResponse(
        id=tracker.id,
        name=tracker.name,
        total_torrents=total_torrents,
        active_torrents=active_torrents,
        total_upload=total_upload,
        total_download=total_download,
        average_ratio=average_ratio,
        seed_time_average_hours=seed_time_avg,
        top_categories=top_categories,
    )


@router.post("/{tracker_id}/update-stats", response_model=TrackerResponse)
async def update_tracker_stats(tracker_id: int, db: AsyncSession = Depends(get_db)):
    """Recalculate and update tracker statistics."""
    result = await db.execute(select(Tracker).where(Tracker.id == tracker_id))
    tracker = result.scalar_one_or_none()
    if not tracker:
        raise HTTPException(status_code=404, detail="Tracker not found")

    # Get torrent stats
    result = await db.execute(
        select(Torrent).where(Torrent.tracker_id == tracker_id)
    )
    torrents = result.scalars().all()

    if torrents:
        tracker.stats_torrent_count = len(torrents)
        tracker.stats_upload = sum(t.uploaded_bytes for t in torrents)
        tracker.stats_download = sum(t.downloaded_bytes for t in torrents)
        tracker.stats_ratio = sum(t.ratio for t in torrents) / len(torrents)
    else:
        tracker.stats_torrent_count = 0
        tracker.stats_upload = 0
        tracker.stats_download = 0
        tracker.stats_ratio = 0

    await db.commit()
    await db.refresh(tracker)
    return tracker
