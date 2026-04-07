from __future__ import annotations

from datetime import datetime
import re

from pydantic import BaseModel, Field, field_validator


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class CategoryCreateInput(BaseModel):
    request_id: str | None = None
    operator: str | None = None
    trace_id: str | None = None
    category_code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=512)
    status: int = Field(default=1)

    @field_validator("category_code", "name", mode="before")
    @classmethod
    def normalize_required_str(cls, value: str) -> str:
        stripped = _strip_or_none(value)
        if stripped is None:
            raise ValueError("字段不能为空")
        return stripped

    @field_validator("description", mode="before")
    @classmethod
    def normalize_optional_str(cls, value: str | None) -> str | None:
        return _strip_or_none(value)

    @field_validator("category_code")
    @classmethod
    def validate_category_code(cls, value: str) -> str:
        if re.fullmatch(r"[A-Za-z0-9_-]+", value) is None:
            raise ValueError("category_code 格式不合法")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: int) -> int:
        if value not in {0, 1}:
            raise ValueError("status 仅允许 0 或 1")
        return value


class CategoryGetInput(BaseModel):
    request_id: str | None = None
    trace_id: str | None = None
    id: int | None = None
    category_code: str | None = Field(default=None, max_length=64)

    @field_validator("category_code", mode="before")
    @classmethod
    def normalize_category_code(cls, value: str | None) -> str | None:
        return _strip_or_none(value)

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("id 必须大于 0")
        return value

    @field_validator("category_code")
    @classmethod
    def validate_category_code(cls, value: str | None) -> str | None:
        if value is not None and re.fullmatch(r"[A-Za-z0-9_-]+", value) is None:
            raise ValueError("category_code 格式不合法")
        return value


class CategoryListInput(BaseModel):
    request_id: str | None = None
    trace_id: str | None = None
    category_code: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, max_length=128)
    status: int | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("category_code", "name", mode="before")
    @classmethod
    def normalize_optional_filter(cls, value: str | None) -> str | None:
        return _strip_or_none(value)

    @field_validator("category_code")
    @classmethod
    def validate_category_code(cls, value: str | None) -> str | None:
        if value is not None and re.fullmatch(r"[A-Za-z0-9_-]+", value) is None:
            raise ValueError("category_code 格式不合法")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: int | None) -> int | None:
        if value is not None and value not in {0, 1}:
            raise ValueError("status 仅允许 0 或 1")
        return value


class CategoryUpdateInput(BaseModel):
    request_id: str | None = None
    operator: str | None = None
    trace_id: str | None = None
    id: int | None = None
    category_code: str | None = Field(default=None, max_length=64)
    new_category_code: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, max_length=128)
    description: str | None = Field(default=None, max_length=512)
    status: int | None = None

    @field_validator("category_code", "new_category_code", "name", mode="before")
    @classmethod
    def normalize_optional_str_fields(cls, value: str | None) -> str | None:
        return _strip_or_none(value)

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("id 必须大于 0")
        return value

    @field_validator("category_code", "new_category_code")
    @classmethod
    def validate_category_code(cls, value: str | None) -> str | None:
        if value is not None and re.fullmatch(r"[A-Za-z0-9_-]+", value) is None:
            raise ValueError("category_code 格式不合法")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: int | None) -> int | None:
        if value is not None and value not in {0, 1}:
            raise ValueError("status 仅允许 0 或 1")
        return value


class CategoryDeleteInput(BaseModel):
    request_id: str | None = None
    operator: str | None = None
    trace_id: str | None = None
    id: int | None = None
    category_code: str | None = Field(default=None, max_length=64)

    @field_validator("category_code", mode="before")
    @classmethod
    def normalize_category_code(cls, value: str | None) -> str | None:
        return _strip_or_none(value)

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("id 必须大于 0")
        return value

    @field_validator("category_code")
    @classmethod
    def validate_category_code(cls, value: str | None) -> str | None:
        if value is not None and re.fullmatch(r"[A-Za-z0-9_-]+", value) is None:
            raise ValueError("category_code 格式不合法")
        return value


class CategoryOutput(BaseModel):
    id: int
    category_code: str
    name: str
    description: str | None
    status: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, model: object) -> "CategoryOutput":
        return cls(
            id=model.id,
            category_code=model.category_code,
            name=model.name,
            description=model.description,
            status=model.status,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
