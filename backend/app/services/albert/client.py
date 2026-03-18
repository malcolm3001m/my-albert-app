from __future__ import annotations

import json
import logging
from typing import Any, Optional

import httpx

from app.core.config import Settings
from app.utils.cache import TTLCache
from app.utils.errors import (
    MissingConfigurationError,
    ResourceNotFoundError,
    UpstreamServiceError,
)


class AlbertClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cache = TTLCache()
        self.http = httpx.AsyncClient(timeout=settings.albert_http_timeout_seconds)

    async def aclose(self) -> None:
        await self.http.aclose()

    async def get_json(self, path: str, *, cache_ttl: Optional[int] = None) -> Any:
        cache_key = f"GET:{path}"
        if cache_ttl:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        if self.settings.albert_use_fixtures:
            payload = self._load_fixture(path)
            if cache_ttl:
                self.cache.set(cache_key, payload, cache_ttl)
            return payload

        if not self.settings.albert_base_url or not self.settings.albert_bearer_token:
            raise MissingConfigurationError(
                "Albert API is not configured. Set ALBERT_BASE_URL and ALBERT_BEARER_TOKEN."
            )

        url = f"{self.settings.albert_base_url.rstrip('/')}{path}"
        headers = {
            "Authorization": f"Bearer {self.settings.albert_bearer_token}",
            "Accept": "application/json",
        }

        try:
            response = await self.http.get(url, headers=headers)
        except httpx.RequestError as exc:
            raise UpstreamServiceError(
                "Albert API",
                f"Albert request failed: {exc}",
                path=path,
            ) from exc

        if response.status_code == 404:
            raise ResourceNotFoundError(f"Albert resource not found for path {path}.")

        if response.status_code >= 500:
            raise UpstreamServiceError(
                "Albert API",
                "Albert returned a server error.",
                path=path,
                upstream_status_code=response.status_code,
            )

        if response.is_error:
            raise UpstreamServiceError(
                "Albert API",
                f"Albert returned {response.status_code}.",
                path=path,
                upstream_status_code=response.status_code,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise UpstreamServiceError(
                "Albert API",
                "Albert returned invalid JSON.",
                path=path,
                upstream_status_code=response.status_code,
            ) from exc

        if cache_ttl:
            self.cache.set(cache_key, payload, cache_ttl)
        return payload

    async def get_profile(self) -> Any:
        return await self.get_json(
            "/user/user-profile",
            cache_ttl=self.settings.albert_profile_cache_ttl_seconds,
        )

    async def get_intake(self) -> Any:
        return await self.get_json("/student/intake", cache_ttl=self.settings.albert_profile_cache_ttl_seconds)

    async def get_cohorts(self, user_id: str) -> Any:
        return await self.get_json(
            f"/student/{user_id}/cohorts",
            cache_ttl=self.settings.albert_profile_cache_ttl_seconds,
        )

    async def get_course_module_instances(self, user_id: str) -> Any:
        return await self.get_json(
            f"/student/{user_id}/course-module-instances",
            cache_ttl=self.settings.albert_detail_cache_ttl_seconds,
        )

    async def get_attendance(self, user_id: str) -> Any:
        return await self.get_json(
            f"/attendance/user/{user_id}",
            cache_ttl=self.settings.albert_detail_cache_ttl_seconds,
        )

    async def get_transcripts(self, user_id: str) -> Any:
        return await self.get_json(
            f"/transcript/by-user-id/{user_id}",
            cache_ttl=self.settings.albert_detail_cache_ttl_seconds,
        )

    async def get_exams(self, student_id: str) -> Any:
        return await self.get_json(
            f"/course/exam/v2/student/{student_id}/exams",
            cache_ttl=self.settings.albert_detail_cache_ttl_seconds,
        )

    async def get_grades(self, student_id: str) -> Any:
        return await self.get_json(
            f"/student-exam-grade/student/{student_id}",
            cache_ttl=self.settings.albert_detail_cache_ttl_seconds,
        )

    async def get_course_module(self, course_module_id: int) -> Any:
        return await self.get_json(
            f"/course-modules/{course_module_id}",
            cache_ttl=self.settings.albert_detail_cache_ttl_seconds,
        )

    async def get_course_module_instance(self, instance_id: int) -> Any:
        return await self.get_json(
            f"/course/course-module-instance/by-id/{instance_id}",
            cache_ttl=self.settings.albert_detail_cache_ttl_seconds,
        )

    def _load_fixture(self, path: str) -> Any:
        fixtures_dir = self.settings.fixtures_path
        if fixtures_dir is None:
            raise MissingConfigurationError(
                "Fixture mode is enabled but ALBERT_FIXTURES_DIR is not configured."
            )

        filename = self._fixture_filename_for_path(path)
        fixture_path = fixtures_dir / filename
        if not fixture_path.exists():
            raise ResourceNotFoundError(f"No Albert fixture found for path {path}.")

        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]
        return payload

    def _fixture_filename_for_path(self, path: str) -> str:
        clean_path = path.split("?", maxsplit=1)[0]

        if clean_path == "/user/user-profile":
            return "01_user_profile.json"
        if clean_path == "/student/intake":
            return "02_student_intake.json"
        if clean_path.startswith("/student/") and clean_path.endswith("/cohorts"):
            return "03_student_cohorts.json"
        if clean_path.startswith("/student/") and clean_path.endswith("/course-module-instances"):
            return "04_student_course_module_instances.json"
        if clean_path.startswith("/attendance/user/"):
            return "05_attendance.json"
        if clean_path.startswith("/transcript/by-user-id/"):
            return "06_transcripts.json"
        if clean_path.startswith("/course/exam/v2/student/") and clean_path.endswith("/exams"):
            return "07_exams.json"
        if clean_path.startswith("/student-exam-grade/student/"):
            return "08_grades_try.json"
        if clean_path.startswith("/course/course-module-instance/by-id/"):
            return f"course_instance__{clean_path.rsplit('/', maxsplit=1)[-1]}.json"
        if clean_path.startswith("/course-modules/"):
            return f"course_module__{clean_path.rsplit('/', maxsplit=1)[-1]}.json"

        raise ResourceNotFoundError(f"No fixture mapping exists for Albert path {path}.")
