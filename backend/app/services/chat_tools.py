from __future__ import annotations

from collections import Counter
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from typing import Any

from app.models.user import User
from app.models.user_owned_game import UserOwnedGame
from app.models.user_profile import UserRecentlyPlayedGame, UserPreference
from app.models.user_device_profile import UserDeviceProfile
from app.models.game_catalog import Game, GameFeature, GameRequirement

def _safe_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(n, maximum))


def _get_user(db: Session, steam_id: str) -> User | None:
    return db.scalar(select(User).where(User.steam_id == steam_id))


def list_owned_games(
    db: Session,
    steam_id: str,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    user = db.scalar(select(User).where(User.steam_id == steam_id))

    if not user:
        return {
            "steam_id": steam_id,
            "user_found": False,
            "total_owned_games": 0,
            "games": [],
        }

    total_owned_games = db.query(UserOwnedGame).filter(
        UserOwnedGame.user_id == user.id
    ).count()

    rows = db.scalars(
        select(UserOwnedGame)
        .where(UserOwnedGame.user_id == user.id)
        .order_by(UserOwnedGame.game_name.asc())
        .offset(offset)
        .limit(limit)
    ).all()

    return {
        "steam_id": steam_id,
        "user_found": True,
        "total_owned_games": total_owned_games,
        "limit": limit,
        "offset": offset,
        "games": [
            {
                "steam_app_id": row.steam_app_id,
                "name": row.game_name,
                "playtime_minutes": row.playtime_minutes,
            }
            for row in rows
        ],
    }


def _listify(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v]
    return []


def get_library_import_status(db: Session, steam_id: str) -> dict:
    user = _get_user(db, steam_id)

    if not user:
        return {
            "steam_id": steam_id,
            "user_found": False,
            "imported_game_count": 0,
            "total_playtime_minutes": 0,
            "last_synced_at": None,
            "top_games": [],
        }

    stats = db.execute(
        select(
            func.count(UserOwnedGame.id),
            func.coalesce(func.sum(UserOwnedGame.playtime_minutes), 0),
            func.max(UserOwnedGame.last_synced_at),
        ).where(UserOwnedGame.user_id == user.id)
    ).one()

    top_games = db.scalars(
        select(UserOwnedGame)
        .where(UserOwnedGame.user_id == user.id)
        .order_by(
            UserOwnedGame.playtime_minutes.desc(),
            UserOwnedGame.steam_app_id.asc(),
        )
        .limit(5)
    ).all()

    return {
        "steam_id": steam_id,
        "user_found": True,
        "imported_game_count": int(stats[0] or 0),
        "total_playtime_minutes": int(stats[1] or 0),
        "last_synced_at": stats[2].isoformat() if stats[2] else None,
        "top_games": [
            {
                "steam_app_id": row.steam_app_id,
                "name": row.game_name,
                "playtime_minutes": row.playtime_minutes,
            }
            for row in top_games
        ],
    }


def get_recently_played_games(db: Session, steam_id: str, limit: int = 5) -> dict:
    user = _get_user(db, steam_id)

    if not user:
        return {
            "steam_id": steam_id,
            "user_found": False,
            "recently_played_games": [],
        }

    rows = db.scalars(
        select(UserRecentlyPlayedGame)
        .where(UserRecentlyPlayedGame.user_id == user.id)
        .order_by(UserRecentlyPlayedGame.playtime_2weeks_minutes.desc())
        .limit(limit)
    ).all()

    return {
        "steam_id": steam_id,
        "user_found": True,
        "recently_played_games": [
            {
                "steam_app_id": row.steam_app_id,
                "name": row.game_name,
                "playtime_2weeks_minutes": row.playtime_2weeks_minutes,
                "playtime_forever_minutes": row.playtime_forever_minutes,
                "last_synced_at": row.last_synced_at.isoformat() if row.last_synced_at else None,
            }
            for row in rows
        ],
    }


from app.services.library_sync_service import sync_owned_games_for_steam_user

async def get_user_context(db: Session, steam_id: str) -> dict:
    # Always sync first to get latest library state
    try:
        await sync_owned_games_for_steam_user(db, steam_id)
    except Exception as e:
        print(f"Sync failed during context gathering: {e}")
        # Continue with existing data if sync fails

    user = _get_user(db, steam_id)

    if not user:
        return {
            "steam_id": steam_id,
            "user_found": False,
        }

    library = get_library_import_status(db, steam_id)
    recent = get_recently_played_games(db, steam_id, limit=5)

    device_profile = db.scalar(
        select(UserDeviceProfile).where(UserDeviceProfile.user_id == user.id)
    )

    preferences = db.scalar(
        select(UserPreference).where(UserPreference.user_id == user.id)
    )

    owned_rows = db.execute(
    select(GameFeature.tags_json, GameFeature.genres_json)
        .join(Game, Game.id == GameFeature.game_id)
        .join(UserOwnedGame, UserOwnedGame.steam_app_id == Game.steam_app_id)
        .where(UserOwnedGame.user_id == user.id)
    ).all()
    tag_counter: Counter[str] = Counter()
    genre_counter: Counter[str] = Counter()

    for tags_json, genres_json in owned_rows:
        tag_counter.update(_listify(tags_json))
        genre_counter.update(_listify(genres_json))

    return {
        "steam_id": steam_id,
        "user_found": True,
        "library_summary": {
            "total_games": library.get("imported_game_count"),
            "top_played_games": [g["name"] for g in library.get("top_games", [])]
        },
        "recent_games": [g["name"] for g in recent.get("recently_played_games", [])],
        "preferences": {
            "favorite_genres": _listify(getattr(preferences, "favorite_genres_json", None)),
            "favorite_tags": _listify(getattr(preferences, "favorite_tags_json", None)),
            "disliked_tags": _listify(getattr(preferences, "disliked_tags_json", None)),
        },
        "top_owned_tags": [
            {"tag": tag, "count": count}
            for tag, count in tag_counter.most_common(10)
        ],
    }


def get_game_metadata(db: Session, steam_app_id: int) -> dict:
    game = db.scalar(select(Game).where(Game.steam_app_id == steam_app_id))

    if not game:
        return {
            "found": False,
            "steam_app_id": steam_app_id,
        }

    features = db.scalar(select(GameFeature).where(GameFeature.game_id == game.id))
    requirements = db.scalar(select(GameRequirement).where(GameRequirement.game_id == game.id))

    return {
        "found": True,
        "steam_app_id": game.steam_app_id,
        "title": game.title,
        "short_description": game.short_description,
        "release_date": game.release_date.isoformat() if getattr(game, "release_date", None) else None,
        "developer": game.developer,
        "publisher": game.publisher,
        "price_current": game.price_current,
        "price_currency": game.price_currency,
        "store_url": game.store_url,
        "header_image_url": game.header_image_url,
        "features": {
            "genres": _listify(getattr(features, "genres_json", None)),
            "tags": _listify(getattr(features, "tags_json", None)),
            "categories": _listify(getattr(features, "categories_json", None)),
            "has_singleplayer": getattr(features, "has_singleplayer", None),
            "has_multiplayer": getattr(features, "has_multiplayer", None),
            "has_online_coop": getattr(features, "has_online_coop", None),
            "has_local_coop": getattr(features, "has_local_coop", None),
            "has_pvp": getattr(features, "has_pvp", None),
            "controller_support": getattr(features, "controller_support", None),
            "steam_deck_status": getattr(features, "steam_deck_status", None),
        } if features else None,
        "requirements": {
            "min_os": getattr(requirements, "min_os", None),
            "min_cpu_text": getattr(requirements, "min_cpu_text", None),
            "min_gpu_text": getattr(requirements, "min_gpu_text", None),
            "min_ram_gb": getattr(requirements, "min_ram_gb", None),
            "min_storage_gb": getattr(requirements, "min_storage_gb", None),
            "recommended_os": getattr(requirements, "recommended_os", None),
            "recommended_cpu_text": getattr(requirements, "recommended_cpu_text", None),
            "recommended_gpu_text": getattr(requirements, "recommended_gpu_text", None),
            "recommended_ram_gb": getattr(requirements, "recommended_ram_gb", None),
            "recommended_storage_gb": getattr(requirements, "recommended_storage_gb", None),
            "performance_tier_estimate": getattr(requirements, "performance_tier_estimate", None),
        } if requirements else None,
    }


def get_reference_game_features(db: Session, steam_app_id: int) -> dict:
    metadata = get_game_metadata(db, steam_app_id)

    if not metadata.get("found"):
        return metadata

    features = metadata.get("features") or {}

    return {
        "found": True,
        "steam_app_id": metadata["steam_app_id"],
        "title": metadata["title"],
        "genres": features.get("genres", []),
        "tags": features.get("tags", []),
        "categories": features.get("categories", []),
        "controller_support": features.get("controller_support"),
        "steam_deck_status": features.get("steam_deck_status"),
        "has_online_coop": features.get("has_online_coop"),
        "has_local_coop": features.get("has_local_coop"),
        "short_description": metadata.get("short_description"),
    }


from app.services.steam_tag_taxonomy_service import resolve_terms_to_tags

def search_owned_games(
    db: Session,
    steam_id: str,
    genres: list[str] | None = None,
    tags: list[str] | None = None,
    coop_only: bool | None = None,
    controller_required: bool | None = None,
    steam_deck_only: bool | None = None,
    max_minutes_played: int | None = None,
    limit: int = 10,
) -> dict:
    def _safe_int(value: Any, default: int, minimum: int, maximum: int) -> int:
        try:
            n = int(value)
        except (TypeError, ValueError):
            return default
        return max(minimum, min(n, maximum))

    user = _get_user(db, steam_id)

    if not user:
        return {
            "steam_id": steam_id,
            "user_found": False,
            "results": [],
        }

    limit = _safe_int(limit, default=10, minimum=1, maximum=25)

    resolved_tag_names: set[str] = set()
    if tags:
        resolution = resolve_terms_to_tags(db, tags)
        for term_res in resolution.get("resolved_terms", []):
            for match in term_res.get("matches", []):
                canonical_name = match.get("canonical_name")
                if canonical_name:
                    resolved_tag_names.add(canonical_name.lower())

    for t in (tags or []):
        if t:
            resolved_tag_names.add(t.lower())

    stmt = (
        select(UserOwnedGame, Game, GameFeature)
        .join(Game, Game.steam_app_id == UserOwnedGame.steam_app_id)
        .join(GameFeature, GameFeature.game_id == Game.id)
        .where(UserOwnedGame.user_id == user.id)
    )

    if max_minutes_played is not None:
        max_minutes_played = _safe_int(
            max_minutes_played,
            default=10_000_000,
            minimum=0,
            maximum=10_000_000,
        )
        stmt = stmt.where(UserOwnedGame.playtime_minutes <= max_minutes_played)

    if coop_only is True:
        stmt = stmt.where(
            (GameFeature.has_online_coop.is_(True)) |
            (GameFeature.has_local_coop.is_(True))
        )

    if controller_required is True:
        stmt = stmt.where(GameFeature.controller_support.isnot(None))

    if steam_deck_only is True:
        stmt = stmt.where(GameFeature.steam_deck_status.in_(["verified", "playable"]))

    stmt = stmt.order_by(
        UserOwnedGame.playtime_minutes.desc(),
        Game.title.asc(),
    )

    rows = db.execute(stmt).all()

    genre_set = {g.lower() for g in (genres or []) if g}

    results = []
    for owned_row, game, feature in rows:
        game_genres = _listify(feature.genres_json)
        game_tags = _listify(feature.tags_json)

        game_genres_lower = {x.lower() for x in game_genres}
        game_tags_lower = {x.lower() for x in game_tags}

        if genre_set and not genre_set.intersection(game_genres_lower):
            continue

        if resolved_tag_names and not resolved_tag_names.intersection(game_tags_lower):
            continue

        results.append(
            {
                "steam_app_id": owned_row.steam_app_id,
                "title": game.title,
                "short_description": game.short_description,
                "header_image_url": game.header_image_url,
                "store_url": game.store_url,
                "playtime_minutes": owned_row.playtime_minutes,
                "genres": game_genres,
                "tags": game_tags,
                "controller_support": feature.controller_support,
                "steam_deck_status": feature.steam_deck_status,
                "has_online_coop": feature.has_online_coop,
                "has_local_coop": feature.has_local_coop,
                "is_owned": True,
            }
        )
        
        if len(results) >= limit:
            break

    #DEBUGGING:
    print("search_owned_games called with:", {
        "genres": genres,
        "tags": tags,
        "coop_only": coop_only,
        "controller_required": controller_required,
        "steam_deck_only": steam_deck_only,
        "max_minutes_played": max_minutes_played,
        "limit": limit,
    })

    return {
        "steam_id": steam_id,
        "user_found": True,
        "results": results,
    }
