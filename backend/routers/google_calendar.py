from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


router = APIRouter()
logger = logging.getLogger("google_calendar_router")

GOOGLE_CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def _get_token_file() -> Path:
    configured = os.getenv("GOOGLE_TOKEN_FILE")
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            path = (Path(__file__).resolve().parents[1] / path).resolve()
        return path
    return (Path(__file__).resolve().parents[1] / ".secrets" / "google_token.json").resolve()


def _load_credentials() -> Credentials:
    token_file = _get_token_file()
    if not token_file.exists():
        logger.error("Google token file not found at %s", token_file)
        raise HTTPException(
            status_code=500,
            detail=f"Google token file not found: {token_file}",
        )

    try:
        credentials = Credentials.from_authorized_user_file(
            str(token_file),
            GOOGLE_CALENDAR_SCOPES,
        )
    except Exception as exc:
        logger.exception("Failed to load Google token file")
        raise HTTPException(
            status_code=500,
            detail="Stored Google token is invalid or unreadable.",
        ) from exc

    if not credentials.valid:
        if credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
                token_file.parent.mkdir(parents=True, exist_ok=True)
                token_file.write_text(credentials.to_json(), encoding="utf-8")
            except Exception as exc:
                logger.exception("Failed to refresh stored Google credentials")
                raise HTTPException(
                    status_code=502,
                    detail="Failed to refresh stored Google credentials.",
                ) from exc
        else:
            logger.error("Stored Google credentials are invalid and cannot be refreshed")
            raise HTTPException(
                status_code=401,
                detail="Stored Google credentials are invalid. Re-run Google OAuth login.",
            )

    return credentials


def _build_calendar_service():
    credentials = _load_credentials()
    try:
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
