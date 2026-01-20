"""Trackers API routes with zone-based seeding rules."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Tracker, Torrent
from app.schemas.tracker import (
    TrackerCreate,
    TrackerUpdate,
    TrackerResponse,
    TrackerStatsResponse,
    DiscoveredTracker,
    TrackerZoneSummary,
)
from app.services.tracker_discovery import TrackerDiscoveryService

router = APIRouter()


@router.get("", response_model=List[TrackerResponse])
async def list_trackers(db: AsyncSession = Depends(get_db)):
    """List all trackers with their zone configurations."""
    result = await db.execute(select(Tracker).order_by(Tracker.name))
    trackers = result.scalars().all()
    return trackers


@router.post("", response_model=TrackerResponse, status_code=status.HTTP_201_CREATED)
async def create_tracker(data: TrackerCreate, db: AsyncSession = Depends(get_db)):
    """Create a new tracker with zone-based seeding rules."""
    tracker = Tracker(
        name=data.name,
        patterns=data.patterns,
        prowlarr_indexer_id=data.prowlarr_indexer_id,
        prowlarr_indexer_name=data.prowlarr_indexer_name,
        enabled=data.enabled,
        # Zone 1: Obligations
        min_seed_time_hours=data.min_seed_time_hours,
        min_ratio=data.min_ratio,
        min_operator=data.min_operator,
        # Zone 2: Preferences
        keep_if_seeders_below=data.keep_if_seeders_below,
        keep_if_activity_within_hours=data.keep_if_activity_within_hours,
        permaseed=data.permaseed,
        # Zone 3: Deletion
        deletion_priority=data.deletion_priority,
        max_seed_time_hours=data.max_seed_time_hours,
    )
    db.add(tracker)
    await db.commit()
    await db.refresh(tracker)
    return tracker


@router.get("/zone-summary", response_model=TrackerZoneSummary)
async def get_zone_summary(db: AsyncSession = Depends(get_db)):
    """Get summary of zone distribution across all trackers."""
    result = await db.execute(select(Tracker).order_by(Tracker.name))
    trackers = result.scalars().all()

    total_zone1 = sum(t.stats_zone1_count for t in trackers)
    total_zone2 = sum(t.stats_zone2_count for t in trackers)
    total_zone3 = sum(t.stats_zone3_count for t in trackers)

    tracker_list = [
        {
            "id": t.id,
            "name": t.name,
            "zone1": t.stats_zone1_count,
            "zone2": t.stats_zone2_count,
            "zone3": t.stats_zone3_count,
            "total": t.stats_torrent_count,
        }
        for t in trackers
    ]

    return TrackerZoneSummary(
        total_zone1=total_zone1,
        total_zone2=total_zone2,
        total_zone3=total_zone3,
        trackers=tracker_list,
    )


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
    """Update a tracker's configuration including zone rules."""
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
    """Get detailed stats for a tracker including zone distribution."""
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

    # Zone distribution
    zone1_count = len([t for t in torrents if t.zone == 1])
    zone2_count = len([t for t in torrents if t.zone == 2])
    zone3_count = len([t for t in torrents if t.zone == 3])

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
        zone1_count=zone1_count,
        zone2_count=zone2_count,
        zone3_count=zone3_count,
    )


@router.post("/{tracker_id}/update-stats", response_model=TrackerResponse)
async def update_tracker_stats(tracker_id: int, db: AsyncSession = Depends(get_db)):
    """Recalculate and update tracker statistics including zone counts."""
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
        tracker.stats_zone1_count = len([t for t in torrents if t.zone == 1])
        tracker.stats_zone2_count = len([t for t in torrents if t.zone == 2])
        tracker.stats_zone3_count = len([t for t in torrents if t.zone == 3])
    else:
        tracker.stats_torrent_count = 0
        tracker.stats_upload = 0
        tracker.stats_download = 0
        tracker.stats_ratio = 0
        tracker.stats_zone1_count = 0
        tracker.stats_zone2_count = 0
        tracker.stats_zone3_count = 0

    await db.commit()
    await db.refresh(tracker)
    return tracker


@router.post("/{tracker_id}/toggle", response_model=TrackerResponse)
async def toggle_tracker(tracker_id: int, db: AsyncSession = Depends(get_db)):
    """Toggle tracker enabled/disabled status."""
    result = await db.execute(select(Tracker).where(Tracker.id == tracker_id))
    tracker = result.scalar_one_or_none()
    if not tracker:
        raise HTTPException(status_code=404, detail="Tracker not found")

    tracker.enabled = not tracker.enabled
    await db.commit()
    await db.refresh(tracker)
    return tracker


@router.post("/{tracker_id}/permaseed", response_model=TrackerResponse)
async def toggle_permaseed(tracker_id: int, db: AsyncSession = Depends(get_db)):
    """Toggle permaseed status for a tracker."""
    result = await db.execute(select(Tracker).where(Tracker.id == tracker_id))
    tracker = result.scalar_one_or_none()
    if not tracker:
        raise HTTPException(status_code=404, detail="Tracker not found")

    tracker.permaseed = not tracker.permaseed
    await db.commit()
    await db.refresh(tracker)
    return tracker
