from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.api.deps import get_supabase_user_tokens_service
from app.services.google.credentials import get_google_oauth_client_settings
from app.services.supabase_user_tokens_service import SupabaseUserTokensService


router = APIRouter(prefix="/api/google/auth", tags=["Google Calendar"])
logger = logging.getLogger("google_oauth_callback")
GOOGLE_OAUTH_REDIRECT_URI = "https://my-albert-app.onrender.com/api/google/auth/callback"
GOOGLE_FRONTEND_REDIRECT_URI = (
    "https://my-albert-hub-beta01.lovable.app/settings?google=connected"
)


@router.get("/callback")
async def google_auth_callback(
    code: str = Query(...),
    state: str = Query(...),
    user_tokens_service: SupabaseUserTokensService = Depends(get_supabase_user_tokens_service),
) -> RedirectResponse:
    if not state or not await user_tokens_service.user_row_exists(state):
        raise HTTPException(status_code=400, detail="Invalid Google OAuth state.")

    oauth_settings = get_google_oauth_client_settings()
    payload = {
        "code": code,
        "client_id": oauth_settings["client_id"],
        "client_secret": oauth_settings["client_secret"],
        "redirect_uri": GOOGLE_OAUTH_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(oauth_settings["token_uri"], data=payload)

    if response.status_code != 200:
        logger.error(
            "Google OAuth token exchange failed: status=%s body=%s",
            response.status_code,
            response.text,
        )
        raise HTTPException(status_code=400, detail="Google token exchange failed.")

    try:
        token_payload = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Google token exchange returned invalid JSON.") from exc

    refresh_token = token_payload.get("refresh_token")
    if not isinstance(refresh_token, str) or not refresh_token:
        raise HTTPException(status_code=400, detail="Google refresh token missing from token exchange.")

    await user_tokens_service.set_google_refresh_token(state, refresh_token)
    return RedirectResponse(url=GOOGLE_FRONTEND_REDIRECT_URI, status_code=302)
