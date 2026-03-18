from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException

from app.core.config import get_settings


router = APIRouter(prefix="/calendar", tags=["calendar"])
logger = logging.getLogger("calendar_api")

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_LIST_URL = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
GOOGLE_EVENTS_URL_TEMPLATE = "https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
TARGET_CALENDAR_SUMMARY = "Malcolm Morgan"


def _load_google_token_data() -> dict:
    settings = get_settings()
    token_path = settings.google_token_path

    if not token_path.exists():
        logger.error("Google token file not found at %s", token_path)
        raise HTTPException(
            status_code=500,
            detail=f"Google token file not found: {token_path}",
        )

    try:
        return json.loads(token_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger.exception("Google token file contains invalid JSON")
        raise HTTPException(
            status_code=500,
            detail="google_token.json contains invalid JSON.",
        ) from exc
    except OSError as exc:
        logger.exception("Google token file could not be read")
        raise HTTPException(
            status_code=500,
            detail="google_token.json could not be read.",
        ) from exc


def _extract_refresh_payload(token_data: dict) -> dict[str, str]:
    refresh_token = token_data.get("refresh_token")
    client_id = token_data.get("client_id")
    client_secret = token_data.get("client_secret")
    token_uri = token_data.get("token_uri") or GOOGLE_TOKEN_URL

    if not refresh_token:
        raise HTTPException(status_code=500, detail="Refresh token missing in google_token.json.")
    if not client_id:
        raise HTTPException(status_code=500, detail="client_id missing in google_token.json.")
    if not client_secret:
        raise HTTPException(status_code=500, detail="client_secret missing in google_token.json.")

    return {
        "token_uri": token_uri,
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
    }


async def _refresh_google_access_token(token_data: dict) -> str:
    refresh_payload = _extract_refresh_payload(token_data)
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_payload["refresh_token"],
        "client_id": refresh_payload["client_id"],
        "client_secret": refresh_payload["client_secret"],
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(refresh_payload["token_uri"], data=payload)

    if response.status_code != 200:
        logger.error(
            "Google token refresh failed: status=%s body=%s",
            response.status_code,
            response.text,
        )
        raise HTTPException(
            status_code=502,
            detail=f"Google token refresh failed: {response.text}",
        )

    try:
        token_response = response.json()
    except ValueError as exc:
        logger.exception("Google token refresh returned invalid JSON")
        raise HTTPException(
            status_code=502,
            detail="Google token refresh returned invalid JSON.",
        ) from exc

    access_token = token_response.get("access_token")
    if not access_token:
        logger.error("Google token refresh response missing access_token")
        raise HTTPException(
            status_code=502,
            detail="Google token refresh response missing access_token.",
        )

    return access_token


async def _fetch_google_json(
    url: str,
    *,
    access_token: str,
    params: dict | None = None,
) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=headers, params=params)

    if response.status_code != 200:
        logger.error(
            "Google API request failed: url=%s status=%s body=%s",
            url,
            response.status_code,
            response.text,
        )
        raise HTTPException(
            status_code=502,
            detail=f"Google API error: {response.text}",
        )

    try:
        return response.json()
    except ValueError as exc:
        logger.exception("Google API returned invalid JSON")
        raise HTTPException(
            status_code=502,
            detail="Google API returned invalid JSON.",
        ) from exc


def _find_calendar_id(calendar_list: dict) -> str:
    for calendar in calendar_list.get("items", []):
        if calendar.get("summary") == TARGET_CALENDAR_SUMMARY:
            calendar_id = calendar.get("id")
            if calendar_id:
                return calendar_id

    logger.error("Calendar with summary '%s' not found", TARGET_CALENDAR_SUMMARY)
    raise HTTPException(
        status_code=404,
        detail=f"Google Calendar '{TARGET_CALENDAR_SUMMARY}' not found.",
    )


def _simplify_event(event: dict) -> dict:
    start_info = event.get("start") or {}
    end_info = event.get("end") or {}
    return {
        "title": event.get("summary", ""),
        "start": start_info.get("dateTime") or start_info.get("date"),
        "end": end_info.get("dateTime") or end_info.get("date"),
        "location": event.get("location"),
        "description": event.get("description"),
    }


@router.get("/events")
async def get_calendar_events() -> list[dict]:
    token_data = _load_google_token_data()
    access_token = await _refresh_google_access_token(token_data)

    calendar_list = await _fetch_google_json(
        GOOGLE_CALENDAR_LIST_URL,
        access_token=access_token,
    )
    calendar_id = _find_calendar_id(calendar_list)

    time_min = datetime.now(timezone.utc).isoformat()
    events_url = GOOGLE_EVENTS_URL_TEMPLATE.format(calendar_id=calendar_id)
    events_response = await _fetch_google_json(
        events_url,
        access_token=access_token,
        params={
            "maxResults": 30,
            "singleEvents": "true",
            "orderBy": "startTime",
            "timeMin": time_min,
        },
    )

    logger.info("Fetched Google Calendar events for calendarId=%s", calendar_id)
    return [_simplify_event(event) for event in events_response.get("items", [])]
