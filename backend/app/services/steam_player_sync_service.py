from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.user_profile import UserRecentlyPlayedGame
from app.services.steam_client import SteamClient


# Replace these imports with your existing user models.
from app.models.user import User
from app.models.user_owned_game import UserOwnedGame


def sync_owned_games(db: Session, client: SteamClient, *, steam_id: str) -> dict[str, int]:
    user = db.scalar(select(User).where(User.steam_id == steam_id))
    if user is None:
        raise ValueError(f"No user found for steam_id={steam_id}")

    games = client.get_owned_games(steam_id=steam_id)
    now = datetime.now(timezone.utc)
    seen_app_ids: set[int] = set()

    for item in games:
        app_id = int(item["appid"])
        seen_app_ids.add(app_id)
        row = db.scalar(
            select(UserOwnedGame).where(
                UserOwnedGame.user_id == user.id,
                UserOwnedGame.steam_app_id == app_id,
            )
        )
        if row is None:
            row = UserOwnedGame(
                user_id=user.id,
                steam_app_id=app_id,
            )
            db.add(row)

        row.game_name = item.get("name")
        row.owned = True
        row.playtime_minutes = int(item.get("playtime_forever") or 0)
        row.last_synced_at = now

    db.commit()
    return {"owned_games_synced": len(seen_app_ids)}


def sync_recently_played_games(db: Session, client: SteamClient, *, steam_id: str, count: int = 20) -> dict[str, int]:
    user = db.scalar(select(User).where(User.steam_id == steam_id))
    if user is None:
        raise ValueError(f"No user found for steam_id={steam_id}")

    games = client.get_recently_played_games(steam_id=steam_id, count=count)
    now = datetime.now(timezone.utc)

    db.execute(delete(UserRecentlyPlayedGame).where(UserRecentlyPlayedGame.user_id == user.id))

    for item in games:
        db.add(
            UserRecentlyPlayedGame(
                user_id=user.id,
                steam_app_id=int(item["appid"]),
                game_name=item.get("name"),
                playtime_2weeks_minutes=int(item.get("playtime_2weeks") or 0),
                playtime_forever_minutes=int(item.get("playtime_forever") or 0),
                last_synced_at=now,
            )
        )

    db.commit()
    return {"recently_played_synced": len(games)}
