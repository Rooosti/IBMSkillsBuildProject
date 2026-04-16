from pydantic import BaseModel


class SessionResponse(BaseModel):
    authenticated: bool
    steam_id: str | None = None
