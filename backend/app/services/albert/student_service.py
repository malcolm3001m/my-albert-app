from __future__ import annotations

from app.models.profile import (
    CohortCampus,
    CohortItem,
    CohortListResponse,
    CohortProgram,
    EmergencyContact,
    Intake,
    IntakeAddress,
    IntakeDocumentStatus,
)
from app.services.albert.client import AlbertClient
from app.services.albert.profile_service import ProfileService


class StudentService:
    def __init__(self, client: AlbertClient, profile_service: ProfileService) -> None:
        self.client = client
        self.profile_service = profile_service

    async def get_cohorts(self) -> CohortListResponse:
        context = await self.profile_service.get_identity_context()
        raw_items = await self.client.get_cohorts(context.user_id)
        items = [
            CohortItem(
                id=item["id"],
                name=item.get("name"),
                year=item.get("year"),
                semester=item.get("semester"),
                google_calendar_id=item.get("google_calendar_id"),
                campus=CohortCampus(**item["campus"]) if item.get("campus") else None,
                academic_program_instance=CohortProgram(**item["academic_program_instance"])
                if item.get("academic_program_instance")
                else None,
            )
            for item in raw_items
        ]
        items.sort(key=lambda item: ((item.year or 0), item.semester or "", item.id), reverse=True)
        return CohortListResponse(count=len(items), items=items)

    async def get_cohort_calendar_ids(self) -> list[str]:
        cohorts = await self.get_cohorts()
        seen: list[str] = []
        for cohort in cohorts.items:
            if cohort.google_calendar_id and cohort.google_calendar_id not in seen:
                seen.append(cohort.google_calendar_id)
        return seen

    async def get_intake(self) -> Intake:
        raw = await self.client.get_intake()
        documents = {
            "cvec": IntakeDocumentStatus(
                status=raw.get("cvec_document_status"),
                validated_at=raw.get("cvec_document_validated_at"),
                comment=raw.get("cvec_document_comment"),
                url=raw.get("cvec_document_url"),
            ),
            "id_document": IntakeDocumentStatus(
                status=raw.get("id_document_status"),
                validated_at=raw.get("id_document_validated_at"),
                comment=raw.get("id_document_comment"),
                url=raw.get("id_document_url"),
            ),
            "picture": IntakeDocumentStatus(
                status=raw.get("picture_status"),
                validated_at=raw.get("picture_validated_at"),
                comment=raw.get("picture_comment"),
                url=raw.get("picture_url"),
            ),
            "civil_liability_certificate": IntakeDocumentStatus(
                status=raw.get("civil_liability_certificate_status"),
                validated_at=raw.get("civil_liability_certificate_validated_at"),
                comment=raw.get("civil_liability_certificate_comment"),
                url=raw.get("civil_liability_certificate_url"),
            ),
            "last_diploma": IntakeDocumentStatus(
                status=raw.get("last_diploma_status"),
                validated_at=raw.get("last_diploma_validated_at"),
                comment=raw.get("last_diploma_comment"),
                url=raw.get("last_diploma_url"),
            ),
        }
        return Intake(
            student_id=raw.get("student_id"),
            academic_year=raw.get("academic_year"),
            school=raw.get("school"),
            form_version=raw.get("form_version"),
            status=raw.get("status"),
            personal_email=raw.get("personal_email"),
            phone_number=raw.get("phone_number"),
            birthday=raw.get("birthday"),
            city_of_birth=raw.get("city_of_birth"),
            country_of_birth=raw.get("country_of_birth"),
            nationality=raw.get("nationality"),
            gender_at_birth=raw.get("gender_at_birth"),
            level_of_class=raw.get("level_of_class"),
            general_information=raw.get("general_information"),
            address=IntakeAddress(
                street=raw.get("address"),
                city=raw.get("address_city"),
                zip_code=raw.get("address_zip_code"),
                country=raw.get("address_country"),
            ),
            emergency_contact=EmergencyContact(
                first_name=raw.get("emergency_contact_first_name"),
                last_name=raw.get("emergency_contact_last_name"),
                phone=raw.get("emergency_contact_phone"),
                email=raw.get("emergency_contact_email"),
            ),
            documents=documents,
            updated_at=raw.get("updated_at"),
        )
