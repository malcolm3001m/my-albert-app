from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def _parse_csv(value: Optional[str], *, default: Optional[List[str]] = None) -> List[str]:
    if value is None:
        return list(default or [])
    parts = [item.strip() for item in value.split(",")]
    return [item for item in parts if item]


def _parse_bool(value: Optional[str], *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_path(raw_path: Optional[str], *, fallback: Optional[str] = None) -> Optional[Path]:
    value = raw_path or fallback
    if not value:
        return None

    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (BACKEND_DIR / path).resolve()
    return path


class Settings(BaseModel):
    app_name: str = "My Albert API"
    app_env: str = "development"
    api_prefix: str = "/api"
    log_level: str = "INFO"
    allowed_origins: List[str] = Field(default_factory=lambda: list(DEFAULT_ALLOWED_ORIGINS))

    albert_base_url: Optional[str] = None
    albert_bearer_token: Optional[str] = None
    albert_http_timeout_seconds: float = 25.0
    albert_profile_cache_ttl_seconds: int = 300
    albert_detail_cache_ttl_seconds: int = 1800
    albert_use_fixtures: bool = False
    albert_fixtures_dir: Optional[str] = None

    google_calendar_enabled: bool = False
    google_client_secret_file: Optional[str] = None
    google_token_file: str = ".secrets/google_token.json"
    google_calendar_ids: List[str] = Field(default_factory=list)
    google_calendar_lookahead_days: int = 30
    google_max_results: int = 50
    google_local_auth_port: int = 8080
    supabase_url: str = "https://khfzyqbvqizctohdfhpr.supabase.co"
    supabase_anon_key: Optional[str] = None
    supabase_service_role_key: Optional[str] = None
    supabase_api_key: Optional[str] = None
    supabase_signed_url_ttl_seconds: int = 604800

    planner_lookahead_days: int = 30

    @property
    def fixtures_path(self) -> Optional[Path]:
        if not self.albert_use_fixtures:
            return None
        return _resolve_path(self.albert_fixtures_dir, fallback="../inside_export")

    @property
    def google_client_secret_path(self) -> Optional[Path]:
        return _resolve_path(self.google_client_secret_file)

    @property
    def google_token_path(self) -> Path:
        path = _resolve_path(self.google_token_file)
        if path is None:
            return (BACKEND_DIR / ".secrets" / "google_token.json").resolve()
        return path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv(BACKEND_DIR / ".env")

    return Settings(
        app_name=os.getenv("APP_NAME", "My Albert API"),
        app_env=os.getenv("APP_ENV", "development"),
        api_prefix=os.getenv("API_PREFIX", "/api"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        allowed_origins=_parse_csv(
            os.getenv("ALLOWED_ORIGINS"),
            default=DEFAULT_ALLOWED_ORIGINS,
        ),
        albert_base_url=os.getenv("ALBERT_BASE_URL"),
        albert_bearer_token=os.getenv("ALBERT_BEARER_TOKEN"),
        albert_http_timeout_seconds=float(os.getenv("ALBERT_HTTP_TIMEOUT_SECONDS", "25")),
        albert_profile_cache_ttl_seconds=int(
            os.getenv("ALBERT_PROFILE_CACHE_TTL_SECONDS", "300")
        ),
        albert_detail_cache_ttl_seconds=int(
            os.getenv("ALBERT_DETAIL_CACHE_TTL_SECONDS", "1800")
        ),
        albert_use_fixtures=_parse_bool(os.getenv("ALBERT_USE_FIXTURES"), default=False),
        albert_fixtures_dir=os.getenv("ALBERT_FIXTURES_DIR"),
        google_calendar_enabled=_parse_bool(
            os.getenv("GOOGLE_CALENDAR_ENABLED"),
            default=False,
        ),
        google_client_secret_file=os.getenv("GOOGLE_CLIENT_SECRET_FILE"),
        google_token_file=os.getenv("GOOGLE_TOKEN_FILE", ".secrets/google_token.json"),
        google_calendar_ids=_parse_csv(os.getenv("GOOGLE_CALENDAR_IDS")),
        google_calendar_lookahead_days=int(
            os.getenv("GOOGLE_CALENDAR_LOOKAHEAD_DAYS", "30")
        ),
        google_max_results=int(os.getenv("GOOGLE_MAX_RESULTS", "50")),
        google_local_auth_port=int(os.getenv("GOOGLE_LOCAL_AUTH_PORT", "8080")),
        supabase_url=os.getenv("SUPABASE_URL", "https://khfzyqbvqizctohdfhpr.supabase.co"),
        supabase_anon_key=os.getenv("SUPABASE_ANON_KEY"),
        supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        supabase_api_key=(
            os.getenv("SUPABASE_API_KEY")
            or os.getenv("SUPABASE_ANON_KEY")
            or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        ),
        supabase_signed_url_ttl_seconds=int(
            os.getenv("SUPABASE_SIGNED_URL_TTL_SECONDS", "604800")
        ),
        planner_lookahead_days=int(os.getenv("PLANNER_LOOKAHEAD_DAYS", "30")),
    )
