from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


DocumentFileType = Literal["pdf", "docx", "pptx", "xlsx", "zip", "other"]
DocumentCategory = Literal["shared", "instance", "exam_prep", "personal"]


class DocumentItem(BaseModel):
    id: str
    title: str
    file_type: DocumentFileType
    size_kb: float = 0
    uploader: str = "Albert School"
    upload_date: Optional[str] = None
    course_module_instance_id: Optional[str] = None
    course_name: Optional[str] = None
    category: DocumentCategory
    is_favorite: bool = False
    last_opened: Optional[str] = None
    download_url: Optional[str] = None
    source_download_url: Optional[str] = Field(default=None, exclude=True)
    storage_base_url: Optional[str] = Field(default=None, exclude=True)
    storage_bucket: Optional[str] = Field(default=None, exclude=True)
    storage_path: Optional[str] = Field(default=None, exclude=True)
