"""Tracker schemas with zone-based seeding rules."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class TrackerBase(BaseModel):
    """Base tracker schema."""

    name: str = Field(..., min_length=1, max_length=100)
    patterns: List[str] = Field(default_factory=list)
    prowlarr_indexer_id: Optional[int] = None
    prowlarr_indexer_name: Optional[str] = None
    enabled: bool = True

    # Zone 1: Obligations (Never delete before)
    min_seed_time_hours: int = Field(default=168, ge=0, description="Minimum seed time in hours (default 7 days)")
    min_ratio: float = Field(default=1.0, ge=0, description="Minimum ratio to reach")
    min_operator: str = Field(default="OR", pattern="^(AND|OR)$", description="AND = both required, OR = either sufficient")

    # Zone 2: Preferences (Keep longer if possible)
    keep_if_seeders_below: Optional[int] = Field(default=5, ge=0, description="Keep if seeders below this threshold")
    keep_if_activity_within_hours: Optional[int] = Field(default=72, ge=0, description="Keep if upload activity within X hours")
    permaseed: bool = Field(default=False, description="Never delete torrents from this tracker")

    # Zone 3: Deletion settings
    deletion_priority: int = Field(default=50, ge=1, le=100, description="Priority 1-100, higher = delete first")
    max_seed_time_hours: Optional[int] = Field(default=None, ge=0, description="Force delete after X hours (optional)")


class TrackerCreate(TrackerBase):
    """Schema for creating a tracker."""

    pass


class TrackerUpdate(BaseModel):
    """Schema for updating a tracker."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    patterns: Optional[List[str]] = None
    prowlarr_indexer_id: Optional[int] = None
    prowlarr_indexer_name: Optional[str] = None
    enabled: Optional[bool] = None

    # Zone 1: Obligations
    min_seed_time_hours: Optional[int] = Field(None, ge=0)
    min_ratio: Optional[float] = Field(None, ge=0)
    min_operator: Optional[str] = Field(None, pattern="^(AND|OR)$")

    # Zone 2: Preferences
    keep_if_seeders_below: Optional[int] = Field(None, ge=0)
    keep_if_activity_within_hours: Optional[int] = Field(None, ge=0)
    permaseed: Optional[bool] = None

    # Zone 3: Deletion settings
    deletion_priority: Optional[int] = Field(None, ge=1, le=100)
    max_seed_time_hours: Optional[int] = Field(None, ge=0)


class TrackerResponse(BaseModel):
    """Schema for tracker response with zone statistics."""

    id: int
    name: str
    patterns: List[str]
    prowlarr_indexer_id: Optional[int] = None
    prowlarr_indexer_name: Optional[str] = None
    enabled: bool

    # Zone 1: Obligations
    min_seed_time_hours: int
    min_ratio: float
    min_operator: str

    # Zone 2: Preferences
    keep_if_seeders_below: Optional[int]
    keep_if_activity_within_hours: Optional[int]
    permaseed: bool

    # Zone 3: Deletion settings
    deletion_priority: int
    max_seed_time_hours: Optional[int]

    # Statistics
    stats_ratio: float
    stats_upload: int
    stats_download: int
    stats_torrent_count: int
    stats_zone1_count: int
    stats_zone2_count: int
    stats_zone3_count: int

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

    # Zone distribution
    zone1_count: int = 0
    zone2_count: int = 0
    zone3_count: int = 0


class DiscoveredTracker(BaseModel):
    """Schema for discovered tracker."""

    name: str
    patterns: List[str]
    torrent_count: int
    prowlarr_indexer_id: Optional[int] = None
    prowlarr_indexer_name: Optional[str] = None
    already_exists: bool = False
    existing_tracker_id: Optional[int] = None


class TrackerZoneSummary(BaseModel):
    """Summary of zone distribution across all trackers."""

    total_zone1: int
    total_zone2: int
    total_zone3: int
    trackers: List[dict]  # [{name, zone1, zone2, zone3}]
