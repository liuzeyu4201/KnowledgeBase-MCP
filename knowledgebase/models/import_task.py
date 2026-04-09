from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import BIGINT, Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from knowledgebase.db.base import Base


class ImportTaskModel(Base):
    """批量文档导入任务主表。"""

    __tablename__ = "kb_import_task"
    __table_args__ = (
        Index("idx_kb_import_task_status_priority", "status", "priority", "created_at"),
        Index("idx_kb_import_task_cancel_requested", "cancel_requested"),
        Index("idx_kb_import_task_lease_expires_at", "lease_expires_at"),
        Index("idx_kb_import_task_request_id", "request_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    task_uid: Mapped[str] = mapped_column(String(36), default=lambda: str(uuid4()), unique=True, index=True)
    task_type: Mapped[str] = mapped_column(String(64), default="document_import_batch", index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    priority: Mapped[int] = mapped_column(Integer, default=50, index=True)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True, index=True)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    operator: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    pending_items: Mapped[int] = mapped_column(Integer, default=0)
    running_items: Mapped[int] = mapped_column(Integer, default=0)
    success_items: Mapped[int] = mapped_column(Integer, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, default=0)
    canceled_items: Mapped[int] = mapped_column(Integer, default=0)
    progress_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    lease_token: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("ImportTaskItemModel", back_populates="task")


class ImportTaskItemModel(Base):
    """批量文档导入任务子项表。"""

    __tablename__ = "kb_import_task_item"
    __table_args__ = (
        UniqueConstraint("task_id", "item_no", name="uq_kb_import_task_item_task_item_no"),
        Index("idx_kb_import_task_item_status", "status", "priority", "id"),
        Index("idx_kb_import_task_item_task_id", "task_id"),
        Index("idx_kb_import_task_item_document_id", "document_id"),
        Index("idx_kb_import_task_item_staged_file_id", "staged_file_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(BIGINT, ForeignKey("kb_import_task.id"), index=True)
    item_no: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    priority: Mapped[int] = mapped_column(Integer, default=50, index=True)
    category_id: Mapped[int] = mapped_column(BIGINT, index=True)
    title: Mapped[str] = mapped_column(String(256))
    file_name: Mapped[str] = mapped_column(String(256))
    mime_type: Mapped[str] = mapped_column(String(128))
    staged_file_id: Mapped[int] = mapped_column(BIGINT, ForeignKey("kb_staged_file.id"), index=True)
    file_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    document_id: Mapped[int | None] = mapped_column(BIGINT, nullable=True, index=True)
    document_uid: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    lease_token: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    task = relationship("ImportTaskModel", back_populates="items")
    staged_file = relationship("StagedFileModel")
