import re
from urllib.parse import urlencode, urlparse, parse_qsl

import httpx

from app.core.config import settings

OPENID_NS = "http://specs.openid.net/auth/2.0"
IDENTIFIER_SELECT = f"{OPENID_NS}/identifier_select"

# Use the interactive login endpoint for browser redirects and verification
STEAM_OPENID_LOGIN_ENDPOINT = "https://steamcommunity.com/openid/login"


def build_steam_openid_url(state: str) -> str:
    return_to = f"{settings.steam_openid_return_to}?state={state}"

    query = urlencode(
        {
            "openid.ns": OPENID_NS,
            "openid.mode": "checkid_setup",
            "openid.return_to": return_to,
            "openid.realm": settings.steam_openid_realm,
            "openid.identity": IDENTIFIER_SELECT,
            "openid.claimed_id": IDENTIFIER_SELECT,
        }
    )

    return f"{STEAM_OPENID_LOGIN_ENDPOINT}?{query}"


async def verify_steam_openid(callback_url: str) -> str | None:
    parsed = urlparse(callback_url)
    original_params = dict(parse_qsl(parsed.query, keep_blank_values=True))

    verify_params = {
        key: value
        for key, value in original_params.items()
        if key.startswith("openid.")
    }
    verify_params["openid.mode"] = "check_authentication"

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            STEAM_OPENID_LOGIN_ENDPOINT,
            data=verify_params,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if response.status_code != 200:
        return None

    if "is_valid:true" not in response.text:
        return None

    claimed_id = original_params.get("openid.claimed_id")
    if not claimed_id:
        return None

    match = re.match(r"^https?://steamcommunity\.com/openid/id/(\d+)$", claimed_id)
    if not match:
        return None

    return match.group(1)
