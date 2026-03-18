from fastapi import APIRouter, Depends

from app.api.deps import get_attendance_service
from app.models.attendance import AttendanceResponse
from app.services.albert.attendance_service import AttendanceService


router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.get("", response_model=AttendanceResponse)
async def get_attendance(
    attendance_service: AttendanceService = Depends(get_attendance_service),
) -> AttendanceResponse:
    return await attendance_service.get_attendance()
