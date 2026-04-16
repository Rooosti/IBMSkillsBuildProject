from __future__ import annotations

import itertools
import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.game_catalog import Game, GameFeature, GameRequirement, GameSemanticDoc
from app.services.steam_client import SteamClient, SteamStoreAppRecord

_TAG_RE = re.compile(r"<[^>]+>")
_GB_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(gb|gib)", re.IGNORECASE)


@dataclass(slots=True)
class IngestionConfig:
    language: str = "english"
    country: str = "US"
    appdetails_batch_size: int = 50
    commit_every: int = 100
    semantic_doc_version: str = "v1"
    if_modified_since: int | None = None
    max_apps: int | None = None


@dataclass(slots=True)
class IngestionResult:
    scanned: int = 0
    detailed: int = 0
    inserted_or_updated: int = 0
    skipped_non_games: int = 0
    skipped_missing_details: int = 0


def ingest_catalog(db: Session, client: SteamClient, config: IngestionConfig) -> IngestionResult:
    result = IngestionResult()
    app_records = client.iter_store_app_list(
        if_modified_since=config.if_modified_since,
        have_description_language=config.language,
        include_games=True,
        include_dlc=False,
        include_software=False,
        include_videos=False,
        include_hardware=False,
    )

    if config.max_apps is not None:
        app_records = itertools.islice(app_records, config.max_apps)

    pending_ids: list[int] = []
    source_index: dict[int, SteamStoreAppRecord] = {}

    for app_record in app_records:
        result.scanned += 1
        pending_ids.append(app_record.appid)
        source_index[app_record.appid] = app_record

        if len(pending_ids) >= config.appdetails_batch_size:
            _flush_app_batch(db, client, config, result, pending_ids, source_index)
            pending_ids.clear()
            source_index.clear()
            if result.inserted_or_updated and result.inserted_or_updated % config.commit_every == 0:
                db.commit()

    if pending_ids:
        _flush_app_batch(db, client, config, result, pending_ids, source_index)

    db.commit()
    return result


def _flush_app_batch(
    db: Session,
    client: SteamClient,
    config: IngestionConfig,
    result: IngestionResult,
    app_ids: list[int],
    source_index: dict[int, SteamStoreAppRecord],
) -> None:
    details_by_app_id = client.get_app_details(
        app_ids,
        language=config.language,
        country=config.country,
    )
    result.detailed += len(details_by_app_id)

    for app_id in app_ids:
        details = details_by_app_id.get(app_id)
        if not details:
            result.skipped_missing_details += 1
            continue

        if details.get("type") != "game":
            result.skipped_non_games += 1
            continue

        upsert_game_from_store_data(
            db=db,
            app_id=app_id,
            source_record=source_index.get(app_id),
            details=details,
            semantic_doc_version=config.semantic_doc_version,
        )
        result.inserted_or_updated += 1


