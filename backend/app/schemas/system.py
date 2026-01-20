"""System schemas."""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel


class StatsResponse(BaseModel):
    """Schema for global stats."""

    total_torrents: int
    active_torrents: int
    paused_torrents: int
    total_upload_bytes: int
    total_download_bytes: int
    average_ratio: float
    total_size_bytes: int
    actions_today: int
    actions_this_week: int
    protected_count: int
    trackers_count: int
    rules_count: int
    last_scan: Optional[datetime] = None


class StatsHistoryResponse(BaseModel):
    """Schema for stats history (for graphs)."""

    dates: List[str]
    upload: List[int]
    download: List[int]
    ratio: List[float]
    torrent_count: List[int]


class ScanResultItem(BaseModel):
    """Schema for a single scan result item."""

    torrent_hash: str
    torrent_name: str
    tracker_name: Optional[str] = None
    rule_name: Optional[str] = None
    action: str
    reason: str


class ScanResult(BaseModel):
    """Schema for scan result."""

    dry_run: bool
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    torrents_scanned: int
    actions_taken: int
    deleted: int
    paused: int
    tagged: int
    protected_skipped: int
    items: List[ScanResultItem]


class LogResponse(BaseModel):
    """Schema for action log response."""

    id: int
    torrent_hash: str
    torrent_name: str
    tracker_id: Optional[int] = None
    tracker_name: Optional[str] = None
    rule_id: Optional[int] = None
    rule_name: Optional[str] = None
    action: str
    reason: str
    dry_run: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LogListResponse(BaseModel):
    """Schema for paginated log list response."""

    items: List[LogResponse]
    total: int
    page: int
    per_page: int
    pages: int


class SettingsResponse(BaseModel):
    """Schema for settings response."""

    scan_interval_minutes: int
    dry_run_mode: bool
    disk_space_threshold_percent: int
    disk_space_action: str
    protected_categories: List[str]
    protected_tags: List[str]
    theme: str
    notifications_enabled: bool
    log_retention_days: int


class SettingsUpdate(BaseModel):
    """Schema for updating settings."""

    scan_interval_minutes: Optional[int] = None
    dry_run_mode: Optional[bool] = None
    disk_space_threshold_percent: Optional[int] = None
    disk_space_action: Optional[str] = None
    protected_categories: Optional[List[str]] = None
    protected_tags: Optional[List[str]] = None
    theme: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    log_retention_days: Optional[int] = None


class HealthResponse(BaseModel):
    """Schema for health check response."""

    status: str
    version: str
    database: str
    qbittorrent: Optional[str] = None
    scheduler: str
    uptime_seconds: float


class BackupData(BaseModel):
    """Schema for backup/restore data."""

    version: str
    exported_at: datetime
    connections: List[dict]
    trackers: List[dict]
    rules: List[dict]
    settings: dict
