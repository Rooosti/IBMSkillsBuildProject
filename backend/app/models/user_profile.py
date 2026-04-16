from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        primary_key=True,
    )

    favorite_genres_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    favorite_tags_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    disliked_tags_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    complexity_preference: Mapped[str | None] = mapped_column(String(32), nullable=True)
    novelty_preference: Mapped[str | None] = mapped_column(String(32), nullable=True)
    solo_vs_coop_preference: Mapped[str | None] = mapped_column(String(32), nullable=True)
    budget_preference: Mapped[str | None] = mapped_column(String(32), nullable=True)

    user = relationship("User", back_populates="preferences")


class UserRecentlyPlayedGame(Base):
    __tablename__ = "user_recently_played_games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    steam_app_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    game_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    playtime_2weeks_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    playtime_forever_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="recently_played_games")
