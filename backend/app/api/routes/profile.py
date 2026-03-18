from fastapi import APIRouter, Depends

from app.api.deps import get_profile_service
from app.models.profile import ProfileResponse
from app.services.albert.profile_service import ProfileService


router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileResponse)
async def get_profile(profile_service: ProfileService = Depends(get_profile_service)) -> ProfileResponse:
    return ProfileResponse(profile=await profile_service.get_profile())
