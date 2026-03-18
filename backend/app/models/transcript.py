from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class TranscriptCatchUp(BaseModel):
    course: Optional[str] = None
    course_name: Optional[str] = None
    grade: Optional[float] = None
    attendance_rate: Optional[float] = None
    reason: Optional[str] = None


class TranscriptDocument(BaseModel):
    document_id: Optional[str] = None
    file_url: Optional[str] = None
    document_name: Optional[str] = None
    version: Optional[int] = None
    generation_date: Optional[str] = None


class TranscriptItem(BaseModel):
    transcript_id: str
    academic_year: Optional[str] = None
    semester: Optional[str] = None
    total_ects_earned: Optional[float] = None
    total_ects_possible: Optional[float] = None
    gpa: Optional[float] = None
    overall_attendance_rate: Optional[float] = None
    validation_status: Optional[str] = None
    status: Optional[str] = None
    generated_at: Optional[str] = None
    to_catch_up: List[TranscriptCatchUp] = Field(default_factory=list)
    current_document: Optional[TranscriptDocument] = None


class TranscriptResponse(BaseModel):
    count: int
    items: List[TranscriptItem] = Field(default_factory=list)
