from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from knowledgebase.models.category import CategoryModel
from knowledgebase.models.chunk import ChunkModel
from knowledgebase.models.document import DocumentModel


class ChunkRepository:
    """切片数据访问层。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_many(self, rows: list[dict]) -> list[ChunkModel]:
        """批量创建切片记录。"""

        chunks = [ChunkModel(**row) for row in rows]
        self.session.add_all(chunks)
        self.session.flush()
        return chunks

    def list_by_document_id(self, document_id: int) -> list[ChunkModel]:
        """查询文档下全部未删除切片。"""

        stmt = (
            select(ChunkModel)
            .where(
                ChunkModel.document_id == document_id,
                ChunkModel.deleted_at.is_(None),
            )
            .order_by(ChunkModel.chunk_no.asc())
        )
        return list(self.session.scalars(stmt).all())

    def soft_delete_many(self, chunks: list[ChunkModel]) -> None:
        """批量软删除切片。"""

        deleted_at = datetime.utcnow()
        for chunk in chunks:
            chunk.deleted_at = deleted_at
            self.session.add(chunk)
        self.session.flush()

    def delete_many(self, chunks: list[ChunkModel]) -> None:
        """物理删除旧切片，用于文档整篇重建。"""

        for chunk in chunks:
            self.session.delete(chunk)
        self.session.flush()

    def list_search_rows(
        self,
        chunk_ids: list[int],
    ) -> dict[int, tuple[ChunkModel, DocumentModel, CategoryModel]]:
        """按切片 ID 批量回查切片、文档和分类，用于检索结果组装。"""

        if not chunk_ids:
            return {}

        stmt = (
            select(ChunkModel, DocumentModel, CategoryModel)
            .join(DocumentModel, ChunkModel.document_id == DocumentModel.id)
            .join(CategoryModel, DocumentModel.category_id == CategoryModel.id)
            .where(
                ChunkModel.id.in_(chunk_ids),
                ChunkModel.deleted_at.is_(None),
                DocumentModel.deleted_at.is_(None),
                CategoryModel.deleted_at.is_(None),
                DocumentModel.parse_status == "success",
                DocumentModel.vector_status == "ready",
            )
        )
        rows = self.session.execute(stmt).all()
        return {chunk.id: (chunk, document, category) for chunk, document, category in rows}
