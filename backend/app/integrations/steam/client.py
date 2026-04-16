import httpx

from app.core.config import settings
from app.schemas.steam import OwnedGame, OwnedGamesResponse

STEAM_PUBLIC_API_BASE = "https://api.steampowered.com"


async def get_owned_games(steam_id: str) -> OwnedGamesResponse:
    if not settings.steam_web_api_key:
        raise RuntimeError("STEAM_WEB_API_KEY is not configured")

    url = f"{STEAM_PUBLIC_API_BASE}/IPlayerService/GetOwnedGames/v1/"

    params = {
        "key": settings.steam_web_api_key,
        "steamid": steam_id,
        "include_appinfo": "true",
        "include_played_free_games": "true",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url, params=params)

    response.raise_for_status()
    payload = response.json()

    response_body = payload.get("response", {}) if isinstance(payload, dict) else {}
    raw_games = response_body.get("games", []) or []

    games = [OwnedGame(**game) for game in raw_games]

    return OwnedGamesResponse(
        steam_id=steam_id,
        game_count=response_body.get("game_count", len(games)),
        games=games,
    )
