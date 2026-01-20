"""Tracker model."""
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Tracker(Base):
    """Model for torrent trackers."""

    __tablename__ = "trackers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # Display name (e.g., "IPT", "TorrentLeech")
    patterns: Mapped[list] = mapped_column(JSON, default=list)  # URL patterns ["ipt.biz", "iptorrents.com"]
    prowlarr_indexer_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Link to Prowlarr
    default_rule_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("rules.id", ondelete="SET NULL"), nullable=True
    )

    # Stats
    stats_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    stats_upload: Mapped[int] = mapped_column(Integer, default=0)  # Bytes
    stats_download: Mapped[int] = mapped_column(Integer, default=0)  # Bytes
    stats_torrent_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    default_rule = relationship("Rule", foreign_keys=[default_rule_id], lazy="selectin")
    torrents = relationship("Torrent", back_populates="tracker", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Tracker(id={self.id}, name='{self.name}')>"
