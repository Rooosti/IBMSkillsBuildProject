from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserDeviceProfile(Base):
    __tablename__ = "user_device_profiles"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    device_type: Mapped[str | None] = mapped_column(String(32))
    performance_tier: Mapped[str | None] = mapped_column(String(16))
    controller_required: Mapped[bool] = mapped_column(Boolean, default=False)
    storage_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    bandwidth_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    preferred_session_length: Mapped[str | None] = mapped_column(String(16))
    accessibility_notes: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship("User", back_populates="device_profile")
