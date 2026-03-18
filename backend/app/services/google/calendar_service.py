from __future__ import annotations

import asyncio
import logging
from typing import Optional, Sequence

from googleapiclient.discovery import build

from app.core.config import Settings
from app.models.calendar import CalendarEvent, CalendarEventsResponse
from app.services.google.credentials import get_google_credentials
from app.utils.errors import MissingConfigurationError


class GoogleCalendarService:
    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)

    async def get_upcoming_events(
        self,
        *,
        calendar_ids: Optional[Sequence[str]] = None,
        days: Optional[int] = None,
        max_results: Optional[int] = None,
    ) -> CalendarEventsResponse:
        return await self.get_events(
            calendar_ids=calendar_ids,
            days=days,
            max_results=max_results,
        )

    async def get_events(
        self,
        *,
        calendar_ids: Optional[Sequence[str]] = None,
        days: Optional[int] = None,
        max_results: Optional[int] = None,
    ) -> CalendarEventsResponse:
        if not self.settings.google_calendar_enabled:
            return CalendarEventsResponse(
                available=False,
                reason="Google Calendar is disabled. Set GOOGLE_CALENDAR_ENABLED=true to enable it.",
                warnings=[],
                count=0,
                items=[],
            )

        effective_limit = max_results or self.settings.google_max_results

        resolved_calendar_ids = self._resolve_calendar_ids(calendar_ids)
        events: list[CalendarEvent] = []
        warnings: list[str] = []

        for calendar_id in resolved_calendar_ids:
            try:
                raw_items = await asyncio.to_thread(
                    self._fetch_events_sync,
                    calendar_id,
                )
                events.extend(self._normalize_event(calendar_id, item) for item in raw_items)
            except Exception as exc:
                self.logger.warning("Google Calendar fetch failed for %s: %s", calendar_id, exc)
                warnings.append(f"Calendar {calendar_id} could not be loaded.")

        deduped: dict[tuple[str, str | None, str | None], CalendarEvent] = {}
        for event in events:
            key = (event.id, event.start, event.end)
            deduped[key] = event

        items = list(deduped.values())
        items.sort(key=lambda item: (item.start or "", item.title or ""))

        available = bool(items) or not warnings
        reason = None if available else "Google Calendar data is currently unavailable."

        return CalendarEventsResponse(
            available=available,
            reason=reason,
            warnings=warnings,
            count=len(items),
            items=items[:effective_limit],
        )

    def _resolve_calendar_ids(self, extra_calendar_ids: Optional[Sequence[str]]) -> list[str]:
        merged = list(self.settings.google_calendar_ids)
        if extra_calendar_ids:
            merged.extend(extra_calendar_ids)
        if not merged:
            merged = ["primary"]

        seen: list[str] = []
        for calendar_id in merged:
            if calendar_id and calendar_id not in seen:
                seen.append(calendar_id)
        return seen

    def _fetch_events_sync(self, calendar_id: str) -> list[dict]:
        service = self._build_service()
        events: list[dict] = []
        page_token = None

        while True:
            result = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    singleEvents=True,
                    pageToken=page_token,
                )
                .execute()
            )
            events.extend(result.get("items", []))
            page_token = result.get("nextPageToken")
            if not page_token:
                break

        return events

    def _build_service(self):
        try:
            creds = get_google_credentials(self.SCOPES)
        except Exception as exc:
            raise MissingConfigurationError(str(exc)) from exc

        return build("calendar", "v3", credentials=creds, cache_discovery=False)

    def _normalize_event(self, calendar_id: str, item: dict) -> CalendarEvent:
        start_info = item.get("start") or {}
        end_info = item.get("end") or {}
        start = start_info.get("dateTime") or start_info.get("date")
        end = end_info.get("dateTime") or end_info.get("date")
        all_day = "date" in start_info and "dateTime" not in start_info

        return CalendarEvent(
            id=item["id"],
            calendar_id=calendar_id,
            title=item.get("summary"),
            description=item.get("description"),
            location=item.get("location"),
            start=start,
            end=end,
            all_day=all_day,
            status=item.get("status"),
            html_link=item.get("htmlLink"),
        )
