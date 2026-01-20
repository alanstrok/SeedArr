"""Rule schemas."""
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class RuleConditions(BaseModel):
    """Schema for rule targeting conditions."""

    tracker_ids: List[int] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    min_size_gb: Optional[float] = None
    max_size_gb: Optional[float] = None


class RuleCriteria(BaseModel):
    """Schema for rule deletion criteria."""

    min_seed_time_minutes: Optional[int] = None
    min_ratio: Optional[float] = None
    max_seed_time_minutes: Optional[int] = None
    operator: Literal["AND", "OR"] = "AND"


class RuleExceptions(BaseModel):
    """Schema for rule exceptions."""

    keep_if_seeders_below: Optional[int] = None
    keep_if_last_activity_days: Optional[int] = None


class RuleBase(BaseModel):
    """Base rule schema."""

    name: str = Field(..., min_length=1, max_length=100)
    priority: int = Field(default=100, ge=1)
    enabled: bool = True
    conditions: RuleConditions = Field(default_factory=RuleConditions)
    criteria: RuleCriteria = Field(default_factory=RuleCriteria)
    exceptions: RuleExceptions = Field(default_factory=RuleExceptions)
    action: Literal["delete", "delete_torrent_only", "pause", "tag"] = "delete"
    action_params: dict = Field(default_factory=dict)
    notify: bool = False
    notify_connections: List[int] = Field(default_factory=list)


class RuleCreate(RuleBase):
    """Schema for creating a rule."""

    pass


class RuleUpdate(BaseModel):
    """Schema for updating a rule."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    priority: Optional[int] = Field(None, ge=1)
    enabled: Optional[bool] = None
    conditions: Optional[RuleConditions] = None
    criteria: Optional[RuleCriteria] = None
    exceptions: Optional[RuleExceptions] = None
    action: Optional[Literal["delete", "delete_torrent_only", "pause", "tag"]] = None
    action_params: Optional[dict] = None
    notify: Optional[bool] = None
    notify_connections: Optional[List[int]] = None


class RuleResponse(BaseModel):
    """Schema for rule response."""

    id: int
    name: str
    priority: int
    enabled: bool
    conditions: dict
    criteria: dict
    exceptions: dict
    action: str
    action_params: dict
    notify: bool
    notify_connections: List[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RuleTestResult(BaseModel):
    """Schema for rule test result."""

    rule_id: int
    rule_name: str
    matched_torrents: List[dict]
    total_matched: int
    would_be_deleted: int
    would_be_paused: int
    would_be_tagged: int
    protected_count: int


class RuleReorder(BaseModel):
    """Schema for reordering rules."""

    rule_ids: List[int] = Field(..., min_items=1)
