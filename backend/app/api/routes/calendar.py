from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.api.deps import get_supabase_user_tokens_service
from app.services.google.credentials import build_google_credentials
from app.services.supabase_user_tokens_service import SupabaseUserTokensService


router = APIRouter(prefix="/calendar", tags=["calendar"])
logger = logging.getLogger("calendar_api")
TARGET_CALENDAR_SUMMARY = "Malcolm Morgan"


def _build_calendar_service(refresh_token: str):
    try:
        credentials = build_google_credentials(refresh_token)
        return build("calendar", "v3", credentials=credentials, cache_discovery=False)
    except Exception as exc:
        logger.exception("Failed to initialize Google Calendar service")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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


def _fetch_all_events(service, calendar_id: str) -> list[dict]:
    events: list[dict] = []
    page_token = None

    while True:
        response = (
            service.events()
            .list(
                calendarId=calendar_id,
                singleEvents=True,
                pageToken=page_token,
            )
            .execute()
        )
        events.extend(response.get("items", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return events


@router.get("/events")
async def get_calendar_events(
    request: Request,
    user_tokens_service: SupabaseUserTokensService = Depends(get_supabase_user_tokens_service),
) -> list[dict]:
    authenticated_user = getattr(request.state, "authenticated_user", None)
    user_id = getattr(authenticated_user, "user_id", None)
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    refresh_token = await user_tokens_service.get_google_refresh_token(user_id)
    if not refresh_token:
        return []

    service = _build_calendar_service(refresh_token)

    try:
        calendar_list = service.calendarList().list().execute()
    except HttpError as exc:
        logger.exception("Google Calendar API calendarList call failed")
        raise HTTPException(status_code=502, detail=f"Google API error: {exc}") from exc
    calendar_id = _find_calendar_id(calendar_list)

    try:
        events = _fetch_all_events(service, calendar_id)
    except HttpError as exc:
        logger.exception("Google Calendar API events call failed")
        raise HTTPException(status_code=502, detail=f"Google API error: {exc}") from exc

    logger.info("Fetched Google Calendar events for calendarId=%s", calendar_id)
    return [_simplify_event(event) for event in events]
