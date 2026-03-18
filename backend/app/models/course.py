from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class CourseModuleSummary(BaseModel):
    id: int
    code: Optional[str] = None
    name: Optional[str] = None
    ects: Optional[float] = None
    duration_hours: Optional[float] = None
    track_attendance: Optional[bool] = None
    syllabus_status: Optional[str] = None
    syllabus_version_id: Optional[int] = None


class CourseListItem(BaseModel):
    module_id: int
    code: Optional[str] = None
    name: Optional[str] = None
    ects: Optional[float] = None
    duration_hours: Optional[float] = None
    instance_count: int = 0
    instance_ids: List[int] = Field(default_factory=list)
    academic_years: List[int] = Field(default_factory=list)
    semesters: List[str] = Field(default_factory=list)
    teacher_names: List[str] = Field(default_factory=list)
    teaching_units: List[str] = Field(default_factory=list)
    syllabus_url: Optional[str] = None


class CourseListResponse(BaseModel):
    count: int
    items: List[CourseListItem] = Field(default_factory=list)


class CourseInstanceSummary(BaseModel):
    id: int
    internal_code: Optional[str] = None
    code: Optional[str] = None
    name: Optional[str] = None
    module_id: Optional[int] = None
    academic_year: Optional[int] = None
    semester: Optional[str] = None
    teaching_unit_name: Optional[str] = None
    teacher_name: Optional[str] = None
    teacher_email: Optional[str] = None
    ects: Optional[float] = None
    duration_hours: Optional[float] = None
    syllabus_url: Optional[str] = None
    cohort_names: List[str] = Field(default_factory=list)


class CourseInstanceListResponse(BaseModel):
    count: int
    items: List[CourseInstanceSummary] = Field(default_factory=list)


class StaffedTeacher(BaseModel):
    teacher_id: Optional[int] = None
    teacher_name: Optional[str] = None
    teacher_email: Optional[str] = None
    teacher_staffing_status: Optional[str] = None
    agreed_hourly_rate_incl_tax: Optional[float] = None


class CourseInstanceDetail(BaseModel):
    id: int
    internal_code: Optional[str] = None
    code: Optional[str] = None
    name: Optional[str] = None
    module_id: Optional[int] = None
    module_version_id: Optional[int] = None
    academic_year: Optional[int] = None
    semester: Optional[str] = None
    language: Optional[str] = None
    campus_name: Optional[str] = None
    teacher_name: Optional[str] = None
    teacher_email: Optional[str] = None
    ects: Optional[float] = None
    duration_hours: Optional[float] = None
    syllabus_url: Optional[str] = None
    blackboard_course_primary_id: Optional[str] = None
    teaching_unit_name: Optional[str] = None
    teaching_unit_code: Optional[str] = None
    staffed_teachers: List[StaffedTeacher] = Field(default_factory=list)
    module: Optional[CourseModuleSummary] = None


class CourseInstanceDetailResponse(BaseModel):
    course_instance: CourseInstanceDetail


class CourseModuleTeacher(BaseModel):
    teacher_id: Optional[int] = None
    user_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    school_email: Optional[str] = None


class CourseModuleDetail(BaseModel):
    id: int
    code: Optional[str] = None
    name: Optional[str] = None
    duration_hours: Optional[float] = None
    ects: Optional[float] = None
    teacher_id: Optional[int] = None
    syllabi_url: Optional[str] = None
    track_attendance: Optional[bool] = None
    current_published_version_id: Optional[int] = None
    teacher: Optional[CourseModuleTeacher] = None
    syllabus_status: Optional[str] = None
    syllabus_version_id: Optional[int] = None


class CourseModuleDetailResponse(BaseModel):
    course_module: CourseModuleDetail
