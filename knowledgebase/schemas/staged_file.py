from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from knowledgebase.domain.document_types import (
    is_supported_document_mime_type,
    normalize_document_mime_type,
    supported_document_mime_type_message,
)


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class StagedFileGetInput(BaseModel):
    request_id: str | None = None
    trace_id: str | None = None
    id: int | None = Field(default=None, gt=0)
    staged_file_uid: str | None = Field(default=None, min_length=1, max_length=36)

    @field_validator("staged_file_uid", mode="before")
    @classmethod
    def normalize_uid(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class StagedFileListInput(BaseModel):
    request_id: str | None = None
    trace_id: str | None = None
    status: str | None = Field(default=None, max_length=32)
    mime_type: str | None = None
    linked_document_id: int | None = Field(default=None, gt=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("status", "mime_type", mode="before")
    @classmethod
    def normalize_optional_fields(cls, value: str | None) -> str | None:
        return _strip_or_none(value)

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_document_mime_type(value)
        if not is_supported_document_mime_type(normalized):
            raise ValueError(supported_document_mime_type_message())
        return normalized


class StagedFileDeleteInput(BaseModel):
    request_id: str | None = None
    operator: str | None = None
    trace_id: str | None = None
    id: int | None = Field(default=None, gt=0)
    staged_file_uid: str | None = Field(default=None, min_length=1, max_length=36)

    @field_validator("staged_file_uid", mode="before")
    @classmethod
    def normalize_uid(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class StagedFileOutput(BaseModel):
    id: int
    staged_file_uid: str
    status: str
    storage_backend: str
    storage_uri: str
    file_name: str
    mime_type: str
    source_type: str
    file_size: int
    file_sha256: str
    upload_completed_at: datetime | None
    expires_at: datetime | None
    consumed_at: datetime | None
    last_error: str | None
    linked_document_id: int | None
    linked_task_id: int | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    @classmethod
    def from_model(cls, model: object) -> "StagedFileOutput":
        return cls(
            id=model.id,
            staged_file_uid=model.staged_file_uid,
            status=model.status,
            storage_backend=model.storage_backend,
            storage_uri=model.storage_uri,
            file_name=model.file_name,
            mime_type=model.mime_type,
            source_type=model.source_type,
            file_size=model.file_size,
            file_sha256=model.file_sha256,
            upload_completed_at=model.upload_completed_at,
            expires_at=model.expires_at,
            consumed_at=model.consumed_at,
            last_error=model.last_error,
            linked_document_id=model.linked_document_id,
            linked_task_id=model.linked_task_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )
