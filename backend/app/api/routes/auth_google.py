from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.services.google.credentials import load_google_client_config


router = APIRouter(prefix="/auth/google", tags=["auth"])
logger = logging.getLogger("auth_google")

GOOGLE_OAUTH_STATE_COOKIE = "google_oauth_state"
GOOGLE_OAUTH_PKCE_COOKIE = "pkce_verifier"
GOOGLE_OAUTH_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]
GOOGLE_REDIRECT_URI = "https://my-albert-app.onrender.com/auth/google/callback"


def load_google_credentials() -> dict:
    try:
        return load_google_client_config()
    except Exception as exc:
        logger.exception("Google OAuth client credentials could not be loaded")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
    code_verifier = flow.code_verifier

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
    response.set_cookie(
        key=GOOGLE_OAUTH_PKCE_COOKIE,
        value=code_verifier,
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
    pkce_verifier = request.cookies.get(GOOGLE_OAUTH_PKCE_COOKIE)

    if not state or not code:
        raise HTTPException(status_code=400, detail="Missing Google OAuth state or code.")

    if not expected_state or state != expected_state:
        logger.error("Google OAuth state mismatch: expected=%s actual=%s", expected_state, state)
        raise HTTPException(status_code=400, detail="Invalid Google OAuth state.")

    if not pkce_verifier:
        logger.error("Google OAuth PKCE verifier cookie is missing")
        raise HTTPException(
            status_code=400,
            detail="Missing PKCE code verifier. Start the Google login flow again.",
        )

    flow = _build_google_flow(state=state)
    flow.code_verifier = pkce_verifier
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
    refresh_token = credentials.refresh_token

    if refresh_token:
        print(f"Google OAuth refresh token: {refresh_token}")
        logger.info("Google OAuth refresh token: %s", refresh_token)
        os.environ["GOOGLE_REFRESH_TOKEN"] = refresh_token
        logger.info("Google OAuth refresh token captured in GOOGLE_REFRESH_TOKEN for current process")
    else:
        print("Google OAuth refresh token missing in callback response")
        logger.info("Google OAuth refresh token missing in callback response")
        if not os.environ.get("GOOGLE_REFRESH_TOKEN"):
            logger.warning("No existing GOOGLE_REFRESH_TOKEN found in environment")

    logger.info("Google OAuth refresh_token_present=%s", bool(refresh_token))

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
            "refresh_token_stored": bool(os.environ.get("GOOGLE_REFRESH_TOKEN")),
            "token_storage": "GOOGLE_REFRESH_TOKEN",
            "calendar_count": calendar_count,
        }
    )
    response.delete_cookie(
        key=GOOGLE_OAUTH_STATE_COOKIE,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    response.delete_cookie(
        key=GOOGLE_OAUTH_PKCE_COOKIE,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return response
