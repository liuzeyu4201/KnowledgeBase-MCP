from __future__ import annotations

from datetime import datetime

from sqlalchemy import BIGINT, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from knowledgebase.db.base import Base


class StorageGCTaskModel(Base):
    """对象存储垃圾清理任务表。"""

    __tablename__ = "kb_storage_gc_task"
    __table_args__ = (
        Index("idx_kb_storage_gc_task_status_next_retry_at", "status", "next_retry_at", "id"),
        Index("idx_kb_storage_gc_task_resource", "resource_type", "resource_id"),
        Index("idx_kb_storage_gc_task_lease_expires_at", "lease_expires_at"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    resource_type: Mapped[str] = mapped_column(String(32), index=True)
    resource_id: Mapped[int | None] = mapped_column(BIGINT, nullable=True, index=True)
    storage_backend: Mapped[str] = mapped_column(String(32))
    storage_uri: Mapped[str] = mapped_column(String(1024))
    action: Mapped[str] = mapped_column(String(32), default="delete", index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retry_count: Mapped[int] = mapped_column(Integer, default=20)
    lease_token: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
