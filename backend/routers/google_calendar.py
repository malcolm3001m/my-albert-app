from __future__ import annotations

import asyncio
import base64
import logging
from datetime import datetime, timezone
from email.utils import parseaddr, parsedate_to_datetime

from fastapi import APIRouter, HTTPException
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.services.google.credentials import DEFAULT_GOOGLE_SCOPES, get_google_credentials


router = APIRouter()
logger = logging.getLogger("google_calendar_router")


def _build_calendar_service():
    return _build_google_service("calendar", "v3")


def _build_gmail_service():
    return _build_google_service("gmail", "v1")


def _build_drive_service():
    return _build_google_service("drive", "v3")


def _build_google_service(api_name: str, version: str):
    try:
        # TODO: Phase 2 - replace shared env-based Google credentials with per-user OAuth credentials.
        credentials = get_google_credentials(DEFAULT_GOOGLE_SCOPES)
        return build(api_name, version, credentials=credentials, cache_discovery=False)
    except Exception as exc:
        logger.exception("Failed to build Google service %s:%s", api_name, version)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize Google {api_name} service.",
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


def _fetch_gmail_summary_sync() -> dict:
    service = _build_gmail_service()

    try:
        unread_response = (
            service.users()
            .messages()
            .list(userId="me", labelIds=["INBOX", "UNREAD"])
            .execute()
        )
        unread_count = unread_response.get("resultSizeEstimate", 0)

        inbox_response = (
            service.users()
            .messages()
            .list(userId="me", labelIds=["INBOX"], maxResults=5)
            .execute()
        )
        messages = inbox_response.get("messages", [])
    except HttpError as exc:
        logger.exception("Google Gmail API list call failed")
        raise HTTPException(
            status_code=502,
            detail=f"Google Gmail API failure: {exc}",
        ) from exc

    threads = []
    for message_ref in messages:
        message_id = message_ref.get("id")
        if not message_id:
            continue
        try:
            message = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=message_id,
                    format="metadata",
                    metadataHeaders=["Subject", "From"],
                )
                .execute()
            )
        except HttpError as exc:
            logger.warning("Google Gmail API get call failed for %s: %s", message_id, exc)
            continue

        payload = message.get("payload") or {}
        headers = payload.get("headers") or []
        subject = _header_value(headers, "Subject")
        sender = _sender_name(_header_value(headers, "From"))
        internal_date = _internal_date_to_iso(message.get("internalDate"))
        label_ids = set(message.get("labelIds", []))

        threads.append(
            {
                "id": message.get("threadId") or message_id,
                "subject": subject,
                "sender": sender,
                "snippet": message.get("snippet"),
                "date": internal_date,
                "unread": "UNREAD" in label_ids,
            }
        )

    return {
        "unread_count": unread_count,
        "threads": threads,
    }


def _fetch_gmail_thread_sync(thread_id: str) -> dict:
    service = _build_gmail_service()

    try:
        thread = (
            service.users()
            .threads()
            .get(userId="me", id=thread_id, format="full")
            .execute()
        )
    except HttpError as exc:
        logger.exception("Google Gmail API thread get call failed for %s", thread_id)
        raise HTTPException(
            status_code=502,
            detail=f"Google Gmail API failure: {exc}",
        ) from exc

    messages = thread.get("messages", [])
    subject = None
    if messages:
        first_headers = (messages[0].get("payload") or {}).get("headers") or []
        subject = _header_value(first_headers, "Subject")

    normalized_messages = []
    for message in messages:
        payload = message.get("payload") or {}
        headers = payload.get("headers") or []
        body_text, body_html = _extract_message_bodies(payload)

        normalized_messages.append(
            {
                "id": message.get("id"),
                "sender": _header_value(headers, "From"),
                "date": _message_date_to_iso(
                    _header_value(headers, "Date"),
                    message.get("internalDate"),
                ),
                "body_text": body_text,
                "body_html": body_html,
            }
        )

    return {
        "id": thread.get("id") or thread_id,
        "subject": subject,
        "messages": normalized_messages,
    }


def _fetch_drive_recent_sync() -> list[dict]:
    service = _build_drive_service()
    try:
        response = (
            service.files()
            .list(
                q="mimeType contains 'google-apps' and trashed = false",
                orderBy="modifiedTime desc",
                pageSize=5,
                fields="files(id,name,mimeType,modifiedTime,webViewLink,iconLink)",
            )
            .execute()
        )
    except HttpError as exc:
        logger.exception("Google Drive API list call failed")
        raise HTTPException(
            status_code=502,
            detail=f"Google Drive API failure: {exc}",
        ) from exc

    items = []
    for file_item in response.get("files", []):
        items.append(
            {
                "id": file_item.get("id"),
                "title": file_item.get("name"),
                "url": file_item.get("webViewLink"),
                "mime_type": file_item.get("mimeType"),
                "modified_time": file_item.get("modifiedTime"),
                "icon_url": file_item.get("iconLink"),
            }
        )
    return items


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


def _header_value(headers: list[dict], name: str) -> str | None:
    lowered = name.lower()
    for header in headers:
        if str(header.get("name", "")).lower() == lowered:
            value = header.get("value")
            if isinstance(value, str):
                return value
    return None


def _sender_name(from_header: str | None) -> str | None:
    if not from_header:
        return None
    name, address = parseaddr(from_header)
    return name or address or from_header


def _internal_date_to_iso(internal_date: str | None) -> str | None:
    if not internal_date:
        return None
    try:
        timestamp = int(internal_date) / 1000
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _message_date_to_iso(date_header: str | None, internal_date: str | None) -> str | None:
    if date_header:
        try:
            parsed = parsedate_to_datetime(date_header)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except (TypeError, ValueError, IndexError):
            pass
    return _internal_date_to_iso(internal_date)


def _extract_message_bodies(payload: dict) -> tuple[str | None, str | None]:
    text_parts: list[str] = []
    html_parts: list[str] = []
    _walk_mime_parts(payload, text_parts, html_parts)
    body_text = "\n".join(part for part in text_parts if part).strip() or None
    body_html = "\n".join(part for part in html_parts if part).strip() or None
    return body_text, body_html


def _walk_mime_parts(payload: dict, text_parts: list[str], html_parts: list[str]) -> None:
    mime_type = payload.get("mimeType")
    body = payload.get("body") or {}
    data = body.get("data")
    decoded = _decode_message_body(data)

    if mime_type == "text/plain" and decoded:
        text_parts.append(decoded)
    elif mime_type == "text/html" and decoded:
        html_parts.append(decoded)

    for part in payload.get("parts", []) or []:
        if isinstance(part, dict):
            _walk_mime_parts(part, text_parts, html_parts)


def _decode_message_body(data: str | None) -> str | None:
    if not data:
        return None
    try:
        padded = data + "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8", errors="replace")
    except (ValueError, TypeError):
        return None


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


@router.get("/gmail")
async def get_google_gmail() -> dict:
    return await asyncio.to_thread(_fetch_gmail_summary_sync)


@router.get("/gmail/{thread_id}")
async def get_google_gmail_thread(thread_id: str) -> dict:
    return await asyncio.to_thread(_fetch_gmail_thread_sync, thread_id)


@router.get("/drive/recent")
async def get_google_drive_recent() -> list[dict]:
    return await asyncio.to_thread(_fetch_drive_recent_sync)
