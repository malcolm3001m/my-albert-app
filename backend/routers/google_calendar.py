from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

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


def _fetch_events_sync() -> list[dict]:
    service = _build_calendar_service()
    try:
        response = (
            service.events()
            .list(
                calendarId="primary",
                maxResults=20,
                singleEvents=True,
                orderBy="startTime",
                timeMin=datetime.now(timezone.utc).isoformat(),
            )
            .execute()
        )
    except HttpError as exc:
        logger.exception("Google Calendar API events call failed")
        raise HTTPException(
            status_code=502,
            detail=f"Google Calendar API failure: {exc}",
        ) from exc

    events = []
    for item in response.get("items", []):
        start_info = item.get("start") or {}
        end_info = item.get("end") or {}
        events.append(
            {
                "id": item.get("id"),
                "summary": item.get("summary"),
                "start": start_info.get("dateTime") or start_info.get("date"),
                "end": end_info.get("dateTime") or end_info.get("date"),
            }
        )
    return events


@router.get("/calendars")
async def get_google_calendars() -> list[dict]:
    return await asyncio.to_thread(_fetch_calendars_sync)


@router.get("/events")
async def get_google_events() -> list[dict]:
    return await asyncio.to_thread(_fetch_events_sync)
