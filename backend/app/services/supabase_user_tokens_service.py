from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.config import Settings
from app.utils.errors import MissingConfigurationError, UpstreamServiceError


class SupabaseUserTokensService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def ensure_user_row(self, user_id: str) -> None:
        await asyncio.to_thread(self._ensure_user_row_sync, user_id)

    async def user_row_exists(self, user_id: str) -> bool:
        return await asyncio.to_thread(self._user_row_exists_sync, user_id)

    async def get_google_refresh_token(self, user_id: str) -> Optional[str]:
        return await asyncio.to_thread(self._get_google_refresh_token_sync, user_id)

    async def set_google_refresh_token(self, user_id: str, refresh_token: str) -> None:
        await asyncio.to_thread(self._set_google_refresh_token_sync, user_id, refresh_token)

    async def clear_google_refresh_token(self, user_id: str) -> None:
        await asyncio.to_thread(self._clear_google_refresh_token_sync, user_id)

    def _client(self):
        if not self.settings.supabase_url:
            raise MissingConfigurationError("SUPABASE_URL is missing.")
        if not self.settings.supabase_service_role_key:
            raise MissingConfigurationError(
                "SUPABASE_SERVICE_ROLE_KEY is missing. It is required for per-user Google token storage."
            )
        try:
            from supabase import Client, create_client
        except ImportError as exc:
            raise MissingConfigurationError(
                "Supabase Python client is not installed. Add 'supabase' to backend requirements."
            ) from exc

        client: Client = create_client(
            self.settings.supabase_url,
            self.settings.supabase_service_role_key,
        )
        return client

    def _ensure_user_row_sync(self, user_id: str) -> None:
        client = self._client()
        try:
            client.table("user_tokens").upsert({"user_id": user_id}, on_conflict="user_id").execute()
        except Exception as exc:
            raise UpstreamServiceError(
                "Supabase",
                f"Failed to ensure user_tokens row for {user_id}: {exc}",
            ) from exc

    def _user_row_exists_sync(self, user_id: str) -> bool:
        client = self._client()
        try:
            response = (
                client.table("user_tokens")
                .select("user_id")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise UpstreamServiceError(
                "Supabase",
                f"Failed to validate user_tokens row for {user_id}: {exc}",
            ) from exc

        data = getattr(response, "data", None) or []
        return bool(data)

    def _get_google_refresh_token_sync(self, user_id: str) -> Optional[str]:
        client = self._client()
        try:
            response = (
                client.table("user_tokens")
                .select("google_refresh_token")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise UpstreamServiceError(
                "Supabase",
                f"Failed to load Google refresh token for {user_id}: {exc}",
            ) from exc

        data = getattr(response, "data", None) or []
        if not data:
            return None
        value = data[0].get("google_refresh_token")
        return value if isinstance(value, str) and value else None

    def _set_google_refresh_token_sync(self, user_id: str, refresh_token: str) -> None:
        client = self._client()
        payload: dict[str, Any] = {
            "google_refresh_token": refresh_token,
            "google_connected_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            client.table("user_tokens").update(payload).eq("user_id", user_id).execute()
        except Exception as exc:
            raise UpstreamServiceError(
                "Supabase",
                f"Failed to store Google refresh token for {user_id}: {exc}",
            ) from exc

    def _clear_google_refresh_token_sync(self, user_id: str) -> None:
        client = self._client()
        payload: dict[str, Any] = {
            "google_refresh_token": None,
            "google_connected_at": None,
        }
        try:
            client.table("user_tokens").update(payload).eq("user_id", user_id).execute()
        except Exception as exc:
            raise UpstreamServiceError(
                "Supabase",
                f"Failed to clear Google refresh token for {user_id}: {exc}",
            ) from exc
