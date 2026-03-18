from __future__ import annotations

from app.models.transcript import (
    TranscriptCatchUp,
    TranscriptDocument,
    TranscriptItem,
    TranscriptResponse,
)
from app.services.albert.client import AlbertClient
from app.services.albert.profile_service import ProfileService


class TranscriptsService:
    def __init__(self, client: AlbertClient, profile_service: ProfileService) -> None:
        self.client = client
        self.profile_service = profile_service

    async def get_transcripts(self) -> TranscriptResponse:
        context = await self.profile_service.get_identity_context()
        raw_items = await self.client.get_transcripts(context.user_id)
        items = []
        for item in raw_items:
            items.append(
                TranscriptItem(
                    transcript_id=item["transcript_id"],
                    academic_year=item.get("academic_year"),
                    semester=item.get("semester"),
                    total_ects_earned=item.get("total_ects_earned"),
                    total_ects_possible=item.get("total_ects_possible"),
                    gpa=item.get("gpa"),
                    overall_attendance_rate=item.get("overall_attendance_rate"),
                    validation_status=item.get("validation_status"),
                    status=item.get("status"),
                    generated_at=item.get("generated_at"),
                    to_catch_up=[
                        TranscriptCatchUp(
                            course=catch_up.get("course"),
                            course_name=catch_up.get("course_name"),
                            grade=catch_up.get("grade"),
                            attendance_rate=catch_up.get("attendance_rate"),
                            reason=catch_up.get("reason"),
                        )
                        for catch_up in item.get("to_catch_up", [])
                    ],
                    current_document=TranscriptDocument(
                        document_id=(item.get("current_document") or {}).get("document_id"),
                        file_url=(item.get("current_document") or {}).get("file_url"),
                        document_name=(item.get("current_document") or {}).get("document_name"),
                        version=(item.get("current_document") or {}).get("version"),
                        generation_date=(item.get("current_document") or {}).get("generation_date"),
                    )
                    if item.get("current_document")
                    else None,
                )
            )

        items.sort(key=lambda item: item.generated_at or "", reverse=True)
        return TranscriptResponse(count=len(items), items=items)
