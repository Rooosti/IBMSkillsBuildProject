import time
from urllib.parse import urlencode

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    STEAM_AUTH_STATE_COOKIE,
    STEAM_SESSION_COOKIE,
    create_signed_token,
    create_state_token,
    read_signed_token,
)
from app.db.deps import get_db
from app.integrations.steam.openid import build_steam_openid_url, verify_steam_openid
from app.schemas.auth import SessionResponse
from app.services.library_sync_service import sync_owned_games_for_steam_user
from scripts.ingest_owned_games_metadata import ingest_owned_metadata_for_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/steam")
async def start_steam_auth() -> RedirectResponse:
    state = create_state_token()
    auth_url = build_steam_openid_url(state)

    response = RedirectResponse(url=auth_url, status_code=302)
    response.set_cookie(
        key=STEAM_AUTH_STATE_COOKIE,
        value=state,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=60 * 10,
        path="/",
    )
    return response


@router.get("/steam/callback")
async def steam_auth_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    state_from_url = request.query_params.get("state")
    state_from_cookie = request.cookies.get(STEAM_AUTH_STATE_COOKIE)

    if not state_from_url or not state_from_cookie or state_from_url != state_from_cookie:
        response = RedirectResponse(
            url=f"{settings.frontend_url}?steamAuth=state_error",
            status_code=302,
        )
        response.delete_cookie(STEAM_AUTH_STATE_COOKIE, path="/")
        return response

    steam_id = await verify_steam_openid(str(request.url))

    if not steam_id:
        response = RedirectResponse(
            url=f"{settings.frontend_url}?steamAuth=failed",
            status_code=302,
        )
        response.delete_cookie(STEAM_AUTH_STATE_COOKIE, path="/")
        return response

    token = create_signed_token(
        {
            "steam_id": steam_id,
            "issued_at": int(time.time()),
        }
    )

    library_sync = "skipped"
    metadata_ingest = "skipped"
    imported_count = 0

    try:
        sync_result = await sync_owned_games_for_steam_user(db, steam_id)
        library_sync = "ok"
        imported_count = int(sync_result.get("game_count", 0))

        # Kick off metadata/tag ingestion in the background after the response is sent.
        background_tasks.add_task(ingest_owned_metadata_for_user, steam_id)
        metadata_ingest = "started"

    except Exception:
        library_sync = "failed"
        metadata_ingest = "skipped"

    query = urlencode(
        {
            "steamAuth": "success",
            "librarySync": library_sync,
            "metadataIngest": metadata_ingest,
            "imported": imported_count,
        }
    )

    response = RedirectResponse(
        url=f"{settings.frontend_url}?{query}",
        status_code=302,
    )
    response.delete_cookie(STEAM_AUTH_STATE_COOKIE, path="/")
    response.set_cookie(
        key=STEAM_SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
        path="/",
    )
    return response


@router.get("/session", response_model=SessionResponse)
async def get_session(request: Request) -> SessionResponse:
    token = request.cookies.get(STEAM_SESSION_COOKIE)
    payload = read_signed_token(token)

    if not payload:
        return SessionResponse(authenticated=False, steam_id=None)

    return SessionResponse(
        authenticated=True,
        steam_id=str(payload.get("steam_id")),
    )


@router.post("/logout")
async def logout() -> Response:
    response = JSONResponse({"ok": True})
    response.delete_cookie(STEAM_SESSION_COOKIE, path="/")
    return response
