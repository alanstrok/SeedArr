"""Tracker model with integrated seeding rules."""
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Tracker(Base):
    """Model for torrent trackers with integrated seeding rules.

    Each tracker has 3 zones:
    - Zone 1 (Obligations): Never delete before these conditions are met
    - Zone 2 (Preferences): Keep if possible even after Zone 1 is cleared
    - Zone 3 (Eligible): Can be deleted when disk space is needed
    """

    __tablename__ = "trackers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    patterns: Mapped[list] = mapped_column(JSON, default=list)  # URL patterns ["ipt.biz", "iptorrents.com"]
    prowlarr_indexer_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prowlarr_indexer_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # ═══════════════════════════════════════════════════════════════
    # ZONE 1: OBLIGATIONS (Never delete before - avoid Hit & Run)
    # ═══════════════════════════════════════════════════════════════
    min_seed_time_hours: Mapped[int] = mapped_column(Integer, default=168)  # 7 days
    min_ratio: Mapped[float] = mapped_column(Float, default=1.0)
    min_operator: Mapped[str] = mapped_column(String(3), default="OR")  # "AND" or "OR"

    # ═══════════════════════════════════════════════════════════════
    # ZONE 2: PREFERENCES (Keep longer if possible)
    # ═══════════════════════════════════════════════════════════════
    keep_if_seeders_below: Mapped[int | None] = mapped_column(Integer, default=5)
    keep_if_activity_within_hours: Mapped[int | None] = mapped_column(Integer, default=72)  # 3 days
    permaseed: Mapped[bool] = mapped_column(Boolean, default=False)

    # ═══════════════════════════════════════════════════════════════
    # ZONE 3: DELETION SETTINGS
    # ═══════════════════════════════════════════════════════════════
    deletion_priority: Mapped[int] = mapped_column(Integer, default=50)  # 1-100, higher = delete first
    max_seed_time_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Force delete after X

    # ═══════════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════════
    stats_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    stats_upload: Mapped[int] = mapped_column(Integer, default=0)  # Bytes
    stats_download: Mapped[int] = mapped_column(Integer, default=0)  # Bytes
    stats_torrent_count: Mapped[int] = mapped_column(Integer, default=0)
    stats_zone1_count: Mapped[int] = mapped_column(Integer, default=0)  # Obligation zone
    stats_zone2_count: Mapped[int] = mapped_column(Integer, default=0)  # Preference zone
    stats_zone3_count: Mapped[int] = mapped_column(Integer, default=0)  # Eligible for deletion

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    torrents = relationship("Torrent", back_populates="tracker", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Tracker(id={self.id}, name='{self.name}')>"
