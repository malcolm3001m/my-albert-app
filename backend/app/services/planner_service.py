from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from app.core.config import Settings
from app.models.calendar import PlannerItem, PlannerResponse
from app.services.albert.exams_service import ExamsService
from app.services.albert.student_service import StudentService
from app.services.google.calendar_service import GoogleCalendarService


class PlannerService:
    def __init__(
        self,
        settings: Settings,
        student_service: StudentService,
        exams_service: ExamsService,
        calendar_service: GoogleCalendarService,
    ) -> None:
        self.settings = settings
        self.student_service = student_service
        self.exams_service = exams_service
        self.calendar_service = calendar_service

    async def get_planner(self) -> PlannerResponse:
        warnings: list[str] = []
        available_sources: list[str] = []
        calendar_ids: list[str] = []

        try:
            calendar_ids = await self.student_service.get_cohort_calendar_ids()
        except Exception:
            warnings.append("Albert cohort calendar IDs could not be loaded.")

        exams_task = self.exams_service.get_upcoming_exams(limit=25)
        calendar_task = self.calendar_service.get_upcoming_events(
            calendar_ids=calendar_ids,
            days=self.settings.planner_lookahead_days,
            max_results=50,
        )

        exams_result, calendar_result = await asyncio.gather(
            exams_task,
            calendar_task,
            return_exceptions=True,
        )

        items: list[PlannerItem] = []

        if isinstance(exams_result, Exception):
            warnings.append("Albert exams could not be loaded.")
        else:
            available_sources.append("albert_exams")
            for exam in exams_result:
                end = exam.exam_date
                if exam.exam_date and exam.duration_minutes:
                    try:
                        start_dt = datetime.fromisoformat(exam.exam_date)
                        end = (start_dt + timedelta(minutes=exam.duration_minutes)).isoformat()
                    except ValueError:
                        end = exam.exam_date

                items.append(
                    PlannerItem(
                        id=f"exam:{exam.paper_id}",
                        kind="exam",
                        title=exam.name or exam.course_module_name,
                        start=exam.exam_date,
                        end=end,
                        status=exam.exam_status,
                        source="albert",
                        payload=exam.model_dump(),
                    )
                )

        if isinstance(calendar_result, Exception):
            warnings.append("Google Calendar events could not be loaded.")
        else:
            if calendar_result.available:
                available_sources.append("google_calendar")
            elif calendar_result.reason:
                warnings.append(calendar_result.reason)

            warnings.extend(calendar_result.warnings)
            for event in calendar_result.items:
                items.append(
                    PlannerItem(
                        id=f"calendar:{event.id}",
                        kind="calendar_event",
                        title=event.title,
                        start=event.start,
                        end=event.end,
                        status=event.status,
                        source="google_calendar",
                        payload=event.model_dump(),
                    )
                )

        items.sort(key=lambda item: (item.start or "", item.title or ""))
        generated_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        return PlannerResponse(
            generated_at=generated_at,
            available_sources=available_sources,
            warnings=list(dict.fromkeys(warnings)),
            count=len(items),
            items=items,
        )
