from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserOwnedGame(Base):
    __tablename__ = "user_owned_games"
    __table_args__ = (
        UniqueConstraint("user_id", "steam_app_id", name="uq_user_owned_games_user_app"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    game_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    steam_app_id: Mapped[int] = mapped_column(Integer, index=True)
    game_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owned: Mapped[bool] = mapped_column(Boolean, default=True)
    playtime_minutes: Mapped[int] = mapped_column(Integer, default=0)
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    user = relationship("User", back_populates="owned_games")
