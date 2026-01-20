"""Settings model for application configuration."""
from datetime import datetime
from sqlalchemy import String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


# Default settings
DEFAULT_SETTINGS = {
    "scan_interval_minutes": 15,
    "dry_run_mode": False,
    "disk_space_threshold_percent": 10,
    "disk_space_action": "pause_lowest_priority",
    "protected_categories": [],
    "protected_tags": ["permaseed", "important"],
    "theme": "auto",
    "notifications_enabled": True,
    "log_retention_days": 30,
}


class Settings(Base):
    """Model for application settings."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict | list | str | int | float | bool] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Settings(key='{self.key}')>"
