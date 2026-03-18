from fastapi import APIRouter, Depends

from app.api.deps import get_dashboard_service
from app.models.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    dashboard_service: DashboardService = Depends(get_dashboard_service),
) -> DashboardResponse:
    return await dashboard_service.get_dashboard()
