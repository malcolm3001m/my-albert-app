from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.api.deps import get_documents_service, get_supabase_storage_service
from app.models.document import DocumentItem
from app.services.albert.documents_service import DocumentsService
from app.services.supabase_storage_service import SupabaseStorageService
from app.utils.errors import ResourceNotFoundError


router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentItem])
async def get_documents(
    request: Request,
    documents_service: DocumentsService = Depends(get_documents_service),
) -> list[DocumentItem]:
    documents = await documents_service.get_documents()
    return [
        document.model_copy(
            update={
                "download_url": str(
                    request.url_for("download_document", document_id=document.id)
                )
            }
        )
        for document in documents
    ]


@router.get("/{document_id}/download", name="download_document")
async def download_document(
    document_id: str,
    documents_service: DocumentsService = Depends(get_documents_service),
    storage_service: SupabaseStorageService = Depends(get_supabase_storage_service),
) -> RedirectResponse:
    document = await documents_service.get_document(document_id)

    if document.storage_bucket and document.storage_path:
        signed_url = await storage_service.create_signed_url(
            bucket=document.storage_bucket,
            object_path=document.storage_path,
            base_url=document.storage_base_url,
        )
        return RedirectResponse(url=signed_url, status_code=307)

    if document.source_download_url:
        return RedirectResponse(url=document.source_download_url, status_code=307)

    raise ResourceNotFoundError(f"Document {document_id} has no downloadable file.")
