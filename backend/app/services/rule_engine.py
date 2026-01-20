"""Zone-based Rule Engine for intelligent seeding management.

Philosophy:
- Zone 1 (Obligations): NEVER delete before these conditions - avoid Hit & Run
- Zone 2 (Preferences): Keep if possible even after obligations are met
- Zone 3 (Eligible): Can be deleted when disk space is needed

Torrents are only deleted when:
1. They have passed Zone 1 AND Zone 2
2. Disk space is critically low OR max_seed_time exceeded
"""
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import shutil

from app.models import Torrent, ActionLog, Tracker, Settings
from app.models.settings import DEFAULT_SETTINGS
from app.services.qbittorrent import QBittorrentService


@dataclass
class ZoneResult:
    """Result of zone evaluation for a torrent."""
    zone: int  # 1, 2, or 3
    reason: str
    deletion_score: float
    hours_until_zone2: Optional[float] = None
    ratio_until_zone2: Optional[float] = None


@dataclass
class DiskSpaceInfo:
    """Disk space information."""
    total_bytes: int
    free_bytes: int
    used_bytes: int
    free_percent: float
    is_critical: bool


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""
    dry_run: bool
    started_at: datetime
    completed_at: datetime
    torrents_evaluated: int
    zone1_count: int
    zone2_count: int
    zone3_count: int
    deleted_count: int
    bytes_freed: int
    disk_before: DiskSpaceInfo
    disk_after: Optional[DiskSpaceInfo]
    deleted_torrents: List[dict]


