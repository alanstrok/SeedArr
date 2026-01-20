"""Torrent model (cache)."""
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Torrent(Base):
    """Model for cached torrent information.

    Zone values:
    - 1: Obligation zone (never delete - H&R protection)
    - 2: Preference zone (keep if possible)
    - 3: Eligible for deletion
    """

    __tablename__ = "torrents"

    hash: Mapped[str] = mapped_column(String(40), primary_key=True)  # Torrent hash
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    tracker_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("trackers.id", ondelete="SET NULL"), nullable=True
    )
    category: Mapped[str] = mapped_column(String(100), default="")
    tags: Mapped[list] = mapped_column(JSON, default=list)  # ["tag1", "tag2"]
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    ratio: Mapped[float] = mapped_column(Float, default=0.0)
    uploaded_bytes: Mapped[int] = mapped_column(Integer, default=0)
    downloaded_bytes: Mapped[int] = mapped_column(Integer, default=0)
    seed_time_seconds: Mapped[int] = mapped_column(Integer, default=0)
    added_on: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completion_on: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_activity: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    num_seeds: Mapped[int] = mapped_column(Integer, default=0)
    num_leeches: Mapped[int] = mapped_column(Integer, default=0)
    state: Mapped[str] = mapped_column(String(50), default="unknown")  # seeding, downloading, paused, etc.
    save_path: Mapped[str] = mapped_column(String(1000), default="")

    # Protection and zone status
    protected: Mapped[bool] = mapped_column(Boolean, default=False)  # Manual protection
    zone: Mapped[int] = mapped_column(Integer, default=1)  # 1=Obligation, 2=Preference, 3=Eligible
    zone_reason: Mapped[str] = mapped_column(String(500), default="")  # Explanation for current zone
    deletion_score: Mapped[float] = mapped_column(Float, default=0.0)  # Higher = delete first

    # Time until obligations are met (for alerts)
    hours_until_zone2: Mapped[float | None] = mapped_column(Float, nullable=True)  # Hours until Zone 1 -> Zone 2
    ratio_until_zone2: Mapped[float | None] = mapped_column(Float, nullable=True)  # Ratio needed for Zone 1 -> Zone 2

    last_scanned: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    tracker = relationship("Tracker", back_populates="torrents", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Torrent(hash='{self.hash}', name='{self.name[:30]}...', zone={self.zone})>"
