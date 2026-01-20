"""Scheduler service for periodic scans and disk space management."""
from datetime import datetime
from typing import Optional, Callable
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Settings, Torrent, Tracker, Connection
from app.models.settings import DEFAULT_SETTINGS
from app.services.qbittorrent import QBittorrentService
from app.services.rule_engine import ZoneEngine
from app.core.security import decrypt_password


class SchedulerService:
    """Service for managing scheduled tasks."""

    def __init__(self):
        """Initialize scheduler service."""
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._started = False
        self._last_scan: Optional[datetime] = None
        self._last_zone_counts: Optional[dict] = None
        self._scan_in_progress = False
        self._start_time: Optional[datetime] = None
        self._db_session_factory: Optional[Callable[[], AsyncSession]] = None

    def set_db_session_factory(self, factory: Callable[[], AsyncSession]):
        """Set the database session factory."""
        self._db_session_factory = factory

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._started and self._scheduler is not None

    @property
    def last_scan(self) -> Optional[datetime]:
        """Get last scan time."""
        return self._last_scan

    @property
    def last_zone_counts(self) -> Optional[dict]:
        """Get last zone counts."""
        return self._last_zone_counts

    @property
    def uptime_seconds(self) -> float:
        """Get uptime in seconds."""
        if self._start_time:
            return (datetime.utcnow() - self._start_time).total_seconds()
        return 0

    async def _get_setting(self, db: AsyncSession, key: str):
        """Get a setting value."""
        result = await db.execute(select(Settings).where(Settings.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            return setting.value
        return DEFAULT_SETTINGS.get(key)

    async def _get_qbittorrent_connection(self, db: AsyncSession) -> Optional[Connection]:
        """Get the first enabled qBittorrent connection."""
        result = await db.execute(
            select(Connection).where(
                Connection.type == "qbittorrent",
                Connection.enabled == True,
            )
        )
        return result.scalar_one_or_none()

    async def _sync_torrents(self, db: AsyncSession) -> int:
        """Sync torrents from qBittorrent to local cache."""
        connection = await self._get_qbittorrent_connection(db)
        if not connection:
            logger.warning("No qBittorrent connection configured")
            return 0

        qbt = QBittorrentService(
            url=connection.url,
            username=connection.username or "",
            password=decrypt_password(connection.password) if connection.password else "",
        )

        if not await qbt.connect():
            logger.error("Failed to connect to qBittorrent")
            return 0

        try:
            torrents = await qbt.get_torrents()
            logger.info(f"Fetched {len(torrents)} torrents from qBittorrent")

            # Get all trackers for matching
            result = await db.execute(select(Tracker))
            trackers = result.scalars().all()

            # Get existing torrent hashes
            result = await db.execute(select(Torrent.hash))
            existing_hashes = set(row[0] for row in result.all())

            synced = 0
            for t in torrents:
                # Match tracker
                tracker_id = None
                for tracker in trackers:
                    patterns = tracker.patterns or []
                    for pattern in patterns:
                        if pattern.lower() in t.tracker.lower():
                            tracker_id = tracker.id
                            break
                    if tracker_id:
                        break

                if t.hash in existing_hashes:
                    # Update existing
                    result = await db.execute(
                        select(Torrent).where(Torrent.hash == t.hash)
                    )
                    torrent = result.scalar_one()
                    torrent.name = t.name
                    torrent.tracker_id = tracker_id
                    torrent.category = t.category
                    torrent.tags = t.tags
                    torrent.size_bytes = t.size
                    torrent.ratio = t.ratio
                    torrent.uploaded_bytes = t.uploaded
                    torrent.downloaded_bytes = t.downloaded
                    torrent.seed_time_seconds = t.seeding_time
                    torrent.last_activity = t.last_activity
                    torrent.num_seeds = t.num_seeds
                    torrent.num_leeches = t.num_leechs
                    torrent.state = t.state
                    torrent.save_path = t.save_path
                    torrent.last_scanned = datetime.utcnow()
                else:
                    # Create new
                    torrent = Torrent(
                        hash=t.hash,
                        name=t.name,
                        tracker_id=tracker_id,
                        category=t.category,
                        tags=t.tags,
                        size_bytes=t.size,
                        ratio=t.ratio,
                        uploaded_bytes=t.uploaded,
                        downloaded_bytes=t.downloaded,
                        seed_time_seconds=t.seeding_time,
                        added_on=t.added_on,
                        completion_on=t.completion_on,
                        last_activity=t.last_activity,
                        num_seeds=t.num_seeds,
                        num_leeches=t.num_leechs,
                        state=t.state,
                        save_path=t.save_path,
                        last_scanned=datetime.utcnow(),
                    )
                    db.add(torrent)

                synced += 1

            # Remove torrents that no longer exist in qBittorrent
            current_hashes = set(t.hash for t in torrents)
            removed_hashes = existing_hashes - current_hashes
            if removed_hashes:
                await db.execute(
                    Torrent.__table__.delete().where(Torrent.hash.in_(removed_hashes))
                )
                logger.info(f"Removed {len(removed_hashes)} orphaned torrents from cache")

            # Update tracker statistics
            await self._update_tracker_stats(db)

            await db.commit()
            return synced

        finally:
            await qbt.disconnect()

    async def _update_tracker_stats(self, db: AsyncSession):
        """Update tracker statistics from cached torrents."""
        result = await db.execute(select(Tracker))
        trackers = result.scalars().all()

        for tracker in trackers:
            result = await db.execute(
                select(Torrent).where(Torrent.tracker_id == tracker.id)
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

    async def _run_scheduled_scan(self):
        """Run scheduled scan task - update zones and cleanup if needed."""
        if self._scan_in_progress:
            logger.warning("Scan already in progress, skipping")
            return

        if not self._db_session_factory:
            logger.error("No database session factory configured")
            return

        self._scan_in_progress = True
        try:
            async with self._db_session_factory() as db:
                logger.info("Starting scheduled scan")

                # First sync torrents
                synced = await self._sync_torrents(db)
                logger.info(f"Synced {synced} torrents")

                # Get qBittorrent connection
                connection = await self._get_qbittorrent_connection(db)
                if not connection:
                    logger.warning("No qBittorrent connection for scan")
                    return

                # Create services
                qbt = QBittorrentService(
                    url=connection.url,
                    username=connection.username or "",
                    password=decrypt_password(connection.password) if connection.password else "",
                )

                if not await qbt.connect():
                    logger.error("Failed to connect to qBittorrent for scan")
                    return

                try:
                    # Run zone evaluation and disk cleanup if needed
                    engine = ZoneEngine(db, qbt)

                    # Get disk space settings
                    threshold = await self._get_setting(db, "disk_space_threshold_percent") or 10
                    target = threshold + 5  # Target 5% above threshold

                    # Run cleanup (will only delete if needed)
                    result = await engine.cleanup_for_disk_space(
                        target_free_percent=target,
                        dry_run=False,
                        path="/downloads"  # TODO: Make configurable
                    )

                    self._last_scan = datetime.utcnow()
                    self._last_zone_counts = {
                        1: result.zone1_count,
                        2: result.zone2_count,
                        3: result.zone3_count,
                    }

                    logger.info(
                        f"Scheduled scan completed: "
                        f"Z1={result.zone1_count}, Z2={result.zone2_count}, Z3={result.zone3_count}, "
                        f"deleted={result.deleted_count}"
                    )
                finally:
                    await qbt.disconnect()

        except Exception as e:
            logger.exception(f"Error during scheduled scan: {e}")
        finally:
            self._scan_in_progress = False

    async def start(self, interval_minutes: int = 15):
        """Start the scheduler."""
        if self._started:
            logger.warning("Scheduler already started")
            return

        self._scheduler = AsyncIOScheduler()
        self._scheduler.add_job(
            self._run_scheduled_scan,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id="scan_job",
            name="Torrent Scan",
            replace_existing=True,
        )
        self._scheduler.start()
        self._started = True
        self._start_time = datetime.utcnow()
        logger.info(f"Scheduler started with {interval_minutes} minute interval")

    async def stop(self):
        """Stop the scheduler."""
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
        self._started = False
        logger.info("Scheduler stopped")

    async def update_interval(self, interval_minutes: int):
        """Update the scan interval."""
        if not self._started or not self._scheduler:
            return

        self._scheduler.reschedule_job(
            "scan_job",
            trigger=IntervalTrigger(minutes=interval_minutes),
        )
        logger.info(f"Scan interval updated to {interval_minutes} minutes")

    async def trigger_scan(self, dry_run: bool = False):
        """Manually trigger a scan/cleanup."""
        if self._scan_in_progress:
            raise RuntimeError("Scan already in progress")

        if not self._db_session_factory:
            raise RuntimeError("No database session factory configured")

        self._scan_in_progress = True
        try:
            async with self._db_session_factory() as db:
                # Sync torrents first
                synced = await self._sync_torrents(db)
                logger.info(f"Synced {synced} torrents")

                # Get qBittorrent connection
                connection = await self._get_qbittorrent_connection(db)
                if not connection:
                    raise RuntimeError("No qBittorrent connection configured")

                qbt = QBittorrentService(
                    url=connection.url,
                    username=connection.username or "",
                    password=decrypt_password(connection.password) if connection.password else "",
                )

                if not await qbt.connect():
                    raise RuntimeError("Failed to connect to qBittorrent")

                try:
                    engine = ZoneEngine(db, qbt)

                    # Get disk space settings
                    threshold = await self._get_setting(db, "disk_space_threshold_percent") or 10
                    target = threshold + 5

                    result = await engine.cleanup_for_disk_space(
                        target_free_percent=target,
                        dry_run=dry_run,
                        path="/downloads"
                    )

                    self._last_scan = datetime.utcnow()
                    self._last_zone_counts = {
                        1: result.zone1_count,
                        2: result.zone2_count,
                        3: result.zone3_count,
                    }

                    return result
                finally:
                    await qbt.disconnect()
        finally:
            self._scan_in_progress = False

    async def update_zones_only(self):
        """Update zone status for all torrents without cleanup."""
        if not self._db_session_factory:
            raise RuntimeError("No database session factory configured")

        async with self._db_session_factory() as db:
            # Sync torrents first
            synced = await self._sync_torrents(db)
            logger.info(f"Synced {synced} torrents")

            # Get qBittorrent connection
            connection = await self._get_qbittorrent_connection(db)
            if not connection:
                raise RuntimeError("No qBittorrent connection configured")

            qbt = QBittorrentService(
                url=connection.url,
                username=connection.username or "",
                password=decrypt_password(connection.password) if connection.password else "",
            )

            if not await qbt.connect():
                raise RuntimeError("Failed to connect to qBittorrent")

            try:
                engine = ZoneEngine(db, qbt)
                zone_counts = await engine.update_all_zones()
                self._last_zone_counts = zone_counts
                return zone_counts
            finally:
                await qbt.disconnect()


# Global scheduler instance
scheduler = SchedulerService()
