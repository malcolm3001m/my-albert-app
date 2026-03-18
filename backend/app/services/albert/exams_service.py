from __future__ import annotations

from datetime import datetime

from app.models.exam import ExamEnrollment, ExamItem, ExamListResponse
from app.services.albert.client import AlbertClient
from app.services.albert.profile_service import ProfileService


class ExamsService:
    def __init__(self, client: AlbertClient, profile_service: ProfileService) -> None:
        self.client = client
        self.profile_service = profile_service

    async def get_exams(self) -> ExamListResponse:
        context = await self.profile_service.get_identity_context()
        if not context.student_id:
            return ExamListResponse(count=0, upcoming_count=0, items=[])

        raw = await self.client.get_exams(context.student_id)
        raw_items = list((raw or {}).get("exams", []))
        items = [self._normalize_exam(item) for item in raw_items]
        items.sort(key=lambda item: (item.exam_date or "", item.name or ""))
        upcoming_count = sum(1 for item in items if item.is_upcoming)
        return ExamListResponse(count=len(items), upcoming_count=upcoming_count, items=items)

    async def get_upcoming_exams(self, limit: int = 5) -> list[ExamItem]:
        exams = await self.get_exams()
        upcoming = [item for item in exams.items if item.is_upcoming]
        if upcoming:
            return upcoming[:limit]
        return exams.items[:limit]

    def _normalize_exam(self, item: dict) -> ExamItem:
        exam_date = item.get("exam_date")
        is_upcoming = False
        if exam_date:
            try:
                is_upcoming = datetime.fromisoformat(exam_date) >= datetime.utcnow()
            except ValueError:
                is_upcoming = False

        enrollment = item.get("enrollment")
        return ExamItem(
            paper_id=item["paper_id"],
            name=item.get("name"),
            exam_date=exam_date,
            duration_minutes=item.get("duration_minutes"),
            session=item.get("session"),
            exam_status=item.get("exam_status"),
            coefficient=item.get("coefficient"),
            course_module_name=item.get("course_module_name"),
            course_module_code=item.get("course_module_code"),
            academic_year=item.get("academic_year"),
            semester=item.get("semester"),
            enrollment_state=item.get("enrollment_state"),
            can_enroll=item.get("can_enroll"),
            can_withdraw=item.get("can_withdraw"),
            enrollment=ExamEnrollment(**enrollment) if enrollment else None,
            is_upcoming=is_upcoming,
        )
