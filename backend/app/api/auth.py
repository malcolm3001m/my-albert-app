from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request, status

from app.core.config import Settings
from app.utils.errors import MissingConfigurationError


@dataclass
class AuthenticatedUser:
    user_id: str
    claims: dict[str, Any]


def require_authenticated_user(request: Request) -> AuthenticatedUser:
    settings: Settings = request.app.state.settings
    secret = settings.supabase_jwt_secret
    if not secret:
        raise MissingConfigurationError(
            "SUPABASE_JWT_SECRET is missing. Configure it to validate Supabase access tokens."
        )

    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Supabase token.",
        )

    token = authorization[len("Bearer ") :].strip()
    claims = _decode_and_verify_supabase_jwt(token, secret)
    user_id = claims.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Supabase token.",
        )

    authenticated_user = AuthenticatedUser(user_id=user_id, claims=claims)
    request.state.authenticated_user = authenticated_user
    return authenticated_user


def _decode_and_verify_supabase_jwt(token: str, secret: str) -> dict[str, Any]:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Supabase token.",
        ) from exc

    header = _decode_jwt_segment(encoded_header)
    payload = _decode_jwt_segment(encoded_payload)

    if header.get("alg") != "HS256":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Supabase token.",
        )

    expected_signature = _base64url_encode(
        hmac.new(
            secret.encode("utf-8"),
            f"{encoded_header}.{encoded_payload}".encode("utf-8"),
            hashlib.sha256,
        ).digest()
    )

    if not hmac.compare_digest(expected_signature, encoded_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Supabase token.",
        )

    now = int(time.time())
    exp = payload.get("exp")
    if isinstance(exp, (int, float)) and now >= int(exp):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Supabase token.",
        )

    nbf = payload.get("nbf")
    if isinstance(nbf, (int, float)) and now < int(nbf):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Supabase token.",
        )

    return payload


def _decode_jwt_segment(segment: str) -> dict[str, Any]:
    try:
        padded = segment + "=" * (-len(segment) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("utf-8"))
        payload = json.loads(decoded.decode("utf-8"))
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Supabase token.",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Supabase token.",
        )
    return payload


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")
