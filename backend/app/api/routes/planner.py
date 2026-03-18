from fastapi import APIRouter, Depends

from app.api.deps import get_planner_service
from app.models.calendar import PlannerResponse
from app.services.planner_service import PlannerService


router = APIRouter(prefix="/planner", tags=["planner"])


@router.get("", response_model=PlannerResponse)
async def get_planner(
    planner_service: PlannerService = Depends(get_planner_service),
) -> PlannerResponse:
    return await planner_service.get_planner()
