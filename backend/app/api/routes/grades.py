from fastapi import APIRouter, Depends

from app.api.deps import get_grades_service
from app.models.exam import GradesResponse
from app.services.albert.grades_service import GradesService


router = APIRouter(prefix="/grades", tags=["grades"])


@router.get("", response_model=GradesResponse)
async def get_grades(grades_service: GradesService = Depends(get_grades_service)) -> GradesResponse:
    return await grades_service.get_grades()
