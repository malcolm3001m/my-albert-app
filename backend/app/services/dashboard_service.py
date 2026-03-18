from __future__ import annotations

import asyncio

from app.models.dashboard import DashboardAlert, DashboardResponse, DashboardSummary
from app.services.albert.attendance_service import AttendanceService
from app.services.albert.courses_service import CoursesService
from app.services.albert.exams_service import ExamsService
from app.services.albert.grades_service import GradesService
from app.services.albert.profile_service import ProfileService
from app.services.albert.student_service import StudentService
from app.services.albert.transcripts_service import TranscriptsService
from app.services.google.calendar_service import GoogleCalendarService


class DashboardService:
    def __init__(
        self,
        profile_service: ProfileService,
        student_service: StudentService,
        courses_service: CoursesService,
        exams_service: ExamsService,
        attendance_service: AttendanceService,
        transcripts_service: TranscriptsService,
        grades_service: GradesService,
        calendar_service: GoogleCalendarService,
    ) -> None:
        self.profile_service = profile_service
        self.student_service = student_service
        self.courses_service = courses_service
        self.exams_service = exams_service
        self.attendance_service = attendance_service
        self.transcripts_service = transcripts_service
        self.grades_service = grades_service
        self.calendar_service = calendar_service

    async def get_dashboard(self) -> DashboardResponse:
        profile = await self.profile_service.get_profile()
        alerts: list[DashboardAlert] = []

        cohort_calendar_ids: list[str] = []
        try:
            cohort_calendar_ids = await self.student_service.get_cohort_calendar_ids()
        except Exception:
            alerts.append(
                DashboardAlert(
                    id="cohort-calendar-ids-unavailable",
                    level="warning",
                    title="Calendar source incomplete",
                    message="Albert cohort calendar IDs could not be resolved.",
                )
            )

        results = await asyncio.gather(
            self.courses_service.get_courses(),
            self.exams_service.get_upcoming_exams(limit=5),
            self.attendance_service.get_attendance(),
            self.transcripts_service.get_transcripts(),
            self.grades_service.get_grades(),
            self.calendar_service.get_upcoming_events(calendar_ids=cohort_calendar_ids, max_results=5),
            return_exceptions=True,
        )

        courses_result, exams_result, attendance_result, transcripts_result, grades_result, calendar_result = results

        course_count = 0
        next_exams = []
        attendance_overview = None
        transcript_count = 0
        calendar_preview = []

        if isinstance(courses_result, Exception):
            alerts.append(
                DashboardAlert(
                    id="courses-unavailable",
                    level="warning",
                    title="Courses unavailable",
                    message="Course data could not be loaded from Albert.",
                )
            )
        else:
            course_count = courses_result.count

        if isinstance(exams_result, Exception):
            alerts.append(
                DashboardAlert(
                    id="exams-unavailable",
                    level="warning",
                    title="Exams unavailable",
                    message="Upcoming exams could not be loaded from Albert.",
                )
            )
        else:
            next_exams = exams_result

        if isinstance(attendance_result, Exception):
            alerts.append(
                DashboardAlert(
                    id="attendance-unavailable",
                    level="warning",
                    title="Attendance unavailable",
                    message="Attendance data could not be loaded from Albert.",
                )
            )
        else:
            attendance_overview = attendance_result.summary
            if (
                attendance_overview.attendance_rate is not None
                and attendance_overview.attendance_rate < 90
            ):
                alerts.append(
                    DashboardAlert(
                        id="attendance-low",
                        level="info",
                        title="Attendance below target",
                        message="Your current attendance rate is below 90%.",
                    )
                )

        if isinstance(transcripts_result, Exception):
            alerts.append(
                DashboardAlert(
                    id="transcripts-unavailable",
                    level="warning",
                    title="Transcripts unavailable",
                    message="Transcript data could not be loaded from Albert.",
                )
            )
        else:
            transcript_count = transcripts_result.count

        if not isinstance(grades_result, Exception) and not grades_result.available:
            alerts.append(
                DashboardAlert(
                    id="grades-unavailable",
                    level="warning",
                    title="Grades unavailable",
                    message=grades_result.reason or "Albert grades are temporarily unavailable.",
                )
            )

        if isinstance(calendar_result, Exception):
            alerts.append(
                DashboardAlert(
                    id="calendar-unavailable",
                    level="warning",
                    title="Calendar unavailable",
                    message="Google Calendar events could not be loaded.",
                )
            )
        else:
            calendar_preview = calendar_result.items[:5]
            if not calendar_result.available:
                alerts.append(
                    DashboardAlert(
                        id="calendar-disabled",
                        level="info",
                        title="Calendar not connected",
                        message=calendar_result.reason or "Google Calendar is not currently available.",
                    )
                )

        summary = DashboardSummary(
            course_count=course_count,
            upcoming_exam_count=len(next_exams),
            attendance_overview=attendance_overview,
            transcript_count=transcript_count,
        )

        return DashboardResponse(
            profile=profile,
            summary=summary,
            next_exams=next_exams,
            alerts=alerts,
            calendar_preview=calendar_preview,
        )
