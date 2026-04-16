from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    steam_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    recently_played_games = relationship(
        "UserRecentlyPlayedGame",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    device_profile = relationship("UserDeviceProfile", back_populates="user", uselist=False)
    preferences = relationship("UserPreference", back_populates="user", uselist=False)
    owned_games = relationship("UserOwnedGame", back_populates="user")
    recommendation_events = relationship("RecommendationEvent", back_populates="user")
