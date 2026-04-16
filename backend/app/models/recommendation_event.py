from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RecommendationEvent(Base):
    __tablename__ = "recommendation_events"

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
    query_text: Mapped[str] = mapped_column(Text)
    parsed_query_json: Mapped[dict | None] = mapped_column(JSON)
    candidate_ids_json: Mapped[list[str] | None] = mapped_column(JSON)
    returned_ids_json: Mapped[list[str] | None] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    user = relationship("User", back_populates="recommendation_events")