class ZoneEngine:
    """Engine for zone-based torrent management."""

    def __init__(self, db: AsyncSession, qbt_service: QBittorrentService):
        """Initialize zone engine."""
        self.db = db
        self.qbt = qbt_service

    async def _get_setting(self, key: str):
        """Get a setting value."""
        result = await self.db.execute(select(Settings).where(Settings.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            return setting.value
        return DEFAULT_SETTINGS.get(key)

    async def _get_protected_tags(self) -> List[str]:
        """Get list of protected tags."""
        return await self._get_setting("protected_tags") or []

    async def _get_protected_categories(self) -> List[str]:
        """Get list of protected categories."""
        return await self._get_setting("protected_categories") or []

    def _get_disk_space(self, path: str = "/") -> DiskSpaceInfo:
        """Get disk space information."""
        try:
            usage = shutil.disk_usage(path)
            free_percent = (usage.free / usage.total) * 100
            threshold = 10  # Default threshold
            return DiskSpaceInfo(
                total_bytes=usage.total,
                free_bytes=usage.free,
                used_bytes=usage.used,
                free_percent=free_percent,
                is_critical=free_percent < threshold,
            )
        except Exception as e:
            logger.error(f"Failed to get disk space: {e}")
            return DiskSpaceInfo(
                total_bytes=0,
                free_bytes=0,
                used_bytes=0,
                free_percent=100,
                is_critical=False,
            )

    async def _is_torrent_protected(self, torrent: Torrent) -> Tuple[bool, str]:
        """Check if torrent is manually protected or has protected tags/categories."""
        # Manual protection
        if torrent.protected:
            return True, "Manually protected"

        # Protected tags
        protected_tags = await self._get_protected_tags()
        torrent_tags = torrent.tags or []
        for tag in protected_tags:
            if tag in torrent_tags:
                return True, f"Protected tag: {tag}"

        # Protected categories
        protected_categories = await self._get_protected_categories()
        if torrent.category in protected_categories:
            return True, f"Protected category: {torrent.category}"

        return False, ""

    def _check_zone1_obligations(self, torrent: Torrent, tracker: Tracker) -> Tuple[bool, str, Optional[float], Optional[float]]:
        """Check if torrent has met Zone 1 obligations.

        Returns:
            (passed, reason, hours_until_clear, ratio_until_clear)
        """
        seed_time_hours = torrent.seed_time_seconds / 3600
        min_time = tracker.min_seed_time_hours
        min_ratio = tracker.min_ratio
        operator = tracker.min_operator

        time_met = seed_time_hours >= min_time
        ratio_met = torrent.ratio >= min_ratio

        # Calculate remaining time/ratio
        hours_remaining = max(0, min_time - seed_time_hours) if not time_met else None
        ratio_remaining = max(0, min_ratio - torrent.ratio) if not ratio_met else None

        if operator == "OR":
            # Either condition clears Zone 1
            if time_met or ratio_met:
                if time_met:
                    reason = f"Seeded {seed_time_hours:.1f}h (min: {min_time}h)"
                else:
                    reason = f"Ratio {torrent.ratio:.2f} (min: {min_ratio})"
                return True, reason, None, None
            else:
                reason = f"Need {min_time}h OR ratio {min_ratio} (current: {seed_time_hours:.1f}h, ratio {torrent.ratio:.2f})"
                return False, reason, hours_remaining, ratio_remaining
        else:  # AND
            # Both conditions required to clear Zone 1
            if time_met and ratio_met:
                reason = f"Seeded {seed_time_hours:.1f}h AND ratio {torrent.ratio:.2f}"
                return True, reason, None, None
            else:
                missing = []
                if not time_met:
                    missing.append(f"{hours_remaining:.1f}h more seeding")
                if not ratio_met:
                    missing.append(f"ratio {ratio_remaining:.2f} more")
                reason = f"Need: {' AND '.join(missing)}"
                return False, reason, hours_remaining, ratio_remaining

    def _check_zone2_preferences(self, torrent: Torrent, tracker: Tracker) -> Tuple[bool, str]:
        """Check if torrent should be kept due to Zone 2 preferences.

        Returns:
            (should_keep, reason)
        """
        # Permaseed - never delete
        if tracker.permaseed:
            return True, "Permaseed enabled"

        # Low seeders
        if tracker.keep_if_seeders_below:
            if torrent.num_seeds < tracker.keep_if_seeders_below:
                return True, f"Only {torrent.num_seeds} seeders (threshold: {tracker.keep_if_seeders_below})"

        # Recent activity
        if tracker.keep_if_activity_within_hours:
            hours_since_activity = (datetime.utcnow() - torrent.last_activity).total_seconds() / 3600
            if hours_since_activity <= tracker.keep_if_activity_within_hours:
                return True, f"Active {hours_since_activity:.1f}h ago (threshold: {tracker.keep_if_activity_within_hours}h)"

        return False, ""

    def _calculate_deletion_score(self, torrent: Torrent, tracker: Tracker) -> float:
        """Calculate deletion priority score. Higher = delete first."""
        # Base score from tracker priority (1-100)
        score = tracker.deletion_priority * 100

        # Add days of inactivity
        days_inactive = (datetime.utcnow() - torrent.last_activity).days
        score += days_inactive * 10

        # Add seeders (more seeders = more likely to delete)
        score += torrent.num_seeds * 5

        # Reduce score for larger uploads (reward good ratio)
        if torrent.uploaded_bytes > 0:
            gb_uploaded = torrent.uploaded_bytes / (1024 ** 3)
            score -= gb_uploaded * 2

        return score

    async def evaluate_torrent(self, torrent: Torrent) -> ZoneResult:
        """Evaluate which zone a torrent belongs to."""
        # Check protection first
        is_protected, protect_reason = await self._is_torrent_protected(torrent)
        if is_protected:
            return ZoneResult(zone=1, reason=protect_reason, deletion_score=0)

        # Get tracker
        if not torrent.tracker_id:
            return ZoneResult(
                zone=1,
                reason="No tracker assigned - protected by default",
                deletion_score=0,
            )

        result = await self.db.execute(
            select(Tracker).where(Tracker.id == torrent.tracker_id)
        )
        tracker = result.scalar_one_or_none()

        if not tracker:
            return ZoneResult(
                zone=1,
                reason="Tracker not found - protected by default",
                deletion_score=0,
            )

        if not tracker.enabled:
            return ZoneResult(
                zone=1,
                reason=f"Tracker '{tracker.name}' is disabled",
                deletion_score=0,
            )

        # Check Zone 1 - Obligations
        zone1_passed, zone1_reason, hours_remaining, ratio_remaining = self._check_zone1_obligations(torrent, tracker)
        if not zone1_passed:
            return ZoneResult(
                zone=1,
                reason=f"Zone 1 (Obligations): {zone1_reason}",
                deletion_score=0,
                hours_until_zone2=hours_remaining,
                ratio_until_zone2=ratio_remaining,
            )

        # Check Zone 2 - Preferences
        keep_preferred, zone2_reason = self._check_zone2_preferences(torrent, tracker)
        if keep_preferred:
            return ZoneResult(
                zone=2,
                reason=f"Zone 2 (Preference): {zone2_reason}",
                deletion_score=0,
            )

        # Zone 3 - Eligible for deletion
        deletion_score = self._calculate_deletion_score(torrent, tracker)

        # Check forced deletion (max_seed_time)
        if tracker.max_seed_time_hours:
            seed_time_hours = torrent.seed_time_seconds / 3600
            if seed_time_hours >= tracker.max_seed_time_hours:
                return ZoneResult(
                    zone=3,
                    reason=f"Zone 3 (Forced): Exceeded max seed time ({seed_time_hours:.0f}h >= {tracker.max_seed_time_hours}h)",
                    deletion_score=deletion_score + 10000,  # High priority for forced deletion
                )

        return ZoneResult(
            zone=3,
            reason=f"Zone 3 (Eligible): Passed obligations ({zone1_reason})",
            deletion_score=deletion_score,
        )

    async def update_all_zones(self) -> dict:
        """Update zone status for all torrents."""
        result = await self.db.execute(select(Torrent))
        torrents = result.scalars().all()

        zone_counts = {1: 0, 2: 0, 3: 0}
        tracker_stats = {}

        for torrent in torrents:
            # Only evaluate seeding torrents
            if torrent.state not in ["uploading", "stalledUP", "pausedUP", "queuedUP", "forcedUP"]:
                continue

            zone_result = await self.evaluate_torrent(torrent)

            # Update torrent
            torrent.zone = zone_result.zone
            torrent.zone_reason = zone_result.reason
            torrent.deletion_score = zone_result.deletion_score
            torrent.hours_until_zone2 = zone_result.hours_until_zone2
            torrent.ratio_until_zone2 = zone_result.ratio_until_zone2

            zone_counts[zone_result.zone] += 1

            # Track per-tracker stats
            if torrent.tracker_id:
                if torrent.tracker_id not in tracker_stats:
                    tracker_stats[torrent.tracker_id] = {1: 0, 2: 0, 3: 0}
                tracker_stats[torrent.tracker_id][zone_result.zone] += 1

        await self.db.commit()

        # Update tracker zone counts
        for tracker_id, stats in tracker_stats.items():
            result = await self.db.execute(
                select(Tracker).where(Tracker.id == tracker_id)
            )
            tracker = result.scalar_one_or_none()
            if tracker:
                tracker.stats_zone1_count = stats[1]
                tracker.stats_zone2_count = stats[2]
                tracker.stats_zone3_count = stats[3]

        await self.db.commit()

        logger.info(f"Zone update: Z1={zone_counts[1]}, Z2={zone_counts[2]}, Z3={zone_counts[3]}")
        return zone_counts

    async def cleanup_for_disk_space(
        self,
        target_free_percent: float = 15.0,
        dry_run: bool = False,
        path: str = "/downloads"
    ) -> CleanupResult:
        """Delete Zone 3 torrents until target disk space is reached."""
        started_at = datetime.utcnow()
        deleted_torrents = []
        bytes_freed = 0

        # Get global dry_run setting
        global_dry_run = await self._get_setting("dry_run_mode")
        if global_dry_run:
            dry_run = True

        # Get current disk space
        disk_before = self._get_disk_space(path)
        logger.info(f"Disk space: {disk_before.free_percent:.1f}% free (critical: {disk_before.is_critical})")

        # Update all zones first
        zone_counts = await self.update_all_zones()

        # Check if cleanup needed
        if disk_before.free_percent >= target_free_percent and not dry_run:
            logger.info(f"Disk space OK ({disk_before.free_percent:.1f}% >= {target_free_percent}%), no cleanup needed")
            return CleanupResult(
                dry_run=dry_run,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                torrents_evaluated=sum(zone_counts.values()),
                zone1_count=zone_counts[1],
                zone2_count=zone_counts[2],
                zone3_count=zone_counts[3],
                deleted_count=0,
                bytes_freed=0,
                disk_before=disk_before,
                disk_after=disk_before,
                deleted_torrents=[],
            )

        # Get Zone 3 torrents sorted by deletion score (highest first)
        result = await self.db.execute(
            select(Torrent)
            .where(Torrent.zone == 3)
            .order_by(Torrent.deletion_score.desc())
        )
        eligible_torrents = result.scalars().all()

        logger.info(f"Found {len(eligible_torrents)} torrents eligible for deletion")

        # Calculate how much space we need to free
        bytes_to_free = int(disk_before.total_bytes * (target_free_percent - disk_before.free_percent) / 100)
        if bytes_to_free < 0:
            bytes_to_free = 0

        logger.info(f"Need to free {bytes_to_free / (1024**3):.2f} GB to reach {target_free_percent}% free")

        # Delete torrents until we reach target
        for torrent in eligible_torrents:
            if bytes_freed >= bytes_to_free and not dry_run:
                break

            # Get tracker name
            tracker_name = None
            if torrent.tracker_id:
                result = await self.db.execute(
                    select(Tracker).where(Tracker.id == torrent.tracker_id)
                )
                tracker = result.scalar_one_or_none()
                if tracker:
                    tracker_name = tracker.name

            if dry_run:
                deleted_torrents.append({
                    "hash": torrent.hash,
                    "name": torrent.name,
                    "tracker_name": tracker_name,
                    "size_bytes": torrent.size_bytes,
                    "deletion_score": torrent.deletion_score,
                    "reason": torrent.zone_reason,
                    "dry_run": True,
                })
                bytes_freed += torrent.size_bytes
            else:
                # Actually delete
                success = await self.qbt.delete_torrent(torrent.hash, delete_files=True)
                if success:
                    # Log the action
                    log = ActionLog(
                        torrent_hash=torrent.hash,
                        torrent_name=torrent.name,
                        tracker_id=torrent.tracker_id,
                        action="deleted",
                        reason=f"Disk cleanup: {torrent.zone_reason}",
                        dry_run=False,
                    )
                    self.db.add(log)

                    deleted_torrents.append({
                        "hash": torrent.hash,
                        "name": torrent.name,
                        "tracker_name": tracker_name,
                        "size_bytes": torrent.size_bytes,
                        "deletion_score": torrent.deletion_score,
                        "reason": torrent.zone_reason,
                        "dry_run": False,
                    })
                    bytes_freed += torrent.size_bytes

                    # Remove from cache
                    await self.db.delete(torrent)

                    logger.info(f"Deleted: {torrent.name[:50]}... ({torrent.size_bytes / (1024**3):.2f} GB)")

        await self.db.commit()

        disk_after = self._get_disk_space(path) if not dry_run else None

        completed_at = datetime.utcnow()
        logger.info(
            f"Cleanup completed: {len(deleted_torrents)} torrents, "
            f"{bytes_freed / (1024**3):.2f} GB freed (dry_run={dry_run})"
        )

        return CleanupResult(
            dry_run=dry_run,
            started_at=started_at,
            completed_at=completed_at,
            torrents_evaluated=sum(zone_counts.values()),
            zone1_count=zone_counts[1],
            zone2_count=zone_counts[2],
            zone3_count=zone_counts[3],
            deleted_count=len(deleted_torrents),
            bytes_freed=bytes_freed,
            disk_before=disk_before,
            disk_after=disk_after,
            deleted_torrents=deleted_torrents,
        )

    async def get_near_hnr_torrents(self, hours_threshold: float = 24.0) -> List[dict]:
        """Get torrents that are close to Hit & Run threshold."""
        result = await self.db.execute(
            select(Torrent)
            .where(Torrent.zone == 1)
            .where(Torrent.hours_until_zone2 != None)
            .where(Torrent.hours_until_zone2 <= hours_threshold)
            .order_by(Torrent.hours_until_zone2.asc())
        )
        torrents = result.scalars().all()

        alerts = []
        for torrent in torrents:
            tracker_name = None
            if torrent.tracker_id:
                result = await self.db.execute(
                    select(Tracker).where(Tracker.id == torrent.tracker_id)
                )
                tracker = result.scalar_one_or_none()
                if tracker:
                    tracker_name = tracker.name

            alerts.append({
                "hash": torrent.hash,
                "name": torrent.name,
                "tracker_name": tracker_name,
                "hours_until_zone2": torrent.hours_until_zone2,
                "ratio_until_zone2": torrent.ratio_until_zone2,
                "current_ratio": torrent.ratio,
                "seed_time_hours": torrent.seed_time_seconds / 3600,
            })

        return alerts


# Alias for backward compatibility
RuleEngine = ZoneEngine
