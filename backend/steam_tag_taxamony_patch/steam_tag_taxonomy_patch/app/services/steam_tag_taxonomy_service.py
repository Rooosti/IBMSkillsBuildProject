from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup
from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.models.steam_tag import SteamQueryTagMap, SteamTag, SteamTagAlias

STEAM_TAGS_DOC_URL = "https://partner.steamgames.com/doc/store/tags"
STEAM_TAGS_SNAPSHOT_VERSION = "steamworks-tags-doc-v1"
QUERY_MAP_SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "steam_query_tag_map_seed.json"

SECTION_MAP = {
    "Top-Level Genres": "top_level_genres",
    "Genres": "genres",
    "Sub-Genres": "sub_genres",
    "Visuals & Viewpoint": "visuals_viewpoint",
    "Themes & Moods": "themes_moods",
    "Features": "features",
    "Players": "players",
    "Other Tags": "other_tags",
}

SECTION_ORDER = list(SECTION_MAP.keys())


def normalize_term(value: str) -> str:
    value = value.strip().lower()
    value = value.replace("&", " and ")
    value = value.replace("/", " ")
    value = re.sub(r"[^a-z0-9+\-\s']", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


DEFAULT_ALIASES: dict[str, set[str]] = {
    "FPS": {"first person shooter"},
    "Third-Person Shooter": {"third person shooter", "tps"},
    "Top-Down Shooter": {"top down shooter"},
    "Action Roguelike": {"action rogue-like", "action roguelite", "action roguelike"},
    "Roguelite": {"rogue-lite", "roguelite"},
    "Roguelike": {"rogue-like", "roguelike"},
    "Souls-like": {"soulslike"},
    "Online Co-Op": {"online coop"},
    "Local Co-Op": {"local coop", "couch coop", "couch co-op"},
    "Singleplayer": {"single player"},
    "PvE": {"player vs environment"},
    "PvP": {"player vs player"},
    "Hack and Slash": {"hack n slash", "hack-and-slash"},
    "JRPG": {"j rpg", "japanese rpg"},
    "CRPG": {"classic rpg", "computer rpg"},
    "4X": {"4 x", "explore expand exploit exterminate"},
    "Turn-Based Tactics": {"turn based tactics"},
    "Real-Time Strategy": {"real time strategy"},
    "Story Rich": {"story-rich"},
    "Choices Matter": {"choice driven", "choices matter"},
    "Character Customization": {"character creator"},
    "Deckbuilding": {"deck builder", "deckbuilder", "deck building"},
    "Card Battler": {"card battler", "card battle"},
    "City Builder": {"city builder"},
    "Colony Sim": {"colony sim", "colony simulator"},
    "Automation": {"factory automation"},
    "Farming Sim": {"farm sim", "farming simulator"},
    "Life Sim": {"life sim", "life simulator"},
    "Open World Survival Craft": {"survival crafting", "open world survival craft"},
    "Metroidvania": {"metroid vania"},
    "Bullet Hell": {"bullethell"},
    "Twin Stick Shooter": {"twin-stick shooter", "twinstick shooter"},
    "Looter Shooter": {"loot shooter"},
    "Boomer Shooter": {"retro fps"},
    "Immersive Sim": {"immersive sim"},
    "Point & Click": {"point and click"},
    "World War II": {"ww2", "world war 2"},
    "Sci-fi": {"scifi", "science fiction"},
    "Post-apocalyptic": {"post apocalyptic"},
}


def fetch_steam_tags_doc_html(timeout_seconds: int = 30) -> str:
    response = requests.get(STEAM_TAGS_DOC_URL, timeout=timeout_seconds)
    response.raise_for_status()
    return response.text


def _extract_lines_from_html(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    return [line.strip() for line in soup.get_text("\n").splitlines() if line.strip()]


def parse_taxonomy_from_html(html: str) -> list[dict[str, str]]:
    lines = _extract_lines_from_html(html)
    parsed: list[dict[str, str]] = []
    current_category: str | None = None

    for index, line in enumerate(lines):
        if line in SECTION_MAP:
            current_category = SECTION_MAP[line]
            continue

        if current_category is None:
            continue

        if line == "Tag":
            continue

        if line in SECTION_ORDER:
            current_category = SECTION_MAP[line]
            continue

        next_line = lines[index + 1] if index + 1 < len(lines) else None
        if next_line in SECTION_ORDER:
            pass

        if line.startswith("## "):
            current_category = None
            continue

        if line in {
            "Commonly used tags:",
            "Simulation",
        } and current_category == "other_tags":
            continue

        if current_category:
            parsed.append(
                {
                    "canonical_name": line,
                    "category": current_category,
                }
            )

    unique: dict[tuple[str, str], dict[str, str]] = {}
    for item in parsed:
        key = (item["category"], item["canonical_name"])
        unique[key] = item

    return list(unique.values())


def _get_tag_by_name(db: Session, canonical_name: str) -> SteamTag | None:
    return db.scalar(select(SteamTag).where(SteamTag.canonical_name == canonical_name))


def upsert_taxonomy(db: Session, taxonomy_rows: list[dict[str, str]]) -> dict[str, int]:
    inserted = 0
    updated = 0

    for row in taxonomy_rows:
        existing = _get_tag_by_name(db, row["canonical_name"])
        if existing:
            existing.category = row["category"]
            existing.source_doc_url = STEAM_TAGS_DOC_URL
            existing.source_snapshot_version = STEAM_TAGS_SNAPSHOT_VERSION
            updated += 1
            tag = existing
        else:
            tag = SteamTag(
                canonical_name=row["canonical_name"],
                category=row["category"],
                source_doc_url=STEAM_TAGS_DOC_URL,
                source_snapshot_version=STEAM_TAGS_SNAPSHOT_VERSION,
                metadata_json=None,
            )
            db.add(tag)
            db.flush()
            inserted += 1

        alias_candidates = {row["canonical_name"], normalize_term(row["canonical_name"]) }
        alias_candidates.update(DEFAULT_ALIASES.get(row["canonical_name"], set()))

        existing_aliases = {
            alias.normalized_alias
            for alias in db.scalars(select(SteamTagAlias).where(SteamTagAlias.tag_id == tag.id)).all()
        }

        for alias in alias_candidates:
            normalized_alias = normalize_term(alias)
            if not normalized_alias or normalized_alias in existing_aliases:
                continue
            collision = db.scalar(select(SteamTagAlias).where(SteamTagAlias.normalized_alias == normalized_alias))
            if collision:
                continue
            db.add(
                SteamTagAlias(
                    tag_id=tag.id,
                    alias=alias,
                    normalized_alias=normalized_alias,
                    alias_type="seed",
                )
            )
            existing_aliases.add(normalized_alias)

    db.commit()
    return {"inserted": inserted, "updated": updated, "taxonomy_count": len(taxonomy_rows)}


def load_query_map_seed() -> list[dict[str, Any]]:
    with QUERY_MAP_SEED_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def seed_query_tag_map(db: Session, mappings: list[dict[str, Any]]) -> dict[str, int]:
    inserted = 0
    skipped_missing_tags = 0

    for mapping in mappings:
        query_term = mapping["query_term"]
        normalized_query_term = normalize_term(query_term)
        for target in mapping.get("targets", []):
            canonical_name = target["canonical_name"]
            weight = int(target.get("weight", 100))
            reason = target.get("reason")

            tag = _get_tag_by_name(db, canonical_name)
            if not tag:
                skipped_missing_tags += 1
                continue

            existing = db.scalar(
                select(SteamQueryTagMap).where(
                    SteamQueryTagMap.normalized_query_term == normalized_query_term,
                    SteamQueryTagMap.tag_id == tag.id,
                )
            )
            if existing:
                existing.query_term = query_term
                existing.weight = weight
                existing.match_reason = reason
                continue

            db.add(
                SteamQueryTagMap(
                    query_term=query_term,
                    normalized_query_term=normalized_query_term,
                    tag_id=tag.id,
                    weight=weight,
                    match_reason=reason,
                )
            )
            inserted += 1

    db.commit()
    return {
        "inserted": inserted,
        "skipped_missing_tags": skipped_missing_tags,
        "query_terms": len(mappings),
    }


def resolve_terms_to_tags(db: Session, terms: list[str], limit_per_term: int = 20) -> dict[str, Any]:
    resolved_terms: list[dict[str, Any]] = []

    for term in terms:
        normalized = normalize_term(term)
        if not normalized:
            continue

        mapped_rows = db.execute(
            select(SteamQueryTagMap, SteamTag)
            .join(SteamTag, SteamTag.id == SteamQueryTagMap.tag_id)
            .where(SteamQueryTagMap.normalized_query_term == normalized)
            .order_by(SteamQueryTagMap.weight.desc(), SteamTag.canonical_name.asc())
            .limit(limit_per_term)
        ).all()

        if mapped_rows:
            resolved_terms.append(
                {
                    "query_term": term,
                    "normalized_query_term": normalized,
                    "matches": [
                        {
                            "canonical_name": tag.canonical_name,
                            "category": tag.category,
                            "weight": mapping.weight,
                            "reason": mapping.match_reason,
                        }
                        for mapping, tag in mapped_rows
                    ],
                }
            )
            continue

        alias_rows = db.execute(
            select(SteamTagAlias, SteamTag)
            .join(SteamTag, SteamTag.id == SteamTagAlias.tag_id)
            .where(
                or_(
                    SteamTagAlias.normalized_alias == normalized,
                    SteamTag.canonical_name.ilike(term),
                )
            )
            .order_by(SteamTag.canonical_name.asc())
            .limit(limit_per_term)
        ).all()

        resolved_terms.append(
            {
                "query_term": term,
                "normalized_query_term": normalized,
                "matches": [
                    {
                        "canonical_name": tag.canonical_name,
                        "category": tag.category,
                        "matched_alias": alias.alias,
                    }
                    for alias, tag in alias_rows
                ],
            }
        )

    return {"resolved_terms": resolved_terms}


def list_tags_by_category(db: Session, category: str, limit: int = 500) -> dict[str, Any]:
    rows = db.scalars(
        select(SteamTag)
        .where(SteamTag.category == category)
        .order_by(SteamTag.canonical_name.asc())
        .limit(limit)
    ).all()

    return {
        "category": category,
        "count": len(rows),
        "tags": [row.canonical_name for row in rows],
    }
