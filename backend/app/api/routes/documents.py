from fastapi import APIRouter, Depends

from app.api.deps import get_documents_service
from app.models.document import DocumentItem
from app.services.albert.documents_service import DocumentsService


router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentItem])
async def get_documents(
    documents_service: DocumentsService = Depends(get_documents_service),
) -> list[DocumentItem]:
    return await documents_service.get_documents()
