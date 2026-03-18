from fastapi import APIRouter, Depends

from app.api.deps import get_student_service
from app.models.profile import IntakeResponse
from app.services.albert.student_service import StudentService


router = APIRouter(prefix="/intake", tags=["intake"])


@router.get("", response_model=IntakeResponse)
async def get_intake(student_service: StudentService = Depends(get_student_service)) -> IntakeResponse:
    return IntakeResponse(intake=await student_service.get_intake())
