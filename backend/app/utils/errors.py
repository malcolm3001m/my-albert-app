from __future__ import annotations

from typing import Optional


class AppError(Exception):
    status_code = 500

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class MissingConfigurationError(AppError):
    status_code = 500


class ResourceNotFoundError(AppError):
    status_code = 404


class UpstreamServiceError(AppError):
    status_code = 502

    def __init__(
        self,
        service: str,
        detail: str,
        *,
        path: Optional[str] = None,
        upstream_status_code: Optional[int] = None,
    ) -> None:
        super().__init__(detail)
        self.service = service
        self.path = path
        self.upstream_status_code = upstream_status_code
