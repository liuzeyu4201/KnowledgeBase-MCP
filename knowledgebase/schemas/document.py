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


class DocumentImportInput(BaseModel):
    request_id: str | None = None
    operator: str | None = None
    trace_id: str | None = None
    category_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=256)
    file_name: str = Field(min_length=1, max_length=256)
    mime_type: str
    file_content_base64: str = Field(min_length=1)

    @field_validator("title", "file_name", mode="before")
    @classmethod
    def normalize_required_str(cls, value: str) -> str:
        stripped = _strip_or_none(value)
        if stripped is None:
            raise ValueError("字段不能为空")
        return stripped

    @field_validator("mime_type", mode="before")
    @classmethod
    def normalize_mime_type(cls, value: str) -> str:
        stripped = _strip_or_none(value)
        if stripped is None:
            raise ValueError("mime_type 不能为空")
        return stripped

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, value: str) -> str:
        normalized = normalize_document_mime_type(value)
        if not is_supported_document_mime_type(normalized):
            raise ValueError(supported_document_mime_type_message())
        return normalized


class DocumentGetInput(BaseModel):
    request_id: str | None = None
    trace_id: str | None = None
    id: int | None = Field(default=None, gt=0)
    document_uid: str | None = Field(default=None, min_length=1, max_length=36)

    @field_validator("document_uid", mode="before")
    @classmethod
    def normalize_document_uid(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class DocumentListInput(BaseModel):
    request_id: str | None = None
    trace_id: str | None = None
    category_id: int | None = Field(default=None, gt=0)
    title: str | None = Field(default=None, max_length=256)
    file_name: str | None = Field(default=None, max_length=256)
    parse_status: str | None = Field(default=None, max_length=32)
    vector_status: str | None = Field(default=None, max_length=32)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("title", "file_name", "parse_status", "vector_status", mode="before")
    @classmethod
    def normalize_optional_str(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class DocumentDeleteInput(BaseModel):
    request_id: str | None = None
    operator: str | None = None
    trace_id: str | None = None
    id: int | None = Field(default=None, gt=0)
    document_uid: str | None = Field(default=None, min_length=1, max_length=36)

    @field_validator("document_uid", mode="before")
    @classmethod
    def normalize_document_uid(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class DocumentUpdateInput(BaseModel):
    request_id: str | None = None
    operator: str | None = None
    trace_id: str | None = None
    id: int | None = Field(default=None, gt=0)
    document_uid: str | None = Field(default=None, min_length=1, max_length=36)
    category_id: int | None = Field(default=None, gt=0)
    title: str | None = Field(default=None, min_length=1, max_length=256)
    file_name: str | None = Field(default=None, min_length=1, max_length=256)
    mime_type: str | None = None
    file_content_base64: str | None = Field(default=None, min_length=1)

    @field_validator("document_uid", "title", "file_name", "mime_type", mode="before")
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


class DocumentCategoryOutput(BaseModel):
    id: int
    category_code: str
    name: str

    @classmethod
    def from_model(cls, model: object) -> "DocumentCategoryOutput":
        return cls(
            id=model.id,
            category_code=model.category_code,
            name=model.name,
        )


class DocumentOutput(BaseModel):
    id: int
    document_uid: str
    category_id: int
    title: str
    source_type: str
    file_name: str
    storage_uri: str
    mime_type: str
    file_size: int
    file_sha256: str
    parse_status: str
    vector_status: str
    version: int
    chunk_count: int
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime
    category: DocumentCategoryOutput | None = None

    @classmethod
    def from_model(cls, model: object) -> "DocumentOutput":
        category = getattr(model, "category", None)
        return cls(
            id=model.id,
            document_uid=model.document_uid,
            category_id=model.category_id,
            title=model.title,
            source_type=model.source_type,
            file_name=model.file_name,
            storage_uri=model.storage_uri,
            mime_type=model.mime_type,
            file_size=model.file_size,
            file_sha256=model.file_sha256,
            parse_status=model.parse_status,
            vector_status=model.vector_status,
            version=model.version,
            chunk_count=model.chunk_count,
            last_error=model.last_error,
            created_at=model.created_at,
            updated_at=model.updated_at,
            category=DocumentCategoryOutput.from_model(category) if category is not None else None,
        )
