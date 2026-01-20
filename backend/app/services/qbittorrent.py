"""qBittorrent API service."""
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from loguru import logger
import qbittorrentapi
from qbittorrentapi.exceptions import LoginFailed, APIConnectionError


@dataclass
class TorrentInfo:
    """Torrent information from qBittorrent."""

    hash: str
    name: str
    category: str
    tags: List[str]
    size: int
    ratio: float
    uploaded: int
    downloaded: int
    seeding_time: int
    added_on: datetime
    completion_on: Optional[datetime]
    last_activity: datetime
    num_seeds: int
    num_leechs: int
    state: str
    save_path: str
    tracker: str


@dataclass
class TrackerInfo:
    """Tracker information from qBittorrent."""

    url: str
    status: int
    tier: int
    num_peers: int
    num_seeds: int
    num_leeches: int
    msg: str


class QBittorrentService:
    """Service for interacting with qBittorrent API."""

    def __init__(self, url: str, username: str, password: str):
        """Initialize qBittorrent service."""
        self.url = url
        self.username = username
        self.password = password
        self._client: Optional[qbittorrentapi.Client] = None
        self._connected = False

    def _get_client(self) -> qbittorrentapi.Client:
        """Get or create qBittorrent client."""
        if self._client is None:
            self._client = qbittorrentapi.Client(
                host=self.url,
                username=self.username,
                password=self.password,
            )
        return self._client

    async def connect(self) -> bool:
        """Connect to qBittorrent."""
        try:
            client = self._get_client()
            # Run blocking auth in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, client.auth_log_in)
            self._connected = True
            logger.info(f"Connected to qBittorrent at {self.url}")
            return True
        except LoginFailed as e:
            logger.error(f"Failed to login to qBittorrent: {e}")
            self._connected = False
            return False
        except APIConnectionError as e:
            logger.error(f"Failed to connect to qBittorrent: {e}")
            self._connected = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to qBittorrent: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from qBittorrent."""
        if self._client:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._client.auth_log_out)
            except Exception:
                pass
            self._client = None
            self._connected = False

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection and return info."""
        try:
            connected = await self.connect()
            if not connected:
                return {"success": False, "message": "Failed to connect"}

            client = self._get_client()
            loop = asyncio.get_event_loop()
            version = await loop.run_in_executor(None, lambda: client.app.version)
            api_version = await loop.run_in_executor(None, lambda: client.app.web_api_version)

            return {
                "success": True,
                "message": "Connected successfully",
                "details": {
                    "version": version,
                    "api_version": api_version,
                },
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def get_torrents(self, category: Optional[str] = None, tag: Optional[str] = None) -> List[TorrentInfo]:
        """Get all torrents."""
        if not self._connected:
            await self.connect()

        client = self._get_client()
        loop = asyncio.get_event_loop()

        # Build filter
        filter_params = {}
        if category:
            filter_params["category"] = category
        if tag:
            filter_params["tag"] = tag

        try:
            torrents = await loop.run_in_executor(
                None, lambda: client.torrents_info(**filter_params)
            )

            result = []
            for t in torrents:
                # Get tracker for this torrent
                trackers = await loop.run_in_executor(
                    None, lambda h=t.hash: client.torrents_trackers(h)
                )
                tracker_url = ""
                for tracker in trackers:
                    if tracker.url and tracker.url.startswith("http"):
                        tracker_url = tracker.url
                        break

                result.append(
                    TorrentInfo(
                        hash=t.hash,
                        name=t.name,
                        category=t.category or "",
                        tags=t.tags.split(",") if t.tags else [],
                        size=t.size,
                        ratio=t.ratio,
                        uploaded=t.uploaded,
                        downloaded=t.downloaded,
                        seeding_time=t.seeding_time,
                        added_on=datetime.fromtimestamp(t.added_on),
                        completion_on=datetime.fromtimestamp(t.completion_on) if t.completion_on > 0 else None,
                        last_activity=datetime.fromtimestamp(t.last_activity) if t.last_activity > 0 else datetime.fromtimestamp(t.added_on),
                        num_seeds=t.num_complete,
                        num_leechs=t.num_incomplete,
                        state=t.state,
                        save_path=t.save_path,
                        tracker=tracker_url,
                    )
                )
            return result
        except Exception as e:
            logger.error(f"Failed to get torrents: {e}")
            return []

    async def get_torrent(self, torrent_hash: str) -> Optional[TorrentInfo]:
        """Get a single torrent by hash."""
        torrents = await self.get_torrents()
        for t in torrents:
            if t.hash.lower() == torrent_hash.lower():
                return t
        return None

    async def delete_torrent(self, torrent_hash: str, delete_files: bool = True) -> bool:
        """Delete a torrent."""
        if not self._connected:
            await self.connect()

        client = self._get_client()
        loop = asyncio.get_event_loop()

        try:
            await loop.run_in_executor(
                None,
                lambda: client.torrents_delete(
                    delete_files=delete_files, torrent_hashes=torrent_hash
                ),
            )
            logger.info(f"Deleted torrent {torrent_hash} (files={'yes' if delete_files else 'no'})")
            return True
        except Exception as e:
            logger.error(f"Failed to delete torrent {torrent_hash}: {e}")
            return False

    async def pause_torrent(self, torrent_hash: str) -> bool:
        """Pause a torrent."""
        if not self._connected:
            await self.connect()

        client = self._get_client()
        loop = asyncio.get_event_loop()

        try:
            await loop.run_in_executor(
                None, lambda: client.torrents_pause(torrent_hashes=torrent_hash)
            )
            logger.info(f"Paused torrent {torrent_hash}")
            return True
        except Exception as e:
            logger.error(f"Failed to pause torrent {torrent_hash}: {e}")
            return False

    async def resume_torrent(self, torrent_hash: str) -> bool:
        """Resume a torrent."""
        if not self._connected:
            await self.connect()

        client = self._get_client()
        loop = asyncio.get_event_loop()

        try:
            await loop.run_in_executor(
                None, lambda: client.torrents_resume(torrent_hashes=torrent_hash)
            )
            logger.info(f"Resumed torrent {torrent_hash}")
            return True
        except Exception as e:
            logger.error(f"Failed to resume torrent {torrent_hash}: {e}")
            return False

    async def add_tag(self, torrent_hash: str, tag: str) -> bool:
        """Add a tag to a torrent."""
        if not self._connected:
            await self.connect()

        client = self._get_client()
        loop = asyncio.get_event_loop()

        try:
            await loop.run_in_executor(
                None, lambda: client.torrents_add_tags(tags=tag, torrent_hashes=torrent_hash)
            )
            logger.info(f"Added tag '{tag}' to torrent {torrent_hash}")
            return True
        except Exception as e:
            logger.error(f"Failed to add tag to torrent {torrent_hash}: {e}")
            return False

    async def remove_tag(self, torrent_hash: str, tag: str) -> bool:
        """Remove a tag from a torrent."""
        if not self._connected:
            await self.connect()

        client = self._get_client()
        loop = asyncio.get_event_loop()

        try:
            await loop.run_in_executor(
                None,
                lambda: client.torrents_remove_tags(tags=tag, torrent_hashes=torrent_hash),
            )
            logger.info(f"Removed tag '{tag}' from torrent {torrent_hash}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove tag from torrent {torrent_hash}: {e}")
            return False

    async def get_trackers(self, torrent_hash: str) -> List[TrackerInfo]:
        """Get trackers for a torrent."""
        if not self._connected:
            await self.connect()

        client = self._get_client()
        loop = asyncio.get_event_loop()

        try:
            trackers = await loop.run_in_executor(
                None, lambda: client.torrents_trackers(torrent_hash)
            )
            return [
                TrackerInfo(
                    url=t.url,
                    status=t.status,
                    tier=t.tier,
                    num_peers=t.num_peers,
                    num_seeds=t.num_seeds,
                    num_leeches=t.num_leeches,
                    msg=t.msg,
                )
                for t in trackers
                if t.url.startswith("http")
            ]
        except Exception as e:
            logger.error(f"Failed to get trackers for {torrent_hash}: {e}")
            return []

    async def get_all_categories(self) -> List[str]:
        """Get all categories."""
        if not self._connected:
            await self.connect()

        client = self._get_client()
        loop = asyncio.get_event_loop()

        try:
            categories = await loop.run_in_executor(None, lambda: client.torrents_categories())
            return list(categories.keys())
        except Exception as e:
            logger.error(f"Failed to get categories: {e}")
            return []

    async def get_all_tags(self) -> List[str]:
        """Get all tags."""
        if not self._connected:
            await self.connect()

        client = self._get_client()
        loop = asyncio.get_event_loop()

        try:
            tags = await loop.run_in_executor(None, lambda: client.torrents_tags())
            return list(tags)
        except Exception as e:
            logger.error(f"Failed to get tags: {e}")
            return []
