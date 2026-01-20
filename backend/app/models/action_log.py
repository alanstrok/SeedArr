"""ActionLog model for tracking actions history."""
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ActionLog(Base):
    """Model for action history logs."""

    __tablename__ = "action_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    torrent_hash: Mapped[str] = mapped_column(String(40), nullable=False)
    torrent_name: Mapped[str] = mapped_column(String(500), nullable=False)
    tracker_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("trackers.id", ondelete="SET NULL"), nullable=True
    )
    rule_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("rules.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # deleted, paused, tagged, protected
    reason: Mapped[str] = mapped_column(Text, nullable=False)  # Detailed explanation
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    tracker = relationship("Tracker", lazy="selectin")
    rule = relationship("Rule", lazy="selectin")

    def __repr__(self) -> str:
        return f"<ActionLog(id={self.id}, action='{self.action}', torrent='{self.torrent_name[:30]}...')>"
