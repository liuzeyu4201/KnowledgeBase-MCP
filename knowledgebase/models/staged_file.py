from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import BIGINT, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from knowledgebase.db.base import Base


class StagedFileModel(Base):
    """远端上传暂存文件表。"""

    __tablename__ = "kb_staged_file"
    __table_args__ = (
        Index("idx_kb_staged_file_status", "status", "created_at"),
        Index("idx_kb_staged_file_expires_at", "expires_at"),
        Index("idx_kb_staged_file_file_sha256", "file_sha256"),
        Index("idx_kb_staged_file_deleted_at", "deleted_at"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    staged_file_uid: Mapped[str] = mapped_column(String(36), default=lambda: str(uuid4()), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="uploaded", index=True)
    storage_backend: Mapped[str] = mapped_column(String(32), default="local")
    storage_uri: Mapped[str] = mapped_column(String(1024))
    file_name: Mapped[str] = mapped_column(String(256))
    mime_type: Mapped[str] = mapped_column(String(128), index=True)
    source_type: Mapped[str] = mapped_column(String(32), index=True)
    file_size: Mapped[int] = mapped_column(BIGINT)
    file_sha256: Mapped[str] = mapped_column(String(64), index=True)
    upload_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    linked_document_id: Mapped[int | None] = mapped_column(
        BIGINT,
        ForeignKey("kb_document.id"),
        nullable=True,
        index=True,
    )
    linked_task_id: Mapped[int | None] = mapped_column(
        BIGINT,
        ForeignKey("kb_import_task.id"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    linked_document = relationship("DocumentModel")
    linked_task = relationship("ImportTaskModel")
