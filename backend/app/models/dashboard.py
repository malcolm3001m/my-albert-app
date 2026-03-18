from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.attendance import AttendanceSummary
from app.models.calendar import CalendarEvent
from app.models.exam import ExamItem
from app.models.profile import Profile


class DashboardAlert(BaseModel):
    id: str
    level: str
    title: str
    message: str


class DashboardSummary(BaseModel):
    course_count: int = 0
    upcoming_exam_count: int = 0
    attendance_overview: Optional[AttendanceSummary] = None
    transcript_count: int = 0


class DashboardResponse(BaseModel):
    profile: Profile
    summary: DashboardSummary
    next_exams: List[ExamItem] = Field(default_factory=list)
    alerts: List[DashboardAlert] = Field(default_factory=list)
    calendar_preview: List[CalendarEvent] = Field(default_factory=list)
