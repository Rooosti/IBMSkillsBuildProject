from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    steam_app_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    short_description: Mapped[str | None] = mapped_column(Text)
    release_date: Mapped[datetime | None] = mapped_column(Date)
    developer: Mapped[str | None] = mapped_column(String(500))
    publisher: Mapped[str | None] = mapped_column(String(500))
    price_current: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    price_currency: Mapped[str | None] = mapped_column(String(8))
    header_image_url: Mapped[str | None] = mapped_column(Text)
    store_url: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_free: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    capsule_image_url: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(Text)
    supported_languages_json: Mapped[list[str] | None] = mapped_column(JSON)
    steam_last_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    features: Mapped["GameFeature"] = relationship(
        back_populates="game",
        uselist=False,
        cascade="all, delete-orphan",
    )
    requirements: Mapped["GameRequirement"] = relationship(
        back_populates="game",
        uselist=False,
        cascade="all, delete-orphan",
    )
    semantic_doc: Mapped["GameSemanticDoc"] = relationship(
        back_populates="game",
        uselist=False,
        cascade="all, delete-orphan",
    )


class GameFeature(Base):
    __tablename__ = "game_features"

    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), primary_key=True)
    genres_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    tags_json: Mapped[list[str] | None] = mapped_column(JSON)
    categories_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    has_singleplayer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_multiplayer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_online_coop: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_local_coop: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_pvp: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    controller_support: Mapped[str | None] = mapped_column(String(32))
    steam_deck_status: Mapped[str | None] = mapped_column(String(32))
    platforms_json: Mapped[dict[str, bool] | None] = mapped_column(JSON)
    content_descriptors_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    game: Mapped[Game] = relationship(back_populates="features")


class GameRequirement(Base):
    __tablename__ = "game_requirements"

    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), primary_key=True)
    min_os: Mapped[str | None] = mapped_column(String(255))
    min_cpu_text: Mapped[str | None] = mapped_column(Text)
    min_gpu_text: Mapped[str | None] = mapped_column(Text)
    min_ram_gb: Mapped[int | None] = mapped_column(Integer)
    min_storage_gb: Mapped[int | None] = mapped_column(Integer)
    recommended_os: Mapped[str | None] = mapped_column(String(255))
    recommended_cpu_text: Mapped[str | None] = mapped_column(Text)
    recommended_gpu_text: Mapped[str | None] = mapped_column(Text)
    recommended_ram_gb: Mapped[int | None] = mapped_column(Integer)
    recommended_storage_gb: Mapped[int | None] = mapped_column(Integer)
    performance_tier_estimate: Mapped[str | None] = mapped_column(String(32), index=True)
    raw_pc_requirements_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    game: Mapped[Game] = relationship(back_populates="requirements")


class GameSemanticDoc(Base):
    __tablename__ = "game_semantic_docs"
    __table_args__ = (UniqueConstraint("game_id", "version", name="uq_game_semantic_doc_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), index=True, nullable=False)
    semantic_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Vector | None] = mapped_column(Vector(384)) # granite-embedding-30m-english
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    game: Mapped[Game] = relationship(back_populates="semantic_doc")
