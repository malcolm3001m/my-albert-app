from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ExamEnrollment(BaseModel):
    enrollment_id: Optional[str] = None
    enrollment_status: Optional[str] = None
    enrollment_type: Optional[str] = None
    exam_location: Optional[str] = None
    seat_assignment: Optional[str] = None
    has_accommodations: Optional[bool] = None
    extended_time_percent: Optional[int] = None


class ExamItem(BaseModel):
    paper_id: str
    name: Optional[str] = None
    exam_date: Optional[str] = None
    duration_minutes: Optional[int] = None
    session: Optional[int] = None
    exam_status: Optional[str] = None
    coefficient: Optional[float] = None
    course_module_name: Optional[str] = None
    course_module_code: Optional[str] = None
    academic_year: Optional[int] = None
    semester: Optional[str] = None
    enrollment_state: Optional[str] = None
    can_enroll: Optional[bool] = None
    can_withdraw: Optional[bool] = None
    enrollment: Optional[ExamEnrollment] = None
    is_upcoming: bool = False


class ExamListResponse(BaseModel):
    count: int
    upcoming_count: int
    items: List[ExamItem] = Field(default_factory=list)


class GradeSummary(BaseModel):
    total_count: int = 0
    numeric_count: int = 0
    average_grade: Optional[float] = None


class GradeItem(BaseModel):
    id: str
    exam_id: Optional[str] = None
    exam_paper_id: Optional[str] = None
    session: Optional[int] = None
    grade: Optional[float] = None
    grade_status: Optional[str] = None
    counts_in_average: Optional[bool] = None
    comment_for_student: Optional[str] = None
    exam_name: Optional[str] = None
    exam_date: Optional[str] = None
    course_module_code: Optional[str] = None
    course_module_name: Optional[str] = None
    academic_year: Optional[int] = None
    semester: Optional[str] = None
    exam_status: Optional[str] = None
    statistics_average: Optional[float] = None
    statistics_min: Optional[float] = None
    statistics_max: Optional[float] = None


class GradesResponse(BaseModel):
    available: bool
    reason: Optional[str] = None
    summary: Optional[GradeSummary] = None
    items: Optional[List[GradeItem]] = None
