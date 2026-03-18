from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CalendarEvent(BaseModel):
    id: str
    calendar_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    all_day: bool = False
    status: Optional[str] = None
    html_link: Optional[str] = None
    source: str = "google_calendar"


class CalendarEventsResponse(BaseModel):
    available: bool
    reason: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    count: int = 0
    items: List[CalendarEvent] = Field(default_factory=list)


class PlannerItem(BaseModel):
    id: str
    kind: str
    title: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    status: Optional[str] = None
    source: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class PlannerResponse(BaseModel):
    generated_at: str
    available_sources: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    count: int = 0
    items: List[PlannerItem] = Field(default_factory=list)
