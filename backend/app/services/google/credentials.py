from __future__ import annotations

import json
import logging
import os
from typing import Sequence

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from app.core.config import get_settings
from app.utils.errors import MissingConfigurationError


logger = logging.getLogger("google_credentials")
DEFAULT_GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def load_google_client_config() -> dict:
    raw_json = os.environ.get("GOOGLE_CLIENT_SECRET_JSON")
    if raw_json:
        logger.info("Loading Google OAuth client config from GOOGLE_CLIENT_SECRET_JSON")
        try:
            config = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise MissingConfigurationError(
                "GOOGLE_CLIENT_SECRET_JSON is present but not valid JSON."
            ) from exc

        if not isinstance(config, dict):
            raise MissingConfigurationError(
                "GOOGLE_CLIENT_SECRET_JSON must decode to a JSON object."
            )
        return config

    settings = get_settings()
    client_secret_path = settings.google_client_secret_path
    if client_secret_path is not None and client_secret_path.exists():
        logger.info("Loading Google OAuth client config from file %s", client_secret_path)
        try:
            return json.loads(client_secret_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise MissingConfigurationError(
                "GOOGLE_CLIENT_SECRET_FILE exists but contains invalid JSON."
            ) from exc
        except OSError as exc:
            raise MissingConfigurationError(
                "GOOGLE_CLIENT_SECRET_FILE exists but could not be read."
            ) from exc

    raise MissingConfigurationError(
        "Google OAuth client credentials are not configured. "
        "Set GOOGLE_CLIENT_SECRET_JSON or GOOGLE_CLIENT_SECRET_FILE."
    )


def get_google_credentials(
    scopes: Sequence[str] | None = None,
) -> Credentials:
    refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN")
    if not refresh_token:
        raise MissingConfigurationError(
            "GOOGLE_REFRESH_TOKEN is missing. Complete Google OAuth and set it in Render env vars."
        )

    client_config = load_google_client_config()
    oauth_config = client_config.get("web") or client_config.get("installed")
    if not isinstance(oauth_config, dict):
        raise MissingConfigurationError(
            "Google client configuration must contain a 'web' or 'installed' object."
        )

    client_id = oauth_config.get("client_id")
    client_secret = oauth_config.get("client_secret")
    token_uri = oauth_config.get("token_uri") or "https://oauth2.googleapis.com/token"
    if not client_id or not client_secret:
        raise MissingConfigurationError(
            "Google client configuration is missing client_id or client_secret."
        )

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=token_uri,
        client_id=client_id,
        client_secret=client_secret,
        scopes=list(scopes or DEFAULT_GOOGLE_SCOPES),
    )

    try:
        credentials.refresh(Request())
    except Exception as exc:
        logger.exception("Failed to refresh Google access token")
        raise MissingConfigurationError(
            "Failed to refresh Google access token using GOOGLE_REFRESH_TOKEN."
        ) from exc

    return credentials
