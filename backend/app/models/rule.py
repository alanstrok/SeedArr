"""Rule model for seeding rules."""
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Rule(Base):
    """Model for seeding rules."""

    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100)  # 1 = highest priority
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Targeting conditions (which torrents to match)
    conditions: Mapped[dict] = mapped_column(JSON, default=dict)
    # Example:
    # {
    #     "tracker_ids": [1, 2],           # OR, empty = all
    #     "categories": ["tv", "movies"],  # OR, empty = all
    #     "tags": ["cross-seed"],          # OR, empty = all
    #     "min_size_gb": 0,
    #     "max_size_gb": 100
    # }

    # Deletion criteria (when to delete)
    criteria: Mapped[dict] = mapped_column(JSON, default=dict)
    # Example:
    # {
    #     "min_seed_time_minutes": 10080,  # 7 days
    #     "min_ratio": 1.0,
    #     "max_seed_time_minutes": null,   # null = no max
    #     "operator": "AND"                # AND = all required, OR = one sufficient
    # }

    # Exceptions (do not delete if)
    exceptions: Mapped[dict] = mapped_column(JSON, default=dict)
    # Example:
    # {
    #     "keep_if_seeders_below": 3,
    #     "keep_if_last_activity_days": 3
    # }

    # Action to perform
    action: Mapped[str] = mapped_column(String(50), default="delete")  # delete, delete_torrent_only, pause, tag
    action_params: Mapped[dict] = mapped_column(JSON, default=dict)  # {"tag": "completed"} if action = "tag"

    # Notifications
    notify: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_connections: Mapped[list] = mapped_column(JSON, default=list)  # [1, 2] connection IDs

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Rule(id={self.id}, name='{self.name}', priority={self.priority})>"