def upsert_game_from_store_data(
    *,
    db: Session,
    app_id: int,
    source_record: SteamStoreAppRecord | None,
    details: dict[str, Any],
    semantic_doc_version: str,
) -> Game:
    game = db.scalar(select(Game).where(Game.steam_app_id == app_id))
    if game is None:
        game = Game(steam_app_id=app_id, title=details.get("name") or f"Steam App {app_id}")
        db.add(game)
        db.flush()

    now = datetime.now(timezone.utc)

    game.title = details.get("name") or game.title
    game.short_description = details.get("short_description")
    game.release_date = _parse_release_date(details.get("release_date"))
    game.developer = ", ".join(details.get("developers") or []) or None
    game.publisher = ", ".join(details.get("publishers") or []) or None
    game.price_current, game.price_currency = _parse_price(details)
    game.header_image_url = details.get("header_image")
    game.capsule_image_url = details.get("capsule_image")
    game.website = details.get("website")
    game.store_url = f"https://store.steampowered.com/app/{app_id}/"
    game.is_active = True
    game.is_free = bool(details.get("is_free", False))
    game.supported_languages_json = _normalize_languages(details.get("supported_languages"))
    game.last_ingested_at = now
    if source_record and source_record.last_modified:
        game.steam_last_modified_at = datetime.fromtimestamp(source_record.last_modified, tz=timezone.utc)

    feature = game.features or GameFeature(game_id=game.id)
    feature.genres_json = [g.get("description") for g in details.get("genres", []) if g.get("description")]
    feature.tags_json = _normalize_store_tags(details)
    feature.categories_json = [c.get("description") for c in details.get("categories", []) if c.get("description")]
    feature.has_singleplayer = _has_category(details, "Single-player")
    feature.has_multiplayer = _has_any_category(details, ["Multi-player", "Online PvP", "LAN PvP", "Shared/Split Screen PvP"])
    feature.has_online_coop = _has_any_category(details, ["Online Co-op", "Online Co-op PvP", "Remote Play Together"])
    feature.has_local_coop = _has_any_category(details, ["Shared/Split Screen Co-op", "LAN Co-op", "Local Co-op", "Remote Play Together"])
    feature.has_pvp = _has_any_category(details, ["PvP", "Online PvP", "LAN PvP", "Shared/Split Screen PvP"])
    feature.controller_support = _normalize_controller_support(details)
    feature.steam_deck_status = _normalize_steam_deck_status(details)
    feature.platforms_json = details.get("platforms") or {}
    feature.content_descriptors_json = details.get("content_descriptors") or {}
    game.features = feature

    requirement = game.requirements or GameRequirement(game_id=game.id)
    pc_requirements = details.get("pc_requirements") or {}
    minimum = _strip_html(pc_requirements.get("minimum"))
    recommended = _strip_html(pc_requirements.get("recommended"))
    requirement.min_os = _extract_requirement_value(minimum, ["OS:"])
    requirement.min_cpu_text = _extract_requirement_value(minimum, ["Processor:", "CPU:"])
    requirement.min_gpu_text = _extract_requirement_value(minimum, ["Graphics:", "GPU:", "Video Card:"])
    requirement.min_ram_gb = _extract_gb(minimum, ["Memory:", "RAM:"])
    requirement.min_storage_gb = _extract_gb(minimum, ["Storage:"])
    requirement.recommended_os = _extract_requirement_value(recommended, ["OS:"])
    requirement.recommended_cpu_text = _extract_requirement_value(recommended, ["Processor:", "CPU:"])
    requirement.recommended_gpu_text = _extract_requirement_value(recommended, ["Graphics:", "GPU:", "Video Card:"])
    requirement.recommended_ram_gb = _extract_gb(recommended, ["Memory:", "RAM:"])
    requirement.recommended_storage_gb = _extract_gb(recommended, ["Storage:"])
    requirement.performance_tier_estimate = _estimate_performance_tier(
        requirement.recommended_ram_gb or requirement.min_ram_gb,
        requirement.recommended_gpu_text or requirement.min_gpu_text,
    )
    requirement.raw_pc_requirements_json = pc_requirements
    game.requirements = requirement

    semantic_doc = game.semantic_doc or GameSemanticDoc(game_id=game.id, version=semantic_doc_version)
    semantic_doc.version = semantic_doc_version
    semantic_doc.semantic_text = build_semantic_text(game, feature, requirement)
    semantic_doc.updated_at = now
    game.semantic_doc = semantic_doc

    db.add(game)
    return game


def build_semantic_text(game: Game, feature: GameFeature, requirement: GameRequirement) -> str:
    genres = ", ".join(_json_label_values(feature.genres_json)) or "Unknown genre"
    tags = ", ".join(feature.tags_json or [])
    categories = ", ".join(_json_label_values(feature.categories_json))
    deck = feature.steam_deck_status or "unknown Steam Deck status"
    controller = feature.controller_support or "unknown controller support"
    session_hint = _session_length_hint(game, requirement)
    coop_hint = _coop_hint(feature)
    complexity_hint = _complexity_hint(requirement)

    parts = [
        f"{game.title}.",
        game.short_description or "",
        f"Genres: {genres}.",
        f"Tags: {tags}." if tags else "",
        f"Play modes: {categories}." if categories else "",
        f"Co-op summary: {coop_hint}.",
        f"Controller support: {controller}.",
        f"Steam Deck: {deck}.",
        f"Complexity/performance: {complexity_hint}.",
        f"Session shape: {session_hint}.",
    ]
    return " ".join(part.strip() for part in parts if part and part.strip())


def _parse_price(details: dict[str, Any]) -> tuple[Decimal | None, str | None]:
    price = details.get("price_overview") or {}
    final_cents = price.get("final")
    currency = price.get("currency")
    if final_cents is None:
        return None, currency
    return Decimal(final_cents) / Decimal(100), currency


