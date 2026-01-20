"""Torrent schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class TorrentResponse(BaseModel):
    """Schema for torrent response."""

    hash: str
    name: str
    tracker_id: Optional[int] = None
    tracker_name: Optional[str] = None
    category: str
    tags: List[str]
    size_bytes: int
    ratio: float
    uploaded_bytes: int
    downloaded_bytes: int
    seed_time_seconds: int
    added_on: datetime
    completion_on: Optional[datetime] = None
    last_activity: datetime
    num_seeds: int
    num_leeches: int
    state: str
    save_path: str
    protected: bool
    matched_rule_id: Optional[int] = None
    matched_rule_name: Optional[str] = None
    last_scanned: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TorrentListResponse(BaseModel):
    """Schema for paginated torrent list response."""

    items: List[TorrentResponse]
    total: int
    page: int
    per_page: int
    pages: int


class TorrentHistoryResponse(BaseModel):
    """Schema for torrent action history."""

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


class TorrentProtectRequest(BaseModel):
    """Schema for protect/unprotect request."""

    protected: bool
