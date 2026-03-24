from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.services.google.credentials import get_google_credentials


router = APIRouter()
logger = logging.getLogger("google_calendar_router")


def _build_calendar_service():
    try:
        credentials = get_google_credentials()
        return build("calendar", "v3", credentials=credentials, cache_discovery=False)
    except Exception as exc:
        logger.exception("Failed to build Google Calendar service")
        raise HTTPException(
            status_code=500,
            detail="Failed to initialize Google Calendar service.",
        ) from exc


def _fetch_calendars_sync() -> list[dict]:
    service = _build_calendar_service()
    try:
        response = service.calendarList().list().execute()
    except HttpError as exc:
        logger.exception("Google Calendar API calendarList call failed")
        raise HTTPException(
            status_code=502,
            detail=f"Google Calendar API failure: {exc}",
        ) from exc

    calendars = []
    for item in response.get("items", []):
        calendars.append(
            {
                "id": item.get("id"),
                "summary": item.get("summary"),
            }
        )
    return calendars


def _fetch_events_sync(
    *,
    time_min: str | None = None,
    time_max: str | None = None,
) -> list[dict]:
    service = _build_calendar_service()
    try:
        events = []
        page_token = None
        while True:
            request_kwargs = {
                "calendarId": "primary",
                "singleEvents": True,
                "orderBy": "startTime",
                "fields": (
                    "nextPageToken,"
                    "items("
                    "id,"
                    "summary,"
                    "start,"
                    "end,"
                    "location,"
                    "attendees(email,displayName,resource,responseStatus,self,organizer)"
                    ")"
                ),
                "pageToken": page_token,
            }
            if time_min:
                request_kwargs["timeMin"] = time_min
            if time_max:
                request_kwargs["timeMax"] = time_max
            response = (
                service.events()
                .list(**request_kwargs)
                .execute()
            )
            events.extend(response.get("items", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break
    except HttpError as exc:
        logger.exception("Google Calendar API events call failed")
        raise HTTPException(
            status_code=502,
            detail=f"Google Calendar API failure: {exc}",
        ) from exc

    serialized_events = []
    for item in events:
        start_info = item.get("start") or {}
        end_info = item.get("end") or {}
        serialized_events.append(
            {
                "id": item.get("id"),
                "summary": item.get("summary"),
                "start": start_info,
                "end": end_info,
                "start_iso": start_info.get("dateTime") or start_info.get("date"),
                "end_iso": end_info.get("dateTime") or end_info.get("date"),
                "location": item.get("location"),
                "attendees": [
                    {
                        "email": attendee.get("email"),
                        "displayName": attendee.get("displayName"),
                        "resource": attendee.get("resource"),
                        "responseStatus": attendee.get("responseStatus"),
                        "self": attendee.get("self"),
                        "organizer": attendee.get("organizer"),
                    }
                    for attendee in item.get("attendees", [])
                ],
            }
        )
    return serialized_events


@router.get("/calendars")
async def get_google_calendars() -> list[dict]:
    return await asyncio.to_thread(_fetch_calendars_sync)


@router.get("/events")
async def get_google_events(
    timeMin: str | None = None,
    timeMax: str | None = None,
) -> list[dict]:
    return await asyncio.to_thread(
        _fetch_events_sync,
        time_min=timeMin,
        time_max=timeMax,
    )
