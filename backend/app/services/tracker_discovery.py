"""Tracker discovery service."""
from typing import List, Optional, Dict
from urllib.parse import urlparse
from collections import defaultdict
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from app.models import Connection, Tracker
from app.services.qbittorrent import QBittorrentService


class TrackerDiscoveryService:
    """Service for discovering trackers from qBittorrent and Prowlarr."""

    def __init__(self, db: AsyncSession):
        """Initialize tracker discovery service."""
        self.db = db

    async def _get_qbittorrent_connection(self) -> Optional[Connection]:
        """Get the first enabled qBittorrent connection."""
        result = await self.db.execute(
            select(Connection).where(
                Connection.type == "qbittorrent",
                Connection.enabled == True,
            )
        )
        return result.scalar_one_or_none()

    async def _get_prowlarr_connection(self) -> Optional[Connection]:
        """Get the first enabled Prowlarr connection."""
        result = await self.db.execute(
            select(Connection).where(
                Connection.type == "prowlarr",
                Connection.enabled == True,
            )
        )
        return result.scalar_one_or_none()

    def _extract_tracker_domain(self, url: str) -> str:
        """Extract domain from tracker URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            # Remove port if present
            if ":" in domain:
                domain = domain.split(":")[0]
            return domain
        except Exception:
            return url

    async def discover_from_qbittorrent(self) -> List[Dict]:
        """Discover trackers from qBittorrent torrents."""
        connection = await self._get_qbittorrent_connection()
        if not connection:
            logger.warning("No qBittorrent connection configured")
            return []

        qbt = QBittorrentService(
            url=connection.url,
            username=connection.username or "",
            password=connection.password or "",
        )

        if not await qbt.connect():
            logger.error("Failed to connect to qBittorrent")
            return []

        try:
            torrents = await qbt.get_torrents()

            # Group by tracker domain
            tracker_domains: Dict[str, int] = defaultdict(int)
            for t in torrents:
                if t.tracker:
                    domain = self._extract_tracker_domain(t.tracker)
                    if domain:
                        tracker_domains[domain] += 1

            # Convert to list of discovered trackers
            discovered = []
            for domain, count in sorted(tracker_domains.items(), key=lambda x: -x[1]):
                # Generate a name from domain
                name = domain.split(".")[0].upper()
                if len(name) < 2:
                    name = domain.replace(".", "_").upper()

                discovered.append({
                    "name": name,
                    "patterns": [domain],
                    "torrent_count": count,
                    "source": "qbittorrent",
                })

            return discovered

        finally:
            await qbt.disconnect()

    async def discover_from_prowlarr(self) -> List[Dict]:
        """Discover indexers from Prowlarr."""
        connection = await self._get_prowlarr_connection()
        if not connection:
            logger.warning("No Prowlarr connection configured")
            return []

        try:
            async with httpx.AsyncClient() as client:
                headers = {"X-Api-Key": connection.api_key}
                response = await client.get(
                    f"{connection.url.rstrip('/')}/api/v1/indexer",
                    headers=headers,
                    timeout=30,
                )
                response.raise_for_status()
                indexers = response.json()

                discovered = []
                for indexer in indexers:
                    if not indexer.get("enable", False):
                        continue

                    # Extract domains from indexer URLs
                    patterns = []
                    for field in indexer.get("fields", []):
                        if field.get("name") == "baseUrl":
                            url = field.get("value", "")
                            if url:
                                domain = self._extract_tracker_domain(url)
                                if domain:
                                    patterns.append(domain)

                    if patterns:
                        discovered.append({
                            "name": indexer.get("name", "Unknown"),
                            "patterns": patterns,
                            "torrent_count": 0,
                            "prowlarr_indexer_id": indexer.get("id"),
                            "prowlarr_indexer_name": indexer.get("name"),
                            "source": "prowlarr",
                        })

                return discovered

        except Exception as e:
            logger.error(f"Failed to fetch indexers from Prowlarr: {e}")
            return []

    async def merge_discoveries(self) -> List[Dict]:
        """Merge tracker discoveries from all sources."""
        qbt_trackers = await self.discover_from_qbittorrent()
        prowlarr_trackers = await self.discover_from_prowlarr()

        # Get existing trackers
        result = await self.db.execute(select(Tracker))
        existing_trackers = result.scalars().all()

        # Build a map of existing patterns
        existing_patterns: Dict[str, Tracker] = {}
        for tracker in existing_trackers:
            for pattern in (tracker.patterns or []):
                existing_patterns[pattern.lower()] = tracker

        # Merge and deduplicate
        merged: Dict[str, Dict] = {}

        for tracker in qbt_trackers:
            for pattern in tracker["patterns"]:
                key = pattern.lower()
                if key not in merged:
                    merged[key] = tracker.copy()
                    merged[key]["patterns"] = [pattern]
                else:
                    merged[key]["torrent_count"] = max(
                        merged[key].get("torrent_count", 0),
                        tracker.get("torrent_count", 0),
                    )

        for tracker in prowlarr_trackers:
            for pattern in tracker["patterns"]:
                key = pattern.lower()
                if key not in merged:
                    merged[key] = tracker.copy()
                    merged[key]["patterns"] = [pattern]
                else:
                    # Add Prowlarr info to existing
                    merged[key]["prowlarr_indexer_id"] = tracker.get("prowlarr_indexer_id")
                    merged[key]["prowlarr_indexer_name"] = tracker.get("prowlarr_indexer_name")
                    if not merged[key].get("name") or merged[key]["name"].startswith("tracker"):
                        merged[key]["name"] = tracker.get("name")

        # Mark already existing
        result = []
        for pattern, tracker_data in merged.items():
            existing = existing_patterns.get(pattern.lower())
            if existing:
                tracker_data["already_exists"] = True
                tracker_data["existing_tracker_id"] = existing.id
            else:
                tracker_data["already_exists"] = False
                tracker_data["existing_tracker_id"] = None

            result.append(tracker_data)

        # Sort by torrent count
        result.sort(key=lambda x: -(x.get("torrent_count", 0)))

        return result

    async def auto_match_prowlarr_indexer(self, tracker: Tracker) -> Optional[int]:
        """Try to automatically match a tracker with a Prowlarr indexer."""
        connection = await self._get_prowlarr_connection()
        if not connection:
            return None

        try:
            async with httpx.AsyncClient() as client:
                headers = {"X-Api-Key": connection.api_key}
                response = await client.get(
                    f"{connection.url.rstrip('/')}/api/v1/indexer",
                    headers=headers,
                    timeout=30,
                )
                response.raise_for_status()
                indexers = response.json()

                # Try to match by name or URL
                tracker_patterns = [p.lower() for p in (tracker.patterns or [])]
                tracker_name_lower = tracker.name.lower()

                for indexer in indexers:
                    indexer_name = indexer.get("name", "").lower()

                    # Check name match
                    if indexer_name and (
                        indexer_name in tracker_name_lower
                        or tracker_name_lower in indexer_name
                    ):
                        return indexer.get("id")

                    # Check URL match
                    for field in indexer.get("fields", []):
                        if field.get("name") == "baseUrl":
                            url = field.get("value", "")
                            if url:
                                domain = self._extract_tracker_domain(url).lower()
                                if domain in tracker_patterns:
                                    return indexer.get("id")

                return None

        except Exception as e:
            logger.error(f"Failed to match Prowlarr indexer: {e}")
            return None
