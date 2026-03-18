from __future__ import annotations

import json
import logging
import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.core.config import get_settings


router = APIRouter(prefix="/auth/google", tags=["auth"])
logger = logging.getLogger("auth_google")

GOOGLE_OAUTH_STATE_COOKIE = "google_oauth_state"
GOOGLE_OAUTH_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/calendar.readonly",
]
GOOGLE_REDIRECT_URI = "https://my-albert-app.onrender.com/auth/google/callback"


def load_google_credentials() -> dict:
    raw_json = os.environ.get("GOOGLE_CLIENT_SECRET_JSON")
    if raw_json:
        logger.info("Loading Google OAuth client credentials from GOOGLE_CLIENT_SECRET_JSON")
        try:
            credentials = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            logger.exception("GOOGLE_CLIENT_SECRET_JSON is not valid JSON")
            raise HTTPException(
                status_code=500,
                detail="GOOGLE_CLIENT_SECRET_JSON is present but not valid JSON.",
            ) from exc

        if not isinstance(credentials, dict):
            raise HTTPException(
                status_code=500,
                detail="GOOGLE_CLIENT_SECRET_JSON must decode to a JSON object.",
            )
        return credentials

    settings = get_settings()
    client_secret_path = settings.google_client_secret_path
    if client_secret_path is not None and client_secret_path.exists():
        logger.info("Loading Google OAuth client credentials from file %s", client_secret_path)
        try:
            with client_secret_path.open("r", encoding="utf-8") as file:
                credentials = json.load(file)
        except json.JSONDecodeError as exc:
            logger.exception("GOOGLE_CLIENT_SECRET_FILE contains invalid JSON")
            raise HTTPException(
                status_code=500,
                detail="GOOGLE_CLIENT_SECRET_FILE exists but contains invalid JSON.",
            ) from exc
        except OSError as exc:
            logger.exception("GOOGLE_CLIENT_SECRET_FILE could not be read")
            raise HTTPException(
                status_code=500,
                detail="GOOGLE_CLIENT_SECRET_FILE exists but could not be read.",
            ) from exc

        if not isinstance(credentials, dict):
            raise HTTPException(
                status_code=500,
                detail="GOOGLE_CLIENT_SECRET_FILE must contain a JSON object.",
            )
        return credentials

    logger.error("Google OAuth client credentials are not configured")
    raise HTTPException(
        status_code=500,
        detail=(
            "Google OAuth credentials are not configured. Set GOOGLE_CLIENT_SECRET_JSON "
            "or GOOGLE_CLIENT_SECRET_FILE."
        ),
    )


def _build_google_flow(*, state: str | None = None) -> Flow:
    client_config = load_google_credentials()

    flow = Flow.from_client_config(
        client_config,
        scopes=GOOGLE_OAUTH_SCOPES,
        state=state,
    )
    flow.redirect_uri = GOOGLE_REDIRECT_URI

    logger.info("Google OAuth flow initialized")
    logger.info("Google OAuth redirect_uri=%s", flow.redirect_uri)
    return flow


@router.get("/login")
async def google_login() -> RedirectResponse:
    flow = _build_google_flow()
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    logger.info("Redirecting user to Google consent screen")
    logger.info("Google OAuth redirect_uri=%s", flow.redirect_uri)

    response = RedirectResponse(url=authorization_url, status_code=302)
    response.set_cookie(
        key=GOOGLE_OAUTH_STATE_COOKIE,
        value=state,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=600,
    )
    return response


@router.get("/callback")
async def google_callback(request: Request) -> JSONResponse:
    if request.query_params.get("error"):
        logger.error("Google OAuth error=%s", request.query_params.get("error"))
        raise HTTPException(
            status_code=400,
            detail=f"Google OAuth error: {request.query_params.get('error')}",
        )

    state = request.query_params.get("state")
    code = request.query_params.get("code")
    expected_state = request.cookies.get(GOOGLE_OAUTH_STATE_COOKIE)

    if not state or not code:
        raise HTTPException(status_code=400, detail="Missing Google OAuth state or code.")

    if not expected_state or state != expected_state:
        logger.error("Google OAuth state mismatch: expected=%s actual=%s", expected_state, state)
        raise HTTPException(status_code=400, detail="Invalid Google OAuth state.")

    flow = _build_google_flow(state=state)
    authorization_response = f"{GOOGLE_REDIRECT_URI}?{request.url.query}"

    logger.info("Handling Google OAuth callback")
    logger.info("Google OAuth redirect_uri=%s", flow.redirect_uri)
    logger.info("Google OAuth authorization_response=%s", authorization_response)

    try:
        flow.fetch_token(authorization_response=authorization_response)
    except Exception as exc:
        logger.exception("Google OAuth token exchange failed")
        raise HTTPException(status_code=400, detail=f"Google token exchange failed: {exc}") from exc

    credentials = flow.credentials
    settings = get_settings()
    token_path = settings.google_token_path
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(credentials.to_json(), encoding="utf-8")
    os.chmod(token_path, 0o600)

    logger.info("Google OAuth tokens stored at %s", token_path)
    logger.info("Google OAuth refresh_token_present=%s", bool(credentials.refresh_token))

    try:
        calendar_service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
        calendar_list = calendar_service.calendarList().list(maxResults=10).execute()
        calendar_count = len(calendar_list.get("items", []))
        logger.info("Google Calendar connection verified, calendars=%s", calendar_count)
    except Exception as exc:
        logger.exception("Google Calendar verification failed")
        raise HTTPException(status_code=500, detail=f"Google Calendar verification failed: {exc}") from exc

    response = JSONResponse(
        content={
            "success": True,
            "message": "Google OAuth completed successfully.",
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "refresh_token_stored": bool(credentials.refresh_token),
            "token_file": str(token_path),
            "calendar_count": calendar_count,
        }
    )
    response.delete_cookie(
        key=GOOGLE_OAUTH_STATE_COOKIE,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return response
