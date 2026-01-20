"""Connection schemas."""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


class ConnectionType(str, Enum):
    """Connection types."""

    QBITTORRENT = "qbittorrent"
    SONARR = "sonarr"
    RADARR = "radarr"
    PROWLARR = "prowlarr"
    DISCORD = "discord"
    TELEGRAM = "telegram"


class ConnectionBase(BaseModel):
    """Base connection schema."""

    type: ConnectionType
    name: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., min_length=1, max_length=500)
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    enabled: bool = True


class ConnectionCreate(ConnectionBase):
    """Schema for creating a connection."""

    pass


class ConnectionUpdate(BaseModel):
    """Schema for updating a connection."""

    type: Optional[ConnectionType] = None
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    url: Optional[str] = Field(None, min_length=1, max_length=500)
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    enabled: Optional[bool] = None


class ConnectionResponse(BaseModel):
    """Schema for connection response."""

    id: int
    type: ConnectionType
    name: str
    url: str
    api_key: Optional[str] = None
    username: Optional[str] = None
    # password is never returned
    enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConnectionTestResult(BaseModel):
    """Schema for connection test result."""

    success: bool
    message: str
    details: Optional[dict] = None
