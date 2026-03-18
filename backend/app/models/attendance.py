from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class AttendanceItem(BaseModel):
    attendance_id: str
    course_module_instance_id: Optional[int] = None
    course_name: Optional[str] = None
    course_code: Optional[str] = None
    present: bool
    exemption: bool = False
    manual_override: bool = False
    session_id: Optional[int] = None
    session_summary: Optional[str] = None
    session_start: Optional[str] = None
    session_end: Optional[str] = None
    updated_at: Optional[str] = None


class AttendanceSummary(BaseModel):
    total_sessions: int = 0
    present_count: int = 0
    absent_count: int = 0
    exempt_count: int = 0
    attendance_rate: Optional[float] = None


class AttendanceResponse(BaseModel):
    summary: AttendanceSummary
    items: List[AttendanceItem] = Field(default_factory=list)
