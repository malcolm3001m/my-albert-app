from __future__ import annotations

import logging

from app.models.exam import GradeItem, GradeSummary, GradesResponse
from app.services.albert.client import AlbertClient
from app.services.albert.profile_service import ProfileService
from app.utils.errors import MissingConfigurationError, ResourceNotFoundError, UpstreamServiceError


class GradesService:
    def __init__(self, client: AlbertClient, profile_service: ProfileService) -> None:
        self.client = client
        self.profile_service = profile_service
        self.logger = logging.getLogger(self.__class__.__name__)

    async def get_grades(self) -> GradesResponse:
        context = await self.profile_service.get_identity_context()
        if not context.student_id:
            return GradesResponse(
                available=False,
                reason="Albert profile did not include a student_id.",
                summary=None,
                items=None,
            )

        try:
            raw_items = await self.client.get_grades(context.student_id)
        except (MissingConfigurationError, ResourceNotFoundError) as exc:
            self.logger.warning("Grades unavailable: %s", exc.detail)
            return GradesResponse(available=False, reason=exc.detail, summary=None, items=None)
        except UpstreamServiceError as exc:
            reason = "Albert grade service currently unavailable."
            if exc.upstream_status_code == 400:
                raise
            self.logger.warning("Albert grades failed: %s", exc.detail)
            return GradesResponse(available=False, reason=reason, summary=None, items=None)

        items = [
            GradeItem(
                id=item["id"],
                exam_id=item.get("exam_id"),
                exam_paper_id=item.get("exam_paper_id"),
                session=item.get("session"),
                grade=item.get("grade"),
                grade_status=item.get("grade_status"),
                counts_in_average=item.get("counts_in_average"),
                comment_for_student=item.get("comment_for_student"),
                exam_name=(item.get("exam") or {}).get("name"),
                exam_date=(item.get("exam") or {}).get("exam_date"),
                course_module_code=((item.get("exam_paper") or {}).get("course_module") or {}).get(
                    "course_module_code"
                ),
                course_module_name=((item.get("exam_paper") or {}).get("course_module") or {}).get(
                    "course_module_name"
                ),
                academic_year=((item.get("exam") or {}).get("course_module_instance") or {}).get(
                    "academic_year"
                ),
                semester=((item.get("exam") or {}).get("course_module_instance") or {}).get("semester"),
                exam_status=(item.get("exam_paper") or {}).get("exam_status"),
                statistics_average=((item.get("exam_paper") or {}).get("grade_statistics") or {}).get(
                    "average"
                ),
                statistics_min=((item.get("exam_paper") or {}).get("grade_statistics") or {}).get("min"),
                statistics_max=((item.get("exam_paper") or {}).get("grade_statistics") or {}).get("max"),
            )
            for item in raw_items
        ]
        items.sort(key=lambda item: item.exam_date or "", reverse=True)

        numeric_grades = [
            item.grade for item in items if item.grade is not None and item.counts_in_average is not False
        ]
        summary = GradeSummary(
            total_count=len(items),
            numeric_count=len(numeric_grades),
            average_grade=round(sum(numeric_grades) / len(numeric_grades), 2)
            if numeric_grades
            else None,
        )
        return GradesResponse(available=True, reason=None, summary=summary, items=items)
