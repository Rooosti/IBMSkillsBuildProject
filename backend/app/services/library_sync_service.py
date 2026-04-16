from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.steam.client import get_owned_games
from app.models.user import User
from app.models.user_owned_game import UserOwnedGame


def get_or_create_user_by_steam_id(db: Session, steam_id: str) -> User:
    user = db.scalar(select(User).where(User.steam_id == steam_id))
    if user:
        return user

    user = User(steam_id=steam_id)
    db.add(user)
    db.flush()
    return user


async def sync_owned_games_for_steam_user(db: Session, steam_id: str) -> dict:
    user = get_or_create_user_by_steam_id(db, steam_id)
    owned_games_response = await get_owned_games(steam_id)

    existing = db.scalars(
        select(UserOwnedGame).where(UserOwnedGame.user_id == user.id)
    ).all()

    by_app_id = {row.steam_app_id: row for row in existing}
    now = datetime.now(timezone.utc)

    for game in owned_games_response.games:
        row = by_app_id.get(game.appid)

        if row:
            row.game_name = game.name
            row.owned = True
            row.playtime_minutes = game.playtime_forever or 0
            row.last_synced_at = now
        else:
            db.add(
                UserOwnedGame(
                    user_id=user.id,
                    game_id=None,
                    steam_app_id=game.appid,
                    game_name=game.name,
                    owned=True,
                    playtime_minutes=game.playtime_forever or 0,
                    last_synced_at=now,
                )
            )

    db.commit()

    return {
        "user_id": user.id,
        "steam_id": steam_id,
        "game_count": owned_games_response.game_count,
    }
