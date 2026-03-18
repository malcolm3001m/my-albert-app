from fastapi import APIRouter, Depends, Query

from app.api.deps import get_calendar_service, get_student_service
from app.models.calendar import CalendarEventsResponse
from app.services.albert.student_service import StudentService
from app.services.google.calendar_service import GoogleCalendarService


router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/events", response_model=CalendarEventsResponse)
async def get_calendar_events(
    days: int = Query(default=14, ge=1, le=90),
    limit: int = Query(default=20, ge=1, le=100),
    student_service: StudentService = Depends(get_student_service),
    calendar_service: GoogleCalendarService = Depends(get_calendar_service),
) -> CalendarEventsResponse:
    warning = None
    try:
        calendar_ids = await student_service.get_cohort_calendar_ids()
    except Exception:
        calendar_ids = []
        warning = "Albert cohort calendar IDs could not be loaded."

    response = await calendar_service.get_upcoming_events(
        calendar_ids=calendar_ids,
        days=days,
        max_results=limit,
    )
    if warning and warning not in response.warnings:
        response.warnings.append(warning)
    return response
