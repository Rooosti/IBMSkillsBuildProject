import json
import traceback

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.core.security import STEAM_SESSION_COOKIE, read_signed_token
from app.db.deps import get_db
from app.schemas.chat import ChatRequest
from app.services.llm_service import answer_chat_message_stream

router = APIRouter(prefix="/chat", tags=["chat"])


def _steam_id_from_request(request: Request) -> str:
    token = request.cookies.get(STEAM_SESSION_COOKIE)
    payload = read_signed_token(token)

    if not payload or not payload.get("steam_id"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    return str(payload["steam_id"])


@router.post("")
async def chat(
    request: Request,
    payload: ChatRequest,
    db: Session = Depends(get_db),
):
    steam_id = _steam_id_from_request(request)

    async def event_generator():
        try:
            async for chunk in answer_chat_message_stream(
                db=db,
                steam_id=steam_id,
                conversation_id=payload.conversation_id,
                user_message=payload.message,
            ):
                yield {"data": json.dumps(chunk)}
        except Exception as exc:
            traceback.print_exc()
            yield {"data": json.dumps({"error": str(exc)})}

    return EventSourceResponse(event_generator())
