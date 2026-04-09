from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from knowledgebase.db.base import Base


class ChunkModel(Base):
    """文档切片表。"""

    __tablename__ = "kb_chunk"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_no", name="uq_kb_chunk_document_chunk_no"),
        Index("idx_kb_chunk_vector_status", "vector_status", "vector_version"),
        Index("idx_kb_chunk_deleted_at", "deleted_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    chunk_uid: Mapped[str] = mapped_column(String(36), default=lambda: str(uuid4()), unique=True, index=True)
    document_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("kb_document.id"), index=True)
    chunk_no: Mapped[int] = mapped_column(Integer)
    page_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    embedding_model: Mapped[str] = mapped_column(String(128))
    vector_version: Mapped[int] = mapped_column(Integer, default=1)
    vector_status: Mapped[str] = mapped_column(String(32), default="pending")
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    document = relationship("DocumentModel", back_populates="chunks")
