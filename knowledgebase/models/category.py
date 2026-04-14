from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, SmallInteger, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from knowledgebase.db.base import Base


class CategoryModel(Base):
    """知识分类表。"""

    __tablename__ = "kb_category"
    __table_args__ = (
        Index(
            "ix_kb_category_category_code",
            "category_code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_kb_category_name",
            "name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("idx_kb_category_status", "status"),
        Index("idx_kb_category_deleted_at", "deleted_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    category_code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    documents = relationship("DocumentModel", back_populates="category")
