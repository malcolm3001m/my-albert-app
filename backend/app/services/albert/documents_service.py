from __future__ import annotations

import logging
import math
import re
from pathlib import PurePosixPath
from typing import Any, Optional
from urllib.parse import unquote, urlparse

from app.models.document import DocumentCategory, DocumentFileType, DocumentItem
from app.services.albert.client import AlbertClient
from app.services.albert.courses_service import CoursesService
from app.utils.errors import MissingConfigurationError


EXAM_PREP_PATTERN = re.compile(r"\b(exam|mock|past)\b", re.IGNORECASE)
KNOWN_FILE_TYPES: set[DocumentFileType] = {"pdf", "docx", "pptx", "xlsx", "zip", "other"}


class DocumentsService:
    def __init__(self, client: AlbertClient, courses_service: CoursesService) -> None:
        self.client = client
        self.courses_service = courses_service
        self.logger = logging.getLogger(self.__class__.__name__)

    async def get_documents(self) -> list[DocumentItem]:
        course_instances = await self.courses_service.get_course_instances()
        documents_by_key: dict[tuple[str, str, str], DocumentItem] = {}

        module_names: dict[int, Optional[str]] = {}
        module_codes: dict[int, Optional[str]] = {}
        seen_modules: set[int] = set()

        for instance in course_instances.items:
            if instance.module_id is not None:
                module_names.setdefault(instance.module_id, instance.name)
                module_codes.setdefault(instance.module_id, instance.code)

            try:
                raw_instance_documents = await self.client.get_academic_documents_by_course_module_instance(
                    instance.id
                )
            except MissingConfigurationError:
                raise
            except Exception as exc:
                self.logger.warning(
                    "Could not load academic documents for course instance %s: %s",
                    instance.id,
                    exc,
                )
                raw_instance_documents = []

            for raw in self._extract_document_items(raw_instance_documents):
                normalized = self._normalize_document(
                    raw,
                    category="instance",
                    course_name=instance.name,
                    course_module_instance_id=instance.id,
                    module_code=instance.code,
                )
                if normalized:
                    self._store_document(documents_by_key, normalized)

            if instance.module_id is None or instance.module_id in seen_modules:
                continue

            seen_modules.add(instance.module_id)
            try:
                raw_module_documents = await self.client.get_academic_documents_by_course_module(
                    instance.module_id
                )
            except MissingConfigurationError:
                raise
            except Exception as exc:
                self.logger.warning(
                    "Could not load shared academic documents for course module %s: %s",
                    instance.module_id,
                    exc,
                )
                raw_module_documents = []

            for raw in self._extract_document_items(raw_module_documents):
                normalized = self._normalize_document(
                    raw,
                    category="shared",
                    course_name=module_names.get(instance.module_id) or instance.name,
                    course_module_instance_id=None,
                    module_code=module_codes.get(instance.module_id) or instance.code,
                )
                if normalized:
                    self._store_document(documents_by_key, normalized)

        items = list(documents_by_key.values())
        items.sort(
            key=lambda item: (
                item.course_name or "",
                item.category,
                item.upload_date or "",
                item.title.lower(),
            )
        )
        return items

    def _extract_document_items(self, payload: Any) -> list[dict[str, Any]]:
        if payload is None:
            return []
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if not isinstance(payload, dict):
            return []

        for key in ("items", "documents", "results", "rows", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
            if isinstance(value, dict):
                nested = self._extract_document_items(value)
                if nested:
                    return nested

        return []

    def _normalize_document(
        self,
        raw: dict[str, Any],
        *,
        category: DocumentCategory,
        course_name: Optional[str],
        course_module_instance_id: Optional[int],
        module_code: Optional[str],
    ) -> Optional[DocumentItem]:
        download_url = self._pick_first_str(
            raw,
            "download_url",
            "downloadUrl",
            "file_url",
            "fileUrl",
            "signed_url",
            "signedUrl",
            "url",
        )
        title = self._pick_first_str(
            raw,
            "title",
            "name",
            "document_name",
            "documentName",
            "file_name",
            "fileName",
        )
        if not title:
            title = self._filename_from_url(download_url)
        if not title:
            title = self._pick_first_str(raw, "storage_path", "storagePath")
            title = self._filename_from_url(title) if title else None
        if not title:
            return None

        inferred_category = "exam_prep" if EXAM_PREP_PATTERN.search(title) else category
        file_type = self._infer_file_type(title, download_url)
        size_kb = self._size_kb_from_raw(raw)
        upload_date = self._pick_first_str(
            raw,
            "upload_date",
            "uploadDate",
            "uploaded_at",
            "uploadedAt",
            "created_at",
            "createdAt",
            "updated_at",
            "updatedAt",
            "published_at",
            "publishedAt",
        )
        uploader = self._pick_first_str(
            raw,
            "uploader",
            "uploaded_by_name",
            "uploadedByName",
            "created_by_name",
            "createdByName",
            "author_name",
            "authorName",
        ) or "Albert School"

        document_id = self._pick_first_str(raw, "id", "document_id", "documentId", "academic_document_id")
        stable_id = document_id or (
            f"{category}:{course_module_instance_id or module_code or 'unknown'}:{title}"
        )

        return DocumentItem(
            id=str(stable_id),
            title=title,
            file_type=file_type,
            size_kb=size_kb,
            uploader=uploader,
            upload_date=upload_date,
            course_module_instance_id=str(course_module_instance_id)
            if course_module_instance_id is not None
            else None,
            course_name=course_name,
            category=inferred_category,
            is_favorite=False,
            last_opened=None,
            download_url=download_url,
        )

    def _store_document(
        self,
        documents_by_key: dict[tuple[str, str, str], DocumentItem],
        document: DocumentItem,
    ) -> None:
        dedupe_key = (
            document.title.strip().lower(),
            (document.download_url or "").strip().lower(),
            document.file_type,
        )
        existing = documents_by_key.get(dedupe_key)
        if existing is None or self._document_priority(document) > self._document_priority(existing):
            documents_by_key[dedupe_key] = document

    def _document_priority(self, document: DocumentItem) -> int:
        if document.category == "instance":
            return 3
        if document.category == "exam_prep":
            return 2
        if document.category == "shared":
            return 1
        return 0

    def _infer_file_type(
        self,
        title: str,
        download_url: Optional[str],
    ) -> DocumentFileType:
        candidates = [title]
        if download_url:
            candidates.append(download_url)

        for value in candidates:
            suffix = PurePosixPath(urlparse(value).path).suffix.lower().lstrip(".")
            if suffix in KNOWN_FILE_TYPES:
                return suffix  # type: ignore[return-value]
        return "other"

    def _size_kb_from_raw(self, raw: dict[str, Any]) -> float:
        raw_size = None
        for key in ("size_bytes", "sizeBytes", "file_size", "fileSize", "size"):
            value = raw.get(key)
            if isinstance(value, (int, float)):
                raw_size = float(value)
                break
        if raw_size is None:
            return 0
        return math.ceil(raw_size / 1024 * 100) / 100

    def _pick_first_str(self, raw: dict[str, Any], *keys: str) -> Optional[str]:
        for key in keys:
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _filename_from_url(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        path = urlparse(value).path
        if not path:
            return None
        filename = PurePosixPath(path).name
        return unquote(filename) if filename else None
