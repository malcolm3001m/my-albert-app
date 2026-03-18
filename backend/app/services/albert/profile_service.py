from __future__ import annotations

from dataclasses import dataclass

from app.models.profile import Profile
from app.services.albert.client import AlbertClient
from app.utils.errors import UpstreamServiceError


@dataclass(frozen=True)
class IdentityContext:
    user_id: str
    student_id: str | None


class ProfileService:
    def __init__(self, client: AlbertClient) -> None:
        self.client = client

    async def get_profile(self) -> Profile:
        raw = await self.client.get_profile()
        profile = Profile(
            user_id=raw["user_id"],
            student_id=raw.get("student_id"),
            first_name=raw.get("first_name"),
            last_name=raw.get("last_name"),
            full_name=" ".join(
                part for part in [raw.get("first_name"), raw.get("last_name")] if part
            )
            or None,
            school_email=raw.get("school_email"),
            personal_email=raw.get("personal_email"),
            phone_number=raw.get("phone_number"),
            birthday=raw.get("birthday"),
            address=raw.get("address"),
            city=raw.get("city"),
            zip_code=raw.get("zip_code"),
            country=raw.get("country"),
            role=raw.get("role"),
            academic_program_name=raw.get("academic_program_name"),
            academic_program_level=raw.get("academic_program_level"),
            academic_program_school=raw.get("academic_program_school"),
            academic_program_track=raw.get("academic_program_track"),
            academic_program_start_date=raw.get("academic_program_start_date"),
            academic_program_main_language=raw.get("academic_program_main_language"),
            enrollment_status=raw.get("enrollment_status"),
            campus_city=raw.get("campus_city"),
            avatar_url=raw.get("avatar_url") or raw.get("picture_url"),
        )
        return profile

    async def get_identity_context(self) -> IdentityContext:
        profile = await self.get_profile()
        if not profile.user_id:
            raise UpstreamServiceError(
                "Albert API",
                "Albert profile is missing user_id.",
                path="/user/user-profile",
            )
        return IdentityContext(user_id=profile.user_id, student_id=profile.student_id)
