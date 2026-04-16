from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.security import STEAM_SESSION_COOKIE, read_signed_token
from app.db.deps import get_db
from app.integrations.steam.client import get_owned_games
from app.schemas.steam import OwnedGamesResponse
from app.services.library_sync_service import sync_owned_games_for_steam_user

router = APIRouter(prefix="/steam", tags=["steam"])


def _steam_id_from_request(request: Request) -> str:
    token = request.cookies.get(STEAM_SESSION_COOKIE)
    payload = read_signed_token(token)

    if not payload or not payload.get("steam_id"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    return str(payload["steam_id"])


@router.get("/owned-games", response_model=OwnedGamesResponse)
async def owned_games(request: Request) -> OwnedGamesResponse:
    steam_id = _steam_id_from_request(request)

    try:
      return await get_owned_games(steam_id)
    except RuntimeError as exc:
      raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
      raise HTTPException(status_code=502, detail="Steam API request failed") from exc


@router.post("/sync-library")
async def sync_library(
    request: Request,
    db: Session = Depends(get_db),
):
    steam_id = _steam_id_from_request(request)

    try:
        result = await sync_owned_games_for_steam_user(db, steam_id)
        return {"ok": True, **result}
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Steam sync failed") from exc
