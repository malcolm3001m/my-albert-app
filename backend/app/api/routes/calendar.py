from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.services.google.credentials import get_google_credentials


router = APIRouter(prefix="/calendar", tags=["calendar"])
logger = logging.getLogger("calendar_api")

GOOGLE_CALENDAR_LIST_URL = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
GOOGLE_EVENTS_URL_TEMPLATE = "https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
TARGET_CALENDAR_SUMMARY = "Malcolm Morgan"


def _build_calendar_service():
    try:
        credentials = get_google_credentials()
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


@router.get("/events")
async def get_calendar_events() -> list[dict]:
    service = _build_calendar_service()

    try:
        calendar_list = service.calendarList().list().execute()
    except HttpError as exc:
        logger.exception("Google Calendar API calendarList call failed")
        raise HTTPException(status_code=502, detail=f"Google API error: {exc}") from exc
    calendar_id = _find_calendar_id(calendar_list)

    time_min = datetime.now(timezone.utc).isoformat()
    try:
        events_response = (
            service.events()
            .list(
                calendarId=calendar_id,
                maxResults=30,
                singleEvents=True,
                orderBy="startTime",
                timeMin=time_min,
            )
            .execute()
        )
    except HttpError as exc:
        logger.exception("Google Calendar API events call failed")
        raise HTTPException(status_code=502, detail=f"Google API error: {exc}") from exc

    logger.info("Fetched Google Calendar events for calendarId=%s", calendar_id)
    return [_simplify_event(event) for event in events_response.get("items", [])]
