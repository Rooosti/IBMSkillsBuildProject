from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.game_catalog import Game, GameFeature
from app.models.user import User
from app.models.user_owned_game import UserOwnedGame
from app.models.user_profile import UserPreference, UserRecentlyPlayedGame

def _listify(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v]
    return []


def get_user_taste_profile(db: Session, steam_id: str) -> dict[str, Any]:
    user = db.scalar(select(User).where(User.steam_id == steam_id))
    if not user:
        return {}

    # 1. Aggregate tags and genres from owned games, weighted by playtime
    owned_games = db.execute(
        select(UserOwnedGame.playtime_minutes, GameFeature.tags_json, GameFeature.genres_json)
        .join(Game, Game.steam_app_id == UserOwnedGame.steam_app_id)
        .join(GameFeature, GameFeature.game_id == Game.id)
        .where(UserOwnedGame.user_id == user.id)
    ).all()

    tag_scores: Counter[str] = Counter()
    genre_scores: Counter[str] = Counter()

    for playtime, tags_json, genres_json in owned_games:
        # Weight: log(playtime + 1) to avoid massive bias from one or two "forever" games
        import math
        weight = math.log10(playtime + 10) 
        
        for tag in _listify(tags_json):
            tag_scores[tag] += weight
        for genre in _listify(genres_json):
            genre_scores[genre] += weight

    # 2. Get explicit preferences
    prefs = db.scalar(select(UserPreference).where(UserPreference.user_id == user.id))
    
    favorite_tags = _listify(getattr(prefs, "favorite_tags_json", []))
    favorite_genres = _listify(getattr(prefs, "favorite_genres_json", []))
    disliked_tags = _listify(getattr(prefs, "disliked_tags_json", []))

    # Boost explicit favorites
    for tag in favorite_tags:
        tag_scores[tag] += 10.0
    for genre in favorite_genres:
        genre_scores[genre] += 10.0

    return {
        "tag_scores": dict(tag_scores),
        "genre_scores": dict(genre_scores),
        "disliked_tags": set(disliked_tags),
        "preferences": {
            "complexity": getattr(prefs, "complexity_preference", None),
            "solo_vs_coop": getattr(prefs, "solo_vs_coop_preference", None),
        }
    }


def score_game(
    game_data: dict[str, Any], 
    taste_profile: dict[str, Any],
    context_tags: list[str] | None = None,
    max_price: float | None = None
) -> float:
    """
    Scores a game based on user taste profile and optional search context.
    game_data is expected to have 'tags', 'genres', 'categories', 'has_online_coop', etc.
    """
    # 1. Hard price filter
    if max_price is not None:
        price = game_data.get("price_final_usd")
        if price is not None and price > max_price:
            return -1000.0

    score = 0.0
    
    game_tags = set(game_data.get("tags", []))
    game_genres = set(game_data.get("genres", []))
    game_categories = set(game_data.get("categories", []))
    
    # Combined set for broader matching
    all_traits = game_tags | game_genres | game_categories
    
    # 1. Disliked tags (Hard Penalty)
    if any(tag in taste_profile.get("disliked_tags", set()) for tag in game_tags):
        return -100.0

    # 2. Tag Similarity
    tag_scores = taste_profile.get("tag_scores", {})
    for tag in game_tags:
        score += tag_scores.get(tag, 0.0)

    # 3. Genre Similarity
    genre_scores = taste_profile.get("genre_scores", {})
    for genre in game_genres:
        score += genre_scores.get(genre, 0.0) * 2.0  # Genres weighted higher

    # 4. Contextual Match (if search terms provided)
    if context_tags:
        context_matches = 0
        for ct in context_tags:
            if ct.lower() in [t.lower() for t in all_traits]:
                context_matches += 1
        score += context_matches * 20.0

    # 5. Preference Alignment
    prefs = taste_profile.get("preferences", {})
    if prefs.get("solo_vs_coop") == "coop":
        if game_data.get("has_online_coop") or game_data.get("has_local_coop") or "Co-op" in game_categories:
            score += 15.0
    elif prefs.get("solo_vs_coop") == "solo":
        if game_data.get("has_singleplayer") or "Single-player" in game_categories:
            score += 10.0

    return score


def rank_games(
    db: Session,
    steam_id: str,
    candidates: list[dict[str, Any]],
    context_tags: list[str] | None = None,
    previously_recommended_ids: list[int] | None = None,
    max_price: float | None = None
) -> list[dict[str, Any]]:
    """
    Ranks a list of candidate games for a user.
    """
    user = db.scalar(select(User).where(User.steam_id == steam_id))
    if not user:
        return sorted(candidates, key=lambda x: x.get("title", ""))

    # Get set of owned steam_app_ids for quick lookup
    owned_app_ids = set(
        db.scalars(
            select(UserOwnedGame.steam_app_id)
            .where(UserOwnedGame.user_id == user.id)
        ).all()
    )
    
    prev_ids = set(previously_recommended_ids or [])

    taste_profile = get_user_taste_profile(db, steam_id)
    
    scored_candidates = []
    for game in candidates:
        app_id = game.get("steam_app_id")
        
        if taste_profile:
            score = score_game(game, taste_profile, context_tags, max_price=max_price)
        else:
            score = 0.0
            if max_price is not None:
                p = game.get("price_final_usd")
                if p is not None and p > max_price:
                    score = -1000.0
            
        # Apply heavy penalty for already recommended games
        if app_id in prev_ids:
            score -= 1000.0

        game_copy = game.copy()
        game_copy["recommendation_score"] = round(score, 2)
        game_copy["is_owned"] = app_id in owned_app_ids
        scored_candidates.append(game_copy)

    # Sort by score descending
    ranked = sorted(scored_candidates, key=lambda x: x["recommendation_score"], reverse=True)
    
    return ranked
