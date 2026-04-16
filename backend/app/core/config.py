import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


postgres_db = _require_env("POSTGRES_DB")
postgres_user = _require_env("POSTGRES_USER")
postgres_password = _require_env("POSTGRES_PASSWORD")
postgres_host = _require_env("POSTGRES_HOST")
postgres_port = _require_env("POSTGRES_PORT")


@dataclass(frozen=True)
class Settings:
    frontend_url: str
    api_base_url: str

    steam_openid_realm: str
    steam_openid_return_to: str
    steam_web_api_key: str

    session_secret: str
    cookie_secure: bool

    postgres_db: str
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: str
    database_url: str

    watsonx_url: str
    watsonx_api_key: str
    watsonx_project_id: str
    watsonx_model_id: str
    watsonx_verify_ssl: bool


settings = Settings(
    frontend_url=_require_env("FRONTEND_URL"),
    api_base_url=_require_env("API_BASE_URL"),
    steam_openid_realm=_require_env("STEAM_OPENID_REALM"),
    steam_openid_return_to=_require_env("STEAM_OPENID_RETURN_TO"),
    steam_web_api_key=_require_env("STEAM_WEB_API_KEY"),
    session_secret=_require_env("SESSION_SECRET"),
    cookie_secure=_as_bool(os.getenv("COOKIE_SECURE"), False),
    postgres_db=postgres_db,
    postgres_user=postgres_user,
    postgres_password=postgres_password,
    postgres_host=postgres_host,
    postgres_port=postgres_port,
    database_url=(
        f"postgresql+psycopg://{postgres_user}:{postgres_password}"
        f"@{postgres_host}:{postgres_port}/{postgres_db}"
    ),
    watsonx_url=_require_env("WATSONX_URL"),
    watsonx_api_key=_require_env("WATSONX_API_KEY"),
    watsonx_project_id=_require_env("WATSONX_PROJECT_ID"),
    watsonx_model_id=_require_env("WATSONX_MODEL_ID"),
    watsonx_verify_ssl=_as_bool(os.getenv("WATSONX_VERIFY_SSL"), True),
)
