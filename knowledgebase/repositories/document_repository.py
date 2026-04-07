from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from knowledgebase.models.document import DocumentModel


class DocumentRepository:
    """文档数据访问层。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        category_id: int,
        title: str,
        file_name: str,
        storage_uri: str,
        mime_type: str,
        file_size: int,
        file_sha256: str,
        parse_status: str,
        vector_status: str,
    ) -> DocumentModel:
        document = DocumentModel(
            category_id=category_id,
            title=title,
            file_name=file_name,
            storage_uri=storage_uri,
            mime_type=mime_type,
            file_size=file_size,
            file_sha256=file_sha256,
            parse_status=parse_status,
            vector_status=vector_status,
        )
        self.session.add(document)
        self.session.flush()
        self.session.refresh(document)
        return document

    def get_by_id(self, document_id: int) -> DocumentModel | None:
        """按主键查询单个文档，并预加载分类信息。"""

        stmt = (
            select(DocumentModel)
            .options(selectinload(DocumentModel.category))
            .where(
                DocumentModel.id == document_id,
                DocumentModel.deleted_at.is_(None),
            )
        )
        return self.session.scalar(stmt)

    def get_by_uid(self, document_uid: str) -> DocumentModel | None:
        """按稳定业务标识查询单个文档，并预加载分类信息。"""

        stmt = (
            select(DocumentModel)
            .options(selectinload(DocumentModel.category))
            .where(
                DocumentModel.document_uid == document_uid,
                DocumentModel.deleted_at.is_(None),
            )
        )
        return self.session.scalar(stmt)

    def list(
        self,
        *,
        category_id: int | None,
        title: str | None,
        file_name: str | None,
        parse_status: str | None,
        vector_status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[DocumentModel], int]:
        """按过滤条件分页查询文档列表。"""

        conditions = [DocumentModel.deleted_at.is_(None)]
        if category_id is not None:
            conditions.append(DocumentModel.category_id == category_id)
        if title:
            conditions.append(DocumentModel.title.ilike(f"%{title}%"))
        if file_name:
            conditions.append(DocumentModel.file_name.ilike(f"%{file_name}%"))
        if parse_status:
            conditions.append(DocumentModel.parse_status == parse_status)
        if vector_status:
            conditions.append(DocumentModel.vector_status == vector_status)

        data_stmt = (
            select(DocumentModel)
            .options(selectinload(DocumentModel.category))
            .where(*conditions)
            .order_by(DocumentModel.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        count_stmt = select(func.count(DocumentModel.id)).where(*conditions)

        items = list(self.session.scalars(data_stmt).all())
        total = self.session.scalar(count_stmt) or 0
        return items, total

    def update_status(
        self,
        document: DocumentModel,
        *,
        parse_status: str | None = None,
        vector_status: str | None = None,
        chunk_count: int | None = None,
        last_error: str | None = None,
    ) -> DocumentModel:
        """更新文档状态字段。"""

        if parse_status is not None:
            document.parse_status = parse_status
        if vector_status is not None:
            document.vector_status = vector_status
        if chunk_count is not None:
            document.chunk_count = chunk_count
        if last_error is not None:
            document.last_error = last_error

        self.session.add(document)
        self.session.flush()
        self.session.refresh(document)
        return document

    def soft_delete(self, document: DocumentModel) -> DocumentModel:
        """对文档执行软删除。"""

        document.deleted_at = datetime.utcnow()
        self.session.add(document)
        self.session.flush()
        self.session.refresh(document)
        return document

    def update_document(
        self,
        document: DocumentModel,
        *,
        category_id: int | None = None,
        title: str | None = None,
        file_name: str | None = None,
        storage_uri: str | None = None,
        mime_type: str | None = None,
        file_size: int | None = None,
        file_sha256: str | None = None,
        version: int | None = None,
        chunk_count: int | None = None,
        parse_status: str | None = None,
        vector_status: str | None = None,
        last_error: str | None = None,
    ) -> DocumentModel:
        """更新文档主体字段。"""

        if category_id is not None:
            document.category_id = category_id
        if title is not None:
            document.title = title
        if file_name is not None:
            document.file_name = file_name
        if storage_uri is not None:
            document.storage_uri = storage_uri
        if mime_type is not None:
            document.mime_type = mime_type
        if file_size is not None:
            document.file_size = file_size
        if file_sha256 is not None:
            document.file_sha256 = file_sha256
        if version is not None:
            document.version = version
        if chunk_count is not None:
            document.chunk_count = chunk_count
        if parse_status is not None:
            document.parse_status = parse_status
        if vector_status is not None:
            document.vector_status = vector_status
        if last_error is not None:
            document.last_error = last_error

        self.session.add(document)
        self.session.flush()
        self.session.refresh(document)
        return document
