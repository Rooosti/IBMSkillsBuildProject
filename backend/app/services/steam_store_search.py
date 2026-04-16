from __future__ import annotations

import re
from typing import Any

import requests
from bs4 import BeautifulSoup
from sqlalchemy import select, func
from app.db.session import SessionLocal
from app.models.game_catalog import Game, GameFeature, GameSemanticDoc
from app.services.steam_tag_taxonomy_service import resolve_terms_to_tags
from app.services.embedding_service import embed_text


STEAM_SEARCH_URL = "https://store.steampowered.com/search/"
STEAM_APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"
USER_AGENT = "PlayNext/1.0"


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9+\- ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_app_id(row: Any) -> int | None:
    raw = row.get("data-ds-appid")
    if raw:
        match = re.search(r"\d+", str(raw))
        if match:
            return int(match.group(0))

    href = row.get("href", "")
    match = re.search(r"/app/(\d+)", href)
    if match:
        return int(match.group(1))

    return None


def _fetch_appdetails(app_id: int, cc: str, lang: str) -> dict[str, Any] | None:
    response = requests.get(
        STEAM_APPDETAILS_URL,
        params={
            "appids": app_id,
            "cc": cc,
            "l": lang,
        },
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    response.raise_for_status()

    payload = response.json()
    node = payload.get(str(app_id), {})

    if not node.get("success"):
        return None

    data = node.get("data") or {}
    if data.get("type") != "game":
        return None

    return data


def _compact_store_game(app_id: int, data: dict[str, Any]) -> dict[str, Any]:
    price_overview = data.get("price_overview") or {}
    genres = [g.get("description") for g in data.get("genres", []) if g.get("description")]
    categories = [c.get("description") for c in data.get("categories", []) if c.get("description")]

    final_price = price_overview.get("final")
    initial_price = price_overview.get("initial")
    
    price_final_float = final_price / 100.0 if final_price is not None else None
    price_initial_float = initial_price / 100.0 if initial_price is not None else None

    short_desc = data.get("short_description", "")
    if len(short_desc) > 150:
        short_desc = short_desc[:147] + "..."

    return {
        "steam_app_id": app_id,
        "title": data.get("name"),
        "is_free": data.get("is_free"),
        "price_formatted": price_overview.get("final_formatted"),
        "price_final_usd": price_final_float,
        "price_initial_usd": price_initial_float,
        "price_discount_percent": price_overview.get("discount_percent"),
        "price_currency": price_overview.get("currency"),
        "short_description": short_desc,
        "genres": genres,
        "categories": categories,
        "controller_support": data.get("controller_support"),
        "release_date": (data.get("release_date") or {}).get("date"),
        "header_image_url": data.get("header_image"),
        "store_url": f"https://store.steampowered.com/app/{app_id}",
    }

def _compact_db_game(game: Game, feature: GameFeature) -> dict[str, Any]:
    return {
        "steam_app_id": game.steam_app_id,
        "title": game.title,
        "is_free": game.is_free,
        "price_final_usd": float(game.price_current) if game.price_current else None,
        "price_currency": game.price_currency,
        "short_description": game.short_description,
        "genres": feature.genres_json or [],
        "categories": feature.categories_json or [],
        "controller_support": feature.controller_support,
        "header_image_url": game.header_image_url,
        "store_url": game.store_url,
    }

async def vector_search_games(
    query_text: str,
    limit: int | str = 10
) -> dict[str, Any]:
    """
    Performs a semantic search for games in our local catalog using pgvector.
    """
    limit = int(limit)
    try:
        query_embedding = await embed_text(query_text)
    except Exception as e:
        return {"error": f"Failed to generate embedding: {e}", "results": []}

    db = SessionLocal()
    try:
        # Use pgvector's <=> operator for cosine distance
        stmt = (
            select(Game, GameFeature)
            .join(GameFeature, Game.id == GameFeature.game_id)
            .join(GameSemanticDoc, Game.id == GameSemanticDoc.game_id)
            .order_by(GameSemanticDoc.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        
        rows = db.execute(stmt).all()
        results = [_compact_db_game(game, feature) for game, feature in rows]
        
        return {
            "query_text": query_text,
            "result_count": len(results),
            "results": results,
            "search_type": "semantic"
        }
    finally:
        db.close()

def search_steam_store(
    query_text: str,
    preferred_tags: list[str] | None = None,
    genres: list[str] | None = None,
    limit: int | str = 12,
    cc: str = "US",
    lang: str = "english",
) -> dict[str, Any]:
    limit = int(limit)
    if not query_text.strip():
        return {
            "query_text": query_text,
            "resolved_tags": [],
            "results": [],
            "error": "query_text is required",
        }

    with SessionLocal() as db:
        terms_to_resolve = [query_text]
        if preferred_tags:
            terms_to_resolve.extend(preferred_tags)
        if genres:
            terms_to_resolve.extend(genres)
        
        resolution = resolve_terms_to_tags(db, terms_to_resolve)
        
        resolved_tags = []
        seen_canonical = set()
        
        for term_res in resolution.get("resolved_terms", []):
            for match in term_res.get("matches", []):
                if match.get("steam_tag_id") and match["canonical_name"] not in seen_canonical:
                    resolved_tags.append({
                        "canonical_name": match["canonical_name"],
                        "category": match["category"],
                        "steam_tag_id": match["steam_tag_id"]
                    })
                    seen_canonical.add(match["canonical_name"])

    tag_ids = [str(item["steam_tag_id"]) for item in resolved_tags][:5]

    if not tag_ids:
        return {
            "query_text": query_text,
            "resolved_tags": resolved_tags,
            "results": [],
            "note": "No Steam tags resolved for live search",
        }

    response = requests.get(
        STEAM_SEARCH_URL,
        params={
            "tags": ",".join(tag_ids),
            "ignore_preferences": "1",
            "ndl": "1",
            "supportedlang": lang,
            "cc": cc,
        },
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.select("a.search_result_row")

    results: list[dict[str, Any]] = []
    seen_app_ids: set[int] = set()

    for row in rows:
        app_id = _extract_app_id(row)
        if not app_id or app_id in seen_app_ids:
            continue

        seen_app_ids.add(app_id)

        try:
            details = _fetch_appdetails(app_id=app_id, cc=cc, lang=lang)
        except requests.RequestException:
            continue

        if not details:
            continue

        results.append(_compact_store_game(app_id=app_id, data=details))

        if len(results) >= limit:
            break

    return {
        "query_text": query_text,
        "resolved_tags": resolved_tags,
        "result_count": len(results),
        "results": results,
        "search_type": "keyword"
    }
