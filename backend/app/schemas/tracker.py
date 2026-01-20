"""Tracker schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class TrackerBase(BaseModel):
    """Base tracker schema."""

    name: str = Field(..., min_length=1, max_length=100)
    patterns: List[str] = Field(default_factory=list)
    prowlarr_indexer_id: Optional[int] = None
    default_rule_id: Optional[int] = None


class TrackerCreate(TrackerBase):
    """Schema for creating a tracker."""

    pass


class TrackerUpdate(BaseModel):
    """Schema for updating a tracker."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    patterns: Optional[List[str]] = None
    prowlarr_indexer_id: Optional[int] = None
    default_rule_id: Optional[int] = None


class TrackerResponse(BaseModel):
    """Schema for tracker response."""

    id: int
    name: str
    patterns: List[str]
    prowlarr_indexer_id: Optional[int] = None
    default_rule_id: Optional[int] = None
    stats_ratio: float
    stats_upload: int
    stats_download: int
    stats_torrent_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TrackerStatsResponse(BaseModel):
    """Schema for detailed tracker stats."""

    id: int
    name: str
    total_torrents: int
    active_torrents: int
    total_upload: int
    total_download: int
    average_ratio: float
    seed_time_average_hours: float
    top_categories: List[dict]


class DiscoveredTracker(BaseModel):
    """Schema for discovered tracker."""

    name: str
    patterns: List[str]
    torrent_count: int
    prowlarr_indexer_id: Optional[int] = None
    prowlarr_indexer_name: Optional[str] = None
    already_exists: bool = False
    existing_tracker_id: Optional[int] = None
