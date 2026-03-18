from fastapi import APIRouter, Depends

from app.api.deps import get_exams_service
from app.models.exam import ExamListResponse
from app.services.albert.exams_service import ExamsService


router = APIRouter(prefix="/exams", tags=["exams"])


@router.get("", response_model=ExamListResponse)
async def get_exams(exams_service: ExamsService = Depends(get_exams_service)) -> ExamListResponse:
    return await exams_service.get_exams()
