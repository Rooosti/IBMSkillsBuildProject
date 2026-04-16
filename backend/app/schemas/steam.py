from pydantic import BaseModel


class OwnedGame(BaseModel):
    appid: int
    name: str | None = None
    playtime_forever: int | None = None
    img_icon_url: str | None = None
    img_logo_url: str | None = None


class OwnedGamesResponse(BaseModel):
    steam_id: str
    game_count: int
    games: list[OwnedGame]
