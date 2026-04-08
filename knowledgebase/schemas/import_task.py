from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class ImportTaskSubmitItemInput(BaseModel):
    category_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=256)
    file_name: str = Field(min_length=1, max_length=256)
    mime_type: str
    file_content_base64: str = Field(min_length=1)
    priority: int | None = Field(default=None, ge=0, le=1000)

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
        if value != "application/pdf":
            raise ValueError("仅支持 application/pdf")
        return value


class ImportTaskSubmitInput(BaseModel):
    request_id: str | None = None
    operator: str | None = None
    trace_id: str | None = None
    idempotency_key: str | None = Field(default=None, max_length=128)
    priority: int = Field(default=50, ge=0, le=1000)
    max_attempts: int = Field(default=3, ge=1, le=10)
    items: list[ImportTaskSubmitItemInput] = Field(min_length=1, max_length=100)

    @field_validator("idempotency_key", mode="before")
    @classmethod
    def normalize_idempotency_key(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class ImportTaskGetInput(BaseModel):
    request_id: str | None = None
    trace_id: str | None = None
    id: int | None = Field(default=None, gt=0)
    task_uid: str | None = Field(default=None, min_length=1, max_length=36)
    include_items: bool = True

    @field_validator("task_uid", mode="before")
    @classmethod
    def normalize_task_uid(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class ImportTaskCancelInput(BaseModel):
    request_id: str | None = None
    operator: str | None = None
    trace_id: str | None = None
    id: int | None = Field(default=None, gt=0)
    task_uid: str | None = Field(default=None, min_length=1, max_length=36)

    @field_validator("task_uid", mode="before")
    @classmethod
    def normalize_task_uid(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


class ImportTaskItemOutput(BaseModel):
    id: int
    item_no: int
    status: str
    priority: int
    category_id: int
    title: str
    file_name: str
    mime_type: str
    file_sha256: str | None
    document_id: int | None
    document_uid: str | None
    attempt_count: int
    started_at: datetime | None
    finished_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, model: object) -> "ImportTaskItemOutput":
        return cls(
            id=model.id,
            item_no=model.item_no,
            status=model.status,
            priority=model.priority,
            category_id=model.category_id,
            title=model.title,
            file_name=model.file_name,
            mime_type=model.mime_type,
            file_sha256=model.file_sha256,
            document_id=model.document_id,
            document_uid=model.document_uid,
            attempt_count=model.attempt_count,
            started_at=model.started_at,
            finished_at=model.finished_at,
            last_error=model.last_error,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class ImportTaskOutput(BaseModel):
    id: int
    task_uid: str
    task_type: str
    status: str
    priority: int
    cancel_requested: bool
    idempotency_key: str | None
    request_id: str | None
    operator: str | None
    trace_id: str | None
    total_items: int
    pending_items: int
    running_items: int
    success_items: int
    failed_items: int
    canceled_items: int
    progress_percent: float
    attempt_count: int
    max_attempts: int
    started_at: datetime | None
    finished_at: datetime | None
    heartbeat_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime
    items: list[ImportTaskItemOutput] | None = None

    @classmethod
    def from_model(
        cls,
        model: object,
        *,
        items: list[object] | None = None,
    ) -> "ImportTaskOutput":
        sorted_items = None
        if items is not None:
            sorted_items = sorted(items, key=lambda item: (item.item_no, item.id))
        return cls(
            id=model.id,
            task_uid=model.task_uid,
            task_type=model.task_type,
            status=model.status,
            priority=model.priority,
            cancel_requested=model.cancel_requested,
            idempotency_key=model.idempotency_key,
            request_id=model.request_id,
            operator=model.operator,
            trace_id=model.trace_id,
            total_items=model.total_items,
            pending_items=model.pending_items,
            running_items=model.running_items,
            success_items=model.success_items,
            failed_items=model.failed_items,
            canceled_items=model.canceled_items,
            progress_percent=float(model.progress_percent or 0),
            attempt_count=model.attempt_count,
            max_attempts=model.max_attempts,
            started_at=model.started_at,
            finished_at=model.finished_at,
            heartbeat_at=model.heartbeat_at,
            last_error=model.last_error,
            created_at=model.created_at,
            updated_at=model.updated_at,
            items=[ImportTaskItemOutput.from_model(item) for item in sorted_items] if sorted_items is not None else None,
        )
