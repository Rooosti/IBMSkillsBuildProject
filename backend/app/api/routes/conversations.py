from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import STEAM_SESSION_COOKIE, read_signed_token
from app.db.deps import get_db
from app.models.chat_conversation import ChatConversation

router = APIRouter()


def _steam_id_from_request(request: Request) -> str:
    token = request.cookies.get(STEAM_SESSION_COOKIE)
    payload = read_signed_token(token)

    if not payload or not payload.get("steam_id"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    return str(payload["steam_id"])


class CreateConversationResponse(BaseModel):
    conversation_id: int
    steam_id: str


@router.post("/conversations", response_model=CreateConversationResponse)
def create_conversation(
    request: Request,
    db: Session = Depends(get_db),
) -> CreateConversationResponse:
    steam_id = _steam_id_from_request(request)

    convo = ChatConversation(
        steam_id=steam_id,
        title=None,
    )
    db.add(convo)
    db.commit()
    db.refresh(convo)

    return CreateConversationResponse(
        conversation_id=convo.id,
        steam_id=steam_id,
    )
