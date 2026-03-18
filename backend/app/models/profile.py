from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Profile(BaseModel):
    user_id: str
    student_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    school_email: Optional[str] = None
    personal_email: Optional[str] = None
    phone_number: Optional[str] = None
    birthday: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    role: Optional[str] = None
    academic_program_name: Optional[str] = None
    academic_program_level: Optional[str] = None
    academic_program_school: Optional[str] = None
    academic_program_track: Optional[str] = None
    academic_program_start_date: Optional[str] = None
    academic_program_main_language: Optional[str] = None
    enrollment_status: Optional[str] = None
    campus_city: Optional[str] = None
    avatar_url: Optional[str] = None


class ProfileResponse(BaseModel):
    profile: Profile


class CohortCampus(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    code: Optional[str] = None


class CohortProgram(BaseModel):
    program_instance_id: Optional[str] = None
    academic_program_instance_name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[str] = None
    track: Optional[str] = None
    format: Optional[str] = None
    main_language: Optional[str] = None


class CohortItem(BaseModel):
    id: int
    name: Optional[str] = None
    year: Optional[int] = None
    semester: Optional[str] = None
    google_calendar_id: Optional[str] = None
    campus: Optional[CohortCampus] = None
    academic_program_instance: Optional[CohortProgram] = None


class CohortListResponse(BaseModel):
    count: int
    items: List[CohortItem] = Field(default_factory=list)


class IntakeAddress(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None


class EmergencyContact(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class IntakeDocumentStatus(BaseModel):
    status: Optional[str] = None
    validated_at: Optional[str] = None
    comment: Optional[str] = None
    url: Optional[str] = None


class Intake(BaseModel):
    student_id: Optional[str] = None
    academic_year: Optional[str] = None
    school: Optional[str] = None
    form_version: Optional[str] = None
    status: Optional[str] = None
    personal_email: Optional[str] = None
    phone_number: Optional[str] = None
    birthday: Optional[str] = None
    city_of_birth: Optional[str] = None
    country_of_birth: Optional[str] = None
    nationality: Optional[str] = None
    gender_at_birth: Optional[str] = None
    level_of_class: Optional[str] = None
    general_information: Optional[str] = None
    address: IntakeAddress
    emergency_contact: EmergencyContact
    documents: dict[str, IntakeDocumentStatus]
    updated_at: Optional[str] = None


class IntakeResponse(BaseModel):
    intake: Intake
