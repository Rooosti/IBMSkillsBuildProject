from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SteamTag(Base):
    __tablename__ = "steam_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    canonical_name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_doc_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_snapshot_version: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    aliases = relationship("SteamTagAlias", back_populates="tag", cascade="all, delete-orphan")
    query_maps = relationship("SteamQueryTagMap", back_populates="tag", cascade="all, delete-orphan")


class SteamTagAlias(Base):
    __tablename__ = "steam_tag_aliases"
    __table_args__ = (
        UniqueConstraint("normalized_alias", name="uq_steam_tag_aliases_normalized_alias"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("steam_tags.id", ondelete="CASCADE"), nullable=False, index=True)
    alias: Mapped[str] = mapped_column(String(128), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    alias_type: Mapped[str] = mapped_column(String(32), nullable=False, default="seed")

    tag = relationship("SteamTag", back_populates="aliases")


class SteamQueryTagMap(Base):
    __tablename__ = "steam_query_tag_map"
    __table_args__ = (
        UniqueConstraint("normalized_query_term", "tag_id", name="uq_steam_query_tag_map_term_tag"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query_term: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    normalized_query_term: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("steam_tags.id", ondelete="CASCADE"), nullable=False, index=True)
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    match_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    tag = relationship("SteamTag", back_populates="query_maps")
