from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import HTTPException, Request, status

from app.core.config import Settings
from app.utils.errors import MissingConfigurationError


DEFAULT_SUPABASE_URL = "https://khfzyqbvqizctohdfhpr.supabase.co"


@dataclass
class AuthenticatedUser:
    user_id: str
    claims: dict[str, Any]


async def require_authenticated_user(request: Request) -> AuthenticatedUser:
    settings: Settings = request.app.state.settings
    supabase_url = (settings.supabase_url or DEFAULT_SUPABASE_URL).rstrip("/")
    supabase_api_key = settings.supabase_api_key
    if not supabase_api_key:
        raise MissingConfigurationError(
            "SUPABASE_API_KEY or SUPABASE_ANON_KEY is missing. Configure it to validate Supabase access tokens."
        )

    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    token = authorization[len("Bearer ") :].strip()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{supabase_url}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": supabase_api_key,
                },
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Supabase auth verification failed: {exc}",
        ) from exc

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    try:
        claims = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase auth verification returned invalid JSON.",
        ) from exc

    user_id = claims.get("id") or claims.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    authenticated_user = AuthenticatedUser(user_id=user_id, claims=claims)
    request.state.authenticated_user = authenticated_user
    return authenticated_user
