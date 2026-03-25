from __future__ import annotations

from typing import Optional
from urllib.parse import quote

import httpx

from app.core.config import Settings
from app.utils.errors import MissingConfigurationError, UpstreamServiceError


class SupabaseStorageService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def create_signed_url(
        self,
        *,
        bucket: str,
        object_path: str,
        base_url: Optional[str] = None,
        expires_in: Optional[int] = None,
    ) -> str:
        resolved_base_url = (base_url or self.settings.supabase_url or "").rstrip("/")
        resolved_api_key = self.settings.supabase_api_key
        resolved_expires_in = expires_in or self.settings.supabase_signed_url_ttl_seconds

        if not resolved_base_url:
            raise MissingConfigurationError(
                "Supabase base URL is missing. Set SUPABASE_URL or expose a storage URL in the document metadata."
            )
        if not resolved_api_key:
            raise MissingConfigurationError(
                "Supabase API key is missing. Set SUPABASE_API_KEY, SUPABASE_ANON_KEY, or SUPABASE_SERVICE_ROLE_KEY."
            )

        encoded_bucket = quote(bucket, safe="")
        encoded_path = quote(object_path.lstrip("/"), safe="/")
        url = f"{resolved_base_url}/storage/v1/object/sign/{encoded_bucket}/{encoded_path}"
        headers = {
            "apikey": resolved_api_key,
            "Authorization": f"Bearer {resolved_api_key}",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                response = await client.post(
                    url,
                    headers=headers,
                    json={"expiresIn": resolved_expires_in},
                )
            except httpx.RequestError as exc:
                raise UpstreamServiceError(
                    "Supabase Storage",
                    f"Supabase signed URL request failed: {exc}",
                ) from exc

        if response.is_error:
            raise UpstreamServiceError(
                "Supabase Storage",
                f"Supabase returned {response.status_code} when creating a signed URL.",
                upstream_status_code=response.status_code,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise UpstreamServiceError(
                "Supabase Storage",
                "Supabase returned invalid JSON when creating a signed URL.",
                upstream_status_code=response.status_code,
            ) from exc

        signed_url = payload.get("signedURL") or payload.get("signedUrl") or payload.get("signed_url")
        if not isinstance(signed_url, str) or not signed_url:
            raise UpstreamServiceError(
                "Supabase Storage",
                "Supabase did not return a signed URL.",
                upstream_status_code=response.status_code,
            )

        if signed_url.startswith("http://") or signed_url.startswith("https://"):
            return signed_url
        return f"{resolved_base_url}{signed_url}"
