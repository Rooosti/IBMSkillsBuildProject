import base64
import hashlib
import hmac
import json
import secrets
from typing import Any

from app.core.config import settings

STEAM_SESSION_COOKIE = "steam_session"
STEAM_AUTH_STATE_COOKIE = "steam_auth_state"


def create_state_token() -> str:
    return secrets.token_hex(16)


def _sign_value(value: str) -> str:
    digest = hmac.new(
        settings.session_secret.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def create_signed_token(payload: dict[str, Any]) -> str:
    encoded_payload = base64.urlsafe_b64encode(
        json.dumps(payload).encode("utf-8")
    ).decode("utf-8").rstrip("=")
    signature = _sign_value(encoded_payload)
    return f"{encoded_payload}.{signature}"


def read_signed_token(token: str | None) -> dict[str, Any] | None:
    if not token or "." not in token:
        return None

    encoded_payload, signature = token.split(".", 1)
    expected_signature = _sign_value(encoded_payload)

    if not hmac.compare_digest(signature, expected_signature):
        return None

    padded = encoded_payload + "=" * (-len(encoded_payload) % 4)

    try:
        payload_bytes = base64.urlsafe_b64decode(padded.encode("utf-8"))
        return json.loads(payload_bytes.decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None
