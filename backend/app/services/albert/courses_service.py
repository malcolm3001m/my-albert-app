from __future__ import annotations

from typing import Any

from app.models.course import (
    CourseInstanceDetail,
    CourseInstanceListResponse,
    CourseInstanceSummary,
    CourseListItem,
    CourseListResponse,
    CourseModuleDetail,
    CourseModuleSummary,
    CourseModuleTeacher,
    StaffedTeacher,
)
from app.services.albert.client import AlbertClient
from app.services.albert.profile_service import ProfileService


class CoursesService:
    def __init__(self, client: AlbertClient, profile_service: ProfileService) -> None:
        self.client = client
        self.profile_service = profile_service

    async def get_course_instances(self) -> CourseInstanceListResponse:
        raw_items = await self._get_course_instance_payloads()
        items = [self._normalize_course_instance(item) for item in raw_items]
        items.sort(
            key=lambda item: (
                -(item.academic_year or 0),
                item.semester or "",
                item.name or "",
                item.id,
            )
        )
        return CourseInstanceListResponse(count=len(items), items=items)

    async def get_courses(self) -> CourseListResponse:
        raw_items = await self._get_course_instance_payloads()
        grouped: dict[int, dict[str, Any]] = {}

        for item in raw_items:
            module_id = item.get("course_module_id")
            if module_id is None:
                continue

            group = grouped.setdefault(
                module_id,
                {
                    "module_id": module_id,
                    "code": item.get("course_module_instance_code"),
                    "name": item.get("course_module_instance_name"),
                    "ects": item.get("ects"),
                    "duration_hours": item.get("duration_hours"),
                    "instance_ids": [],
                    "academic_years": set(),
                    "semesters": set(),
                    "teacher_names": set(),
                    "teaching_units": set(),
                    "syllabus_url": item.get("syllabi_url"),
                },
            )

            if item.get("id") is not None:
                group["instance_ids"].append(item["id"])
            if item.get("academic_year") is not None:
                group["academic_years"].add(item["academic_year"])
            if item.get("semester"):
                group["semesters"].add(item["semester"])
            if item.get("teacher_name"):
                group["teacher_names"].add(item["teacher_name"])
            if item.get("teaching_unit_instance_name"):
                group["teaching_units"].add(item["teaching_unit_instance_name"])

        items = [
            CourseListItem(
                module_id=module_id,
                code=data["code"],
                name=data["name"],
                ects=data["ects"],
                duration_hours=data["duration_hours"],
                instance_count=len(data["instance_ids"]),
                instance_ids=sorted(data["instance_ids"]),
                academic_years=sorted(data["academic_years"], reverse=True),
                semesters=sorted(data["semesters"], reverse=True),
                teacher_names=sorted(data["teacher_names"]),
                teaching_units=sorted(data["teaching_units"]),
                syllabus_url=data["syllabus_url"],
            )
            for module_id, data in grouped.items()
        ]
        items.sort(key=lambda item: (-(max(item.academic_years) if item.academic_years else 0), item.name or ""))
        return CourseListResponse(count=len(items), items=items)

    async def get_course_instance(self, instance_id: int) -> CourseInstanceDetail:
        raw = await self.client.get_course_module_instance(instance_id)
        module = None
        module_id = raw.get("course_module_id")
        if module_id is not None:
            try:
                module = await self._get_module_summary(module_id)
            except Exception:
                module = None

        staffed_teachers = [
            StaffedTeacher(
                teacher_id=item.get("teacher_id"),
                teacher_name=item.get("teacher_name"),
                teacher_email=item.get("teacher_email"),
                teacher_staffing_status=item.get("teacher_staffing_status"),
                agreed_hourly_rate_incl_tax=item.get("agreed_hourly_rate_incl_tax"),
            )
            for item in raw.get("staffed_teachers", [])
        ]

        teacher_name = " ".join(
            part for part in [raw.get("teacher_first_name"), raw.get("teacher_last_name")] if part
        ) or None

        return CourseInstanceDetail(
            id=raw["id"],
            internal_code=raw.get("id_internal"),
            code=raw.get("course_module_instance_code"),
            name=raw.get("course_module_instance_name"),
            module_id=module_id,
            module_version_id=raw.get("course_module_version_id"),
            academic_year=raw.get("academic_year"),
            semester=raw.get("semester"),
            language=raw.get("language"),
            campus_name=raw.get("campus_name"),
            teacher_name=teacher_name,
            teacher_email=raw.get("teacher_notification_email"),
            ects=raw.get("ects"),
            duration_hours=raw.get("duration_hours"),
            syllabus_url=raw.get("syllabi_url"),
            blackboard_course_primary_id=raw.get("blackboard_course_primary_id"),
            teaching_unit_name=raw.get("teaching_unit_instance_name"),
            teaching_unit_code=raw.get("teaching_unit_instance_code"),
            staffed_teachers=staffed_teachers,
            module=module,
        )

    async def get_course_module(self, course_module_id: int) -> CourseModuleDetail:
        raw = await self.client.get_course_module(course_module_id)
        teacher = raw.get("teacher") or {}
        syllabus = raw.get("syllabus") or {}
        return CourseModuleDetail(
            id=raw["course_module_id"],
            code=raw.get("course_module_code"),
            name=raw.get("course_module_name"),
            duration_hours=raw.get("duration_hours"),
            ects=raw.get("ects"),
            teacher_id=raw.get("teacher_id"),
            syllabi_url=raw.get("syllabi_url"),
            track_attendance=raw.get("track_attendance"),
            current_published_version_id=raw.get("current_published_version_id"),
            teacher=CourseModuleTeacher(
                teacher_id=teacher.get("teacher_id"),
                user_id=teacher.get("user_id"),
                first_name=teacher.get("first_name"),
                last_name=teacher.get("last_name"),
                email=teacher.get("email"),
                school_email=teacher.get("school_email"),
            )
            if teacher
            else None,
            syllabus_status=syllabus.get("status"),
            syllabus_version_id=syllabus.get("current_version_id"),
        )

    async def _get_course_instance_payloads(self) -> list[dict[str, Any]]:
        context = await self.profile_service.get_identity_context()
        raw_items = await self.client.get_course_module_instances(context.user_id)
        return list(raw_items or [])

    def _normalize_course_instance(self, item: dict[str, Any]) -> CourseInstanceSummary:
        cohort_names = [cohort.get("default_prefix") for cohort in item.get("cohorts", []) if cohort.get("default_prefix")]
        if item.get("cohort", {}).get("name"):
            cohort_names.append(item["cohort"]["name"])

        ordered_cohorts = list(dict.fromkeys(cohort_names))
        return CourseInstanceSummary(
            id=item["id"],
            internal_code=item.get("id_internal"),
            code=item.get("course_module_instance_code"),
            name=item.get("course_module_instance_name"),
            module_id=item.get("course_module_id"),
            academic_year=item.get("academic_year"),
            semester=item.get("semester"),
            teaching_unit_name=item.get("teaching_unit_instance_name"),
            teacher_name=item.get("teacher_name"),
            teacher_email=item.get("teacher_notification_email"),
            ects=item.get("ects"),
            duration_hours=item.get("duration_hours"),
            syllabus_url=item.get("syllabi_url"),
            cohort_names=ordered_cohorts,
        )

    async def _get_module_summary(self, course_module_id: int) -> CourseModuleSummary:
        raw = await self.client.get_course_module(course_module_id)
        syllabus = raw.get("syllabus") or {}
        return CourseModuleSummary(
            id=raw["course_module_id"],
            code=raw.get("course_module_code"),
            name=raw.get("course_module_name"),
            ects=raw.get("ects"),
            duration_hours=raw.get("duration_hours"),
            track_attendance=raw.get("track_attendance"),
            syllabus_status=syllabus.get("status"),
            syllabus_version_id=syllabus.get("current_version_id"),
        )
