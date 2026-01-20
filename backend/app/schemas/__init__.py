"""Pydantic schemas for API validation."""
from app.schemas.connection import (
    ConnectionCreate,
    ConnectionUpdate,
    ConnectionResponse,
    ConnectionType,
)
from app.schemas.tracker import (
    TrackerCreate,
    TrackerUpdate,
    TrackerResponse,
    TrackerStatsResponse,
    DiscoveredTracker,
)
from app.schemas.rule import (
    RuleCreate,
    RuleUpdate,
    RuleResponse,
    RuleConditions,
    RuleCriteria,
    RuleExceptions,
    RuleTestResult,
    RuleReorder,
)
from app.schemas.torrent import (
    TorrentResponse,
    TorrentListResponse,
    TorrentHistoryResponse,
)
from app.schemas.system import (
    StatsResponse,
    ScanResult,
    LogResponse,
    SettingsResponse,
    SettingsUpdate,
    HealthResponse,
)

__all__ = [
    # Connection
    "ConnectionCreate",
    "ConnectionUpdate",
    "ConnectionResponse",
    "ConnectionType",
    # Tracker
    "TrackerCreate",
    "TrackerUpdate",
    "TrackerResponse",
    "TrackerStatsResponse",
    "DiscoveredTracker",
    # Rule
    "RuleCreate",
    "RuleUpdate",
    "RuleResponse",
    "RuleConditions",
    "RuleCriteria",
    "RuleExceptions",
    "RuleTestResult",
    "RuleReorder",
    # Torrent
    "TorrentResponse",
    "TorrentListResponse",
    "TorrentHistoryResponse",
    # System
    "StatsResponse",
    "ScanResult",
    "LogResponse",
    "SettingsResponse",
    "SettingsUpdate",
    "HealthResponse",
]
