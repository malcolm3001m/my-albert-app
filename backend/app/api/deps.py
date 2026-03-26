from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from app.core.config import Settings
from app.services.albert.attendance_service import AttendanceService
from app.services.albert.client import AlbertClient
from app.services.albert.courses_service import CoursesService
from app.services.albert.documents_service import DocumentsService
from app.services.albert.exams_service import ExamsService
from app.services.albert.grades_service import GradesService
from app.services.albert.profile_service import ProfileService
from app.services.albert.student_service import StudentService
from app.services.albert.transcripts_service import TranscriptsService
from app.services.dashboard_service import DashboardService
from app.services.google.calendar_service import GoogleCalendarService
from app.services.planner_service import PlannerService
from app.services.supabase_storage_service import SupabaseStorageService


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_albert_client(request: Request) -> AlbertClient:
    token = request.headers.get("X-Albert-Token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Albert token required",
        )
    return request.app.state.albert_client.with_bearer_token(token)


def get_calendar_service(request: Request) -> GoogleCalendarService:
    return request.app.state.calendar_service


def get_supabase_storage_service(
    settings: Settings = Depends(get_settings),
) -> SupabaseStorageService:
    return SupabaseStorageService(settings)


def get_profile_service(client: AlbertClient = Depends(get_albert_client)) -> ProfileService:
    return ProfileService(client)


def get_student_service(
    client: AlbertClient = Depends(get_albert_client),
    profile_service: ProfileService = Depends(get_profile_service),
) -> StudentService:
    return StudentService(client, profile_service)


def get_courses_service(
    client: AlbertClient = Depends(get_albert_client),
    profile_service: ProfileService = Depends(get_profile_service),
) -> CoursesService:
    return CoursesService(client, profile_service)


def get_documents_service(
    client: AlbertClient = Depends(get_albert_client),
    courses_service: CoursesService = Depends(get_courses_service),
) -> DocumentsService:
    return DocumentsService(client, courses_service)


def get_exams_service(
    client: AlbertClient = Depends(get_albert_client),
    profile_service: ProfileService = Depends(get_profile_service),
) -> ExamsService:
    return ExamsService(client, profile_service)


def get_attendance_service(
    client: AlbertClient = Depends(get_albert_client),
    profile_service: ProfileService = Depends(get_profile_service),
) -> AttendanceService:
    return AttendanceService(client, profile_service)


def get_transcripts_service(
    client: AlbertClient = Depends(get_albert_client),
    profile_service: ProfileService = Depends(get_profile_service),
) -> TranscriptsService:
    return TranscriptsService(client, profile_service)


def get_grades_service(
    client: AlbertClient = Depends(get_albert_client),
    profile_service: ProfileService = Depends(get_profile_service),
) -> GradesService:
    return GradesService(client, profile_service)


def get_dashboard_service(
    profile_service: ProfileService = Depends(get_profile_service),
    student_service: StudentService = Depends(get_student_service),
    courses_service: CoursesService = Depends(get_courses_service),
    exams_service: ExamsService = Depends(get_exams_service),
    attendance_service: AttendanceService = Depends(get_attendance_service),
    transcripts_service: TranscriptsService = Depends(get_transcripts_service),
    grades_service: GradesService = Depends(get_grades_service),
    calendar_service: GoogleCalendarService = Depends(get_calendar_service),
) -> DashboardService:
    return DashboardService(
        profile_service=profile_service,
        student_service=student_service,
        courses_service=courses_service,
        exams_service=exams_service,
        attendance_service=attendance_service,
        transcripts_service=transcripts_service,
        grades_service=grades_service,
        calendar_service=calendar_service,
    )


def get_planner_service(
    settings: Settings = Depends(get_settings),
    student_service: StudentService = Depends(get_student_service),
    exams_service: ExamsService = Depends(get_exams_service),
    calendar_service: GoogleCalendarService = Depends(get_calendar_service),
) -> PlannerService:
    return PlannerService(
        settings=settings,
        student_service=student_service,
        exams_service=exams_service,
        calendar_service=calendar_service,
    )
