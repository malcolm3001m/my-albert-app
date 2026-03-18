from fastapi import APIRouter, Depends

from app.api.deps import get_student_service
from app.models.profile import CohortListResponse
from app.services.albert.student_service import StudentService


router = APIRouter(prefix="/cohorts", tags=["cohorts"])


@router.get("", response_model=CohortListResponse)
async def get_cohorts(student_service: StudentService = Depends(get_student_service)) -> CohortListResponse:
    return await student_service.get_cohorts()