def _parse_release_date(raw: Any) -> date | None:
    if not isinstance(raw, dict):
        return None
    raw_date = raw.get("date")
    if not raw_date or raw.get("coming_soon"):
        return None

    formats = ["%b %d, %Y", "%d %b, %Y", "%b %Y", "%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(raw_date, fmt).date()
        except ValueError:
            continue
    return None


def _normalize_languages(value: Any) -> list[str] | None:
    if not value:
        return None
    cleaned = _strip_html(str(value)).replace("*", "")
    return [part.strip() for part in cleaned.split(",") if part.strip()]


def _normalize_store_tags(details: dict[str, Any]) -> list[str] | None:
    # 1) Try real user tags first (these contain things like 'Cozy', 'Relaxing')
    # Note: store appdetails sometimes provides this under 'tags' (as a dict of name: 1)
    tags_data = details.get("tags")
    if isinstance(tags_data, dict):
        return sorted(tags_data.keys())
    if isinstance(tags_data, list):
        # Some API versions return list of {id, description}
        return sorted([t.get("description") for t in tags_data if t.get("description")])

    # 2) Fallback to categories if tags are missing
    raw = details.get("categories") or []
    derived = []
    for item in raw:
        desc = (item or {}).get("description")
        if desc in {"Steam Achievements", "Steam Cloud", "Family Sharing"}:
            continue
        if desc:
            derived.append(desc)
    return sorted(set(derived)) or None


def _normalize_controller_support(details: dict[str, Any]) -> str | None:
    raw = details.get("controller_support")
    if raw:
        return str(raw).lower().strip()
    if _has_category(details, "Full controller support"):
        return "full"
    if _has_category(details, "Partial Controller Support"):
        return "partial"
    return None


def _normalize_steam_deck_status(details: dict[str, Any]) -> str | None:
    status = details.get("steam_deck_compatibility")
    if isinstance(status, dict):
        category = status.get("category")
        mapping = {
            1: "unsupported",
            2: "playable",
            3: "verified",
            0: "unknown",
        }
        if isinstance(category, int):
            return mapping.get(category, "unknown")
        if isinstance(category, str):
            return category.lower()
    return None


def _has_category(details: dict[str, Any], description: str) -> bool:
    return description in _category_descriptions(details)


def _has_any_category(details: dict[str, Any], descriptions: list[str]) -> bool:
    available = _category_descriptions(details)
    return any(item in available for item in descriptions)


def _category_descriptions(details: dict[str, Any]) -> set[str]:
    return {
        str(item.get("description"))
        for item in (details.get("categories") or [])
        if item and item.get("description")
    }


def _json_label_values(items: Any) -> list[str]:
    labels: list[str] = []
    for item in items or []:
        if isinstance(item, dict) and item.get("description"):
            labels.append(str(item["description"]))
        elif isinstance(item, str):
            labels.append(item)
    return labels


def _strip_html(value: Any) -> str:
    if not value:
        return ""
    text = _TAG_RE.sub(" ", str(value))
    return re.sub(r"\s+", " ", text).strip()


def _extract_requirement_value(text: str, labels: list[str]) -> str | None:
    if not text:
        return None
    for label in labels:
        idx = text.lower().find(label.lower())
        if idx == -1:
            continue
        segment = text[idx + len(label):]
        cut_points = [segment.find(next_label) for next_label in ["OS:", "Processor:", "CPU:", "Memory:", "RAM:", "Graphics:", "GPU:", "Video Card:", "Storage:"] if segment.find(next_label) > 0]
        if cut_points:
            segment = segment[: min(cut_points)]
        cleaned = segment.strip(" :-")
        return cleaned or None
    return None


def _extract_gb(text: str, labels: list[str]) -> int | None:
    value = _extract_requirement_value(text, labels)
    if not value:
        return None
    match = _GB_RE.search(value)
    if not match:
        return None
    number = float(match.group(1))
    return int(math.ceil(number))


def _estimate_performance_tier(ram_gb: int | None, gpu_text: str | None) -> str | None:
    gpu_text = (gpu_text or "").lower()
    if ram_gb is None and not gpu_text:
        return None
    if ram_gb is not None and ram_gb <= 8:
        return "low"
    if ram_gb is not None and ram_gb <= 16:
        return "mid"
    if ram_gb is not None and ram_gb > 16:
        return "high"
    if any(token in gpu_text for token in ["gtx 10", "rx 580", "1060"]):
        return "mid"
    return "unknown"


def _session_length_hint(game: Game, requirement: GameRequirement) -> str:
    if requirement.performance_tier_estimate == "low":
        return "likely accessible on low-to-mid range hardware"
    if requirement.performance_tier_estimate == "high":
        return "likely a heavier install and performance budget"
    return "session length should be inferred from tags and description"


def _coop_hint(feature: GameFeature) -> str:
    if feature.has_online_coop and feature.has_local_coop:
        return "supports both online and local co-op"
    if feature.has_online_coop:
        return "supports online co-op"
    if feature.has_local_coop:
        return "supports local co-op"
    if feature.has_multiplayer:
        return "supports multiplayer without explicit co-op signal"
    return "primarily single-player"


def _complexity_hint(requirement: GameRequirement) -> str:
    tier = requirement.performance_tier_estimate or "unknown"
    if tier == "low":
        return "lighter technical requirements"
    if tier == "mid":
        return "moderate technical requirements"
    if tier == "high":
        return "heavier technical requirements"
    return "technical complexity unknown"
