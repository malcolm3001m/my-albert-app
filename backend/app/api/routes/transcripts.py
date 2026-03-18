from fastapi import APIRouter, Depends

from app.api.deps import get_transcripts_service
from app.models.transcript import TranscriptResponse
from app.services.albert.transcripts_service import TranscriptsService


router = APIRouter(prefix="/transcripts", tags=["transcripts"])


@router.get("", response_model=TranscriptResponse)
async def get_transcripts(
    transcripts_service: TranscriptsService = Depends(get_transcripts_service),
) -> TranscriptResponse:
    return await transcripts_service.get_transcripts()
