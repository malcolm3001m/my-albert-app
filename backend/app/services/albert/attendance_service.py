from __future__ import annotations

from app.models.attendance import AttendanceItem, AttendanceResponse, AttendanceSummary
from app.services.albert.client import AlbertClient
from app.services.albert.profile_service import ProfileService


class AttendanceService:
    def __init__(self, client: AlbertClient, profile_service: ProfileService) -> None:
        self.client = client
        self.profile_service = profile_service

    async def get_attendance(self) -> AttendanceResponse:
        context = await self.profile_service.get_identity_context()
        raw_items = await self.client.get_attendance(context.user_id)
        items = [
            AttendanceItem(
                attendance_id=item["attendance_id"],
                course_module_instance_id=item.get("course_module_instance_id"),
                course_name=(item.get("course_module_instance") or {}).get("course_module_instance_name"),
                course_code=(item.get("course_module_instance") or {}).get("course_module_instance_code"),
                present=bool(item.get("present")),
                exemption=bool(item.get("exemption")),
                manual_override=bool(item.get("manual_override")),
                session_id=item.get("course_instance_session_id"),
                session_summary=(item.get("course_instance_session") or {}).get("summary"),
                session_start=(item.get("course_instance_session") or {}).get("session_start_datetime_utc"),
                session_end=(item.get("course_instance_session") or {}).get("session_end_datetime_utc"),
                updated_at=item.get("updated_at"),
            )
            for item in raw_items
        ]
        items.sort(key=lambda item: item.session_start or "", reverse=True)

        exempt_count = sum(1 for item in items if item.exemption)
        counted_items = [item for item in items if not item.exemption]
        present_count = sum(1 for item in counted_items if item.present)
        absent_count = sum(1 for item in counted_items if not item.present)
        denominator = present_count + absent_count
        attendance_rate = round((present_count / denominator) * 100, 1) if denominator else None

        summary = AttendanceSummary(
            total_sessions=len(items),
            present_count=present_count,
            absent_count=absent_count,
            exempt_count=exempt_count,
            attendance_rate=attendance_rate,
        )
        return AttendanceResponse(summary=summary, items=items)
