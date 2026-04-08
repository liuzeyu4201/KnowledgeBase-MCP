from __future__ import annotations

import hashlib
from typing import Callable
from dataclasses import dataclass, field

from pydantic import ValidationError

from knowledgebase.domain.exceptions import AppError
from knowledgebase.integrations.chunking.text_chunker import TextChunker
from knowledgebase.integrations.embedding.embedder import build_embedder
from knowledgebase.integrations.milvus.collection_manager import MilvusCollectionManager
from knowledgebase.integrations.parser.pdf_parser import PDFParser
from knowledgebase.integrations.storage.file_storage import FileStorage
from knowledgebase.repositories.category_repository import CategoryRepository
from knowledgebase.repositories.chunk_repository import ChunkRepository
from knowledgebase.repositories.document_repository import DocumentRepository
from knowledgebase.schemas.document import (
    DocumentDeleteInput,
    DocumentGetInput,
    DocumentImportInput,
    DocumentListInput,
    DocumentOutput,
    DocumentUpdateInput,
)


@dataclass
class ImportCompensationContext:
    """记录文档导入期间已落地的外部副作用，便于失败时补偿。"""

    storage_uri: str | None = None
    milvus_chunk_ids: list[int] = field(default_factory=list)
    milvus_inserted: bool = False


@dataclass
class DeleteCompensationContext:
    """记录文档删除期间需要恢复的外部状态。"""

    original_storage_uri: str | None = None
    staged_storage_uri: str | None = None
    milvus_backup_rows: list[dict] = field(default_factory=list)
    milvus_deleted: bool = False


@dataclass
class UpdateCompensationContext:
    """记录文档更新期间需要恢复和清理的外部状态。"""

    old_storage_uri: str | None = None
    staged_old_storage_uri: str | None = None
    new_storage_uri: str | None = None
    old_milvus_rows: list[dict] = field(default_factory=list)
    old_milvus_deleted: bool = False
    new_milvus_chunk_ids: list[int] = field(default_factory=list)
    new_milvus_inserted: bool = False


class DocumentService:
    """文档导入服务。"""

    def __init__(
        self,
        *,
        category_repository: CategoryRepository,
        document_repository: DocumentRepository,
        chunk_repository: ChunkRepository,
    ) -> None:
        self.category_repository = category_repository
        self.document_repository = document_repository
        self.chunk_repository = chunk_repository
        self.storage = FileStorage()
        self.parser = PDFParser()
        self.chunker = TextChunker()
        self.embedder = build_embedder()
        self.milvus = MilvusCollectionManager()
        self._compensation_context: ImportCompensationContext | None = None
        self._delete_compensation_context: DeleteCompensationContext | None = None
        self._update_compensation_context: UpdateCompensationContext | None = None

    def import_document(self, payload: dict) -> dict:
        """导入 PDF、创建文档与切片，并写入 Milvus 稠密向量和 BM25 索引。"""

        self._compensation_context = ImportCompensationContext()
        try:
            data = DocumentImportInput.model_validate(payload)
        except ValidationError as exc:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="文档导入参数不合法",
                error_type="validation_error",
                details={"errors": exc.errors()},
            ) from exc

        file_bytes = self.storage.decode_base64_pdf(data.file_content_base64)
        return self._import_document_from_bytes(
            data=data,
            file_bytes=file_bytes,
            cancellation_checker=None,
        )

    def import_document_from_bytes(
        self,
        payload: dict,
        *,
        file_bytes: bytes,
        cancellation_checker: Callable[[], bool] | None = None,
    ) -> dict:
        """供后台任务复用的导入入口，直接消费已暂存文件字节内容。"""

        self._compensation_context = ImportCompensationContext()
        try:
            normalized_payload = dict(payload)
            normalized_payload.setdefault("file_content_base64", "staged-file")
            data = DocumentImportInput.model_validate(normalized_payload)
        except ValidationError as exc:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="文档导入参数不合法",
                error_type="validation_error",
                details={"errors": exc.errors()},
            ) from exc

        return self._import_document_from_bytes(
            data=data,
            file_bytes=file_bytes,
            cancellation_checker=cancellation_checker,
        )

    def get_document(self, payload: dict) -> DocumentOutput:
        """按主键或文档业务标识查询单个文档详情。"""

        try:
            data = DocumentGetInput.model_validate(payload)
        except ValidationError as exc:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="文档查询参数不合法",
                error_type="validation_error",
                details={"errors": exc.errors()},
            ) from exc

        document = self._resolve_document(id=data.id, document_uid=data.document_uid)
        return DocumentOutput.from_model(document)

    def list_documents(self, payload: dict) -> tuple[list[DocumentOutput], dict]:
        """按过滤条件分页查询文档列表。"""

        try:
            data = DocumentListInput.model_validate(payload)
        except ValidationError as exc:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="文档列表查询参数不合法",
                error_type="validation_error",
                details={"errors": exc.errors()},
            ) from exc

        items, total = self.document_repository.list(
            category_id=data.category_id,
            title=data.title,
            file_name=data.file_name,
            parse_status=data.parse_status,
            vector_status=data.vector_status,
            page=data.page,
            page_size=data.page_size,
        )
        outputs = [DocumentOutput.from_model(item) for item in items]
        pagination = {
            "page": data.page,
            "page_size": data.page_size,
            "total": total,
            "has_next": data.page * data.page_size < total,
        }
        return outputs, pagination

    def delete_document(self, payload: dict) -> dict:
        """删除文档、切片、Milvus 向量与原始文件，并保留补偿能力。"""

        try:
            data = DocumentDeleteInput.model_validate(payload)
        except ValidationError as exc:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="文档删除参数不合法",
                error_type="validation_error",
                details={"errors": exc.errors()},
            ) from exc

        document = self._resolve_document(id=data.id, document_uid=data.document_uid)
        chunks = self.chunk_repository.list_by_document_id(document.id)
        chunk_ids = [chunk.id for chunk in chunks]

        self._delete_compensation_context = DeleteCompensationContext()
        self._delete_compensation_context.milvus_backup_rows = self.milvus.fetch_chunks(chunk_ids)

        original_storage_uri, staged_storage_uri = self.storage.stage_delete_file(document.storage_uri)
        self._delete_compensation_context.original_storage_uri = original_storage_uri
        self._delete_compensation_context.staged_storage_uri = staged_storage_uri

        try:
            if chunk_ids:
                self.milvus.delete_chunks(chunk_ids)
                self._delete_compensation_context.milvus_deleted = True

            self.chunk_repository.soft_delete_many(chunks)
            self.document_repository.soft_delete(document)
        except Exception as exc:  # noqa: BLE001
            rollback_error = self.rollback_delete_side_effects(original_error=exc)
            if rollback_error is not None:
                raise rollback_error from exc
            if isinstance(exc, AppError):
                raise
            raise AppError(
                code="DOCUMENT_DELETE_FAILED",
                message="document delete failed",
                error_type="system_error",
                details={"error": str(exc)},
            ) from exc

        return {
            "deleted": True,
            "document_id": document.id,
            "document_uid": document.document_uid,
            "chunk_count": len(chunks),
        }

    def update_document(self, payload: dict) -> dict:
        """更新文档元数据，或以整篇重建方式替换 PDF、切片和向量。"""

        try:
            data = DocumentUpdateInput.model_validate(payload)
        except ValidationError as exc:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="文档更新参数不合法",
                error_type="validation_error",
                details={"errors": exc.errors()},
            ) from exc

        document = self._resolve_document(id=data.id, document_uid=data.document_uid)
        self._ensure_update_fields_present(data)

        if data.category_id is not None:
            category = self.category_repository.get_by_id(data.category_id)
            if category is None:
                raise AppError(
                    code="CATEGORY_NOT_FOUND",
                    message="category not found",
                    error_type="not_found",
                    details={"category_id": data.category_id},
                )

        has_file_update = data.file_content_base64 is not None
        self._ensure_file_update_fields(data, has_file_update=has_file_update)

        if not has_file_update:
            updated = self.document_repository.update_document(
                document,
                category_id=data.category_id,
                title=data.title,
            )
            return {
                "document": DocumentOutput.from_model(updated).model_dump(mode="json"),
                "chunks": {
                    "count": updated.chunk_count,
                },
                "vector_store": {
                    "provider": "milvus",
                    "collection_name": self.milvus.collection_name,
                    "dense_model": self._embedding_model_name(),
                    "sparse_strategy": "milvus_bm25",
                },
            }

        old_chunks = self.chunk_repository.list_by_document_id(document.id)
        old_chunk_ids = [chunk.id for chunk in old_chunks]

        self._update_compensation_context = UpdateCompensationContext()
        self._update_compensation_context.old_milvus_rows = self.milvus.fetch_chunks(old_chunk_ids)

        old_storage_uri, staged_old_storage_uri = self.storage.stage_delete_file(document.storage_uri)
        self._update_compensation_context.old_storage_uri = old_storage_uri
        self._update_compensation_context.staged_old_storage_uri = staged_old_storage_uri

        new_storage_uri, file_bytes = self.storage.save_pdf(
            file_name=data.file_name,
            file_content_base64=data.file_content_base64,
        )
        self._update_compensation_context.new_storage_uri = new_storage_uri
        file_sha256 = hashlib.sha256(file_bytes).hexdigest()

        try:
            pages = self.parser.parse(file_bytes)
            chunk_payloads = self.chunker.chunk_pages(pages)
            if not chunk_payloads:
                raise AppError(
                    code="DOCUMENT_PARSE_FAILED",
                    message="no chunks generated from document",
                    error_type="system_error",
                )

            dense_vectors = self.embedder.embed_texts([item.content for item in chunk_payloads])

            if old_chunk_ids:
                self.milvus.delete_chunks(old_chunk_ids)
                self._update_compensation_context.old_milvus_deleted = True

            self.chunk_repository.delete_many(old_chunks)

            updating_document = self.document_repository.update_document(
                document,
                category_id=data.category_id,
                title=data.title,
                file_name=data.file_name,
                storage_uri=new_storage_uri,
                mime_type=data.mime_type,
                file_size=len(file_bytes),
                file_sha256=file_sha256,
                version=document.version + 1,
                chunk_count=0,
                parse_status="processing",
                vector_status="indexing",
                last_error=None,
            )

            chunk_rows = []
            for item in chunk_payloads:
                chunk_rows.append(
                    {
                        "document_id": updating_document.id,
                        "chunk_no": item.chunk_no,
                        "page_no": item.page_no,
                        "char_start": item.char_start,
                        "char_end": item.char_end,
                        "token_count": item.token_count,
                        "content": item.content,
                        "content_hash": hashlib.sha256(item.content.encode("utf-8")).hexdigest(),
                        "embedding_model": self._embedding_model_name(),
                        "vector_version": updating_document.version,
                        "vector_status": "ready",
                        "metadata_json": {"page_no": item.page_no},
                    }
                )

            new_chunks = self.chunk_repository.create_many(chunk_rows)
            self._update_compensation_context.new_milvus_chunk_ids = [chunk.id for chunk in new_chunks]

            milvus_rows = []
            for chunk, dense_vector in zip(new_chunks, dense_vectors, strict=True):
                milvus_rows.append(
                    {
                        "chunk_id": chunk.id,
                        "document_id": updating_document.id,
                        "category_id": updating_document.category_id,
                        "chunk_no": chunk.chunk_no,
                        "page_no": chunk.page_no or 0,
                        "content": chunk.content,
                        "dense_vector": dense_vector,
                    }
                )

            self.milvus.insert_chunks(milvus_rows)
            self._update_compensation_context.new_milvus_inserted = True

            updated = self.document_repository.update_document(
                updating_document,
                chunk_count=len(new_chunks),
                parse_status="success",
                vector_status="ready",
                last_error=None,
            )
        except Exception as exc:  # noqa: BLE001
            rollback_error = self.rollback_update_side_effects(original_error=exc)
            if rollback_error is not None:
                raise rollback_error from exc
            if isinstance(exc, AppError):
                raise
            raise AppError(
                code="DOCUMENT_UPDATE_FAILED",
                message="document update failed",
                error_type="system_error",
                details={"error": str(exc)},
            ) from exc

        return {
            "document": DocumentOutput.from_model(updated).model_dump(mode="json"),
            "chunks": {
                "count": updated.chunk_count,
            },
            "vector_store": {
                "provider": "milvus",
                "collection_name": self.milvus.collection_name,
                "dense_model": self._embedding_model_name(),
                "sparse_strategy": "milvus_bm25",
            },
        }

    def rollback_import_side_effects(
        self,
        *,
        original_error: Exception | None = None,
    ) -> AppError | None:
        """回滚数据库事务、Milvus 向量和原始文件，尽量消除跨存储不一致。"""

        rollback_errors: list[str] = []

        try:
            self.document_repository.session.rollback()
        except Exception as exc:  # noqa: BLE001
            rollback_errors.append(f"database rollback failed: {exc}")

        if self._compensation_context and self._compensation_context.milvus_inserted:
            try:
                self.milvus.delete_chunks(self._compensation_context.milvus_chunk_ids)
            except Exception as exc:  # noqa: BLE001
                rollback_errors.append(f"milvus rollback failed: {exc}")

        if self._compensation_context and self._compensation_context.storage_uri:
            try:
                self.storage.delete_file(self._compensation_context.storage_uri)
            except Exception as exc:  # noqa: BLE001
                rollback_errors.append(f"storage rollback failed: {exc}")

        self._compensation_context = None

        if rollback_errors:
            return AppError(
                code="CONSISTENCY_ROLLBACK_FAILED",
                message="document import rollback failed",
                error_type="system_error",
                details={
                    "original_error": str(original_error) if original_error else None,
                    "rollback_errors": rollback_errors,
                },
            )

        return None

    def clear_import_context(self) -> None:
        """在数据库事务提交成功后清理补偿上下文。"""

        self._compensation_context = None

    def rollback_delete_side_effects(
        self,
        *,
        original_error: Exception | None = None,
    ) -> AppError | None:
        """回滚文档删除期间已经执行的跨存储操作。"""

        rollback_errors: list[str] = []

        try:
            self.document_repository.session.rollback()
        except Exception as exc:  # noqa: BLE001
            rollback_errors.append(f"database rollback failed: {exc}")

        if self._delete_compensation_context and self._delete_compensation_context.milvus_deleted:
            try:
                self.milvus.insert_chunks(self._delete_compensation_context.milvus_backup_rows)
            except Exception as exc:  # noqa: BLE001
                rollback_errors.append(f"milvus rollback failed: {exc}")

        if self._delete_compensation_context:
            try:
                self.storage.restore_staged_file(
                    original_path=self._delete_compensation_context.original_storage_uri,
                    staged_path=self._delete_compensation_context.staged_storage_uri,
                )
            except Exception as exc:  # noqa: BLE001
                rollback_errors.append(f"storage rollback failed: {exc}")

        self._delete_compensation_context = None

        if rollback_errors:
            return AppError(
                code="CONSISTENCY_ROLLBACK_FAILED",
                message="document delete rollback failed",
                error_type="system_error",
                details={
                    "original_error": str(original_error) if original_error else None,
                    "rollback_errors": rollback_errors,
                },
            )

        return None

    def finalize_delete_context(self) -> None:
        """数据库提交成功后最终清理暂存文件并清空删除补偿上下文。"""

        if self._delete_compensation_context:
            self.storage.finalize_staged_file_delete(
                self._delete_compensation_context.staged_storage_uri
            )
        self._delete_compensation_context = None

    def rollback_update_side_effects(
        self,
        *,
        original_error: Exception | None = None,
    ) -> AppError | None:
        """回滚文档更新期间已执行的跨存储操作。"""

        rollback_errors: list[str] = []

        try:
            self.document_repository.session.rollback()
        except Exception as exc:  # noqa: BLE001
            rollback_errors.append(f"database rollback failed: {exc}")

        if self._update_compensation_context and self._update_compensation_context.new_milvus_inserted:
            try:
                self.milvus.delete_chunks(self._update_compensation_context.new_milvus_chunk_ids)
            except Exception as exc:  # noqa: BLE001
                rollback_errors.append(f"new milvus rollback failed: {exc}")

        if self._update_compensation_context and self._update_compensation_context.old_milvus_deleted:
            try:
                self.milvus.insert_chunks(self._update_compensation_context.old_milvus_rows)
            except Exception as exc:  # noqa: BLE001
                rollback_errors.append(f"old milvus restore failed: {exc}")

        if self._update_compensation_context and self._update_compensation_context.new_storage_uri:
            try:
                self.storage.delete_file(self._update_compensation_context.new_storage_uri)
            except Exception as exc:  # noqa: BLE001
                rollback_errors.append(f"new storage cleanup failed: {exc}")

        if self._update_compensation_context:
            try:
                self.storage.restore_staged_file(
                    original_path=self._update_compensation_context.old_storage_uri,
                    staged_path=self._update_compensation_context.staged_old_storage_uri,
                )
            except Exception as exc:  # noqa: BLE001
                rollback_errors.append(f"old storage restore failed: {exc}")

        self._update_compensation_context = None

        if rollback_errors:
            return AppError(
                code="CONSISTENCY_ROLLBACK_FAILED",
                message="document update rollback failed",
                error_type="system_error",
                details={
                    "original_error": str(original_error) if original_error else None,
                    "rollback_errors": rollback_errors,
                },
            )

        return None

    def finalize_update_context(self) -> None:
        """数据库提交成功后最终清理被替换掉的旧文件。"""

        if self._update_compensation_context:
            self.storage.finalize_staged_file_delete(
                self._update_compensation_context.staged_old_storage_uri
            )
        self._update_compensation_context = None

    def _resolve_document(
        self,
        *,
        id: int | None,
        document_uid: str | None,
    ):
        """按主键或业务标识解析目标文档。"""

        if id is None and document_uid is None:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="id or document_uid is required",
                error_type="validation_error",
            )

        document = None
        if id is not None:
            document = self.document_repository.get_by_id(id)
        if document_uid is not None:
            document_by_uid = self.document_repository.get_by_uid(document_uid)
            if id is not None and document and document_by_uid and document.id != document_by_uid.id:
                raise AppError(
                    code="INVALID_ARGUMENT",
                    message="id and document_uid do not match",
                    error_type="validation_error",
                )
            document = document_by_uid or document

        if document is None:
            raise AppError(
                code="DOCUMENT_NOT_FOUND",
                message="document not found",
                error_type="not_found",
                details={"id": id, "document_uid": document_uid},
            )

        return document

    def _ensure_update_fields_present(self, data: DocumentUpdateInput) -> None:
        """确保更新请求至少包含一个实际变更字段。"""

        if (
            data.category_id is None
            and data.title is None
            and data.file_name is None
            and data.mime_type is None
            and data.file_content_base64 is None
        ):
            raise AppError(
                code="INVALID_ARGUMENT",
                message="at least one update field is required",
                error_type="validation_error",
            )

    def _ensure_file_update_fields(
        self,
        data: DocumentUpdateInput,
        *,
        has_file_update: bool,
    ) -> None:
        """校验文件替换场景下的必填字段组合。"""

        if not has_file_update:
            if data.file_name is not None or data.mime_type is not None:
                raise AppError(
                    code="INVALID_ARGUMENT",
                    message="file_name and mime_type require file_content_base64",
                    error_type="validation_error",
                )
            return

        if data.file_name is None or data.mime_type is None:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="file_name, mime_type and file_content_base64 are required together",
                error_type="validation_error",
            )

    def _embedding_model_name(self) -> str:
        """返回当前向量模型名。"""

        return getattr(self.embedder, "model", "mock-embedding")

    def _import_document_from_bytes(
        self,
        *,
        data: DocumentImportInput,
        file_bytes: bytes,
        cancellation_checker: Callable[[], bool] | None,
    ) -> dict:
        """执行真正的文档导入流程，支持同步导入和后台任务复用。"""

        category = self.category_repository.get_by_id(data.category_id)
        if category is None:
            raise AppError(
                code="CATEGORY_NOT_FOUND",
                message="category not found",
                error_type="not_found",
                details={"category_id": data.category_id},
            )

        self._check_cooperative_cancellation(cancellation_checker)
        storage_uri, saved_file_bytes = self.storage.save_pdf_bytes(
            file_name=data.file_name,
            file_bytes=file_bytes,
        )
        self._compensation_context.storage_uri = storage_uri
        file_sha256 = hashlib.sha256(saved_file_bytes).hexdigest()

        document = self.document_repository.create(
            category_id=data.category_id,
            title=data.title,
            file_name=data.file_name,
            storage_uri=storage_uri,
            mime_type=data.mime_type,
            file_size=len(saved_file_bytes),
            file_sha256=file_sha256,
            parse_status="processing",
            vector_status="indexing",
        )

        try:
            self._check_cooperative_cancellation(cancellation_checker)
            pages = self.parser.parse(saved_file_bytes)

            self._check_cooperative_cancellation(cancellation_checker)
            chunk_payloads = self.chunker.chunk_pages(pages)
            if not chunk_payloads:
                raise AppError(
                    code="DOCUMENT_PARSE_FAILED",
                    message="no chunks generated from document",
                    error_type="system_error",
                )

            self._check_cooperative_cancellation(cancellation_checker)
            dense_vectors = self.embedder.embed_texts([item.content for item in chunk_payloads])

            chunk_rows = []
            for item in chunk_payloads:
                chunk_rows.append(
                    {
                        "document_id": document.id,
                        "chunk_no": item.chunk_no,
                        "page_no": item.page_no,
                        "char_start": item.char_start,
                        "char_end": item.char_end,
                        "token_count": item.token_count,
                        "content": item.content,
                        "content_hash": hashlib.sha256(item.content.encode("utf-8")).hexdigest(),
                        "embedding_model": self._embedding_model_name(),
                        "vector_version": 1,
                        "vector_status": "ready",
                        "metadata_json": {"page_no": item.page_no},
                    }
                )

            chunks = self.chunk_repository.create_many(chunk_rows)
            self._compensation_context.milvus_chunk_ids = [chunk.id for chunk in chunks]

            milvus_rows = []
            for chunk, dense_vector in zip(chunks, dense_vectors, strict=True):
                milvus_rows.append(
                    {
                        "chunk_id": chunk.id,
                        "document_id": document.id,
                        "category_id": document.category_id,
                        "chunk_no": chunk.chunk_no,
                        "page_no": chunk.page_no or 0,
                        "content": chunk.content,
                        "dense_vector": dense_vector,
                    }
                )

            self._check_cooperative_cancellation(cancellation_checker)
            self.milvus.insert_chunks(milvus_rows)
            self._compensation_context.milvus_inserted = True

            document = self.document_repository.update_status(
                document,
                parse_status="success",
                vector_status="ready",
                chunk_count=len(chunks),
                last_error=None,
            )
        except Exception as exc:  # noqa: BLE001
            rollback_error = self.rollback_import_side_effects(original_error=exc)
            if rollback_error is not None:
                raise rollback_error from exc
            if isinstance(exc, AppError):
                raise
            raise AppError(
                code="DOCUMENT_IMPORT_FAILED",
                message="document import failed",
                error_type="system_error",
                details={"error": str(exc)},
            ) from exc

        return {
            "document": DocumentOutput.from_model(document).model_dump(mode="json"),
            "chunks": {
                "count": document.chunk_count,
            },
            "vector_store": {
                "provider": "milvus",
                "collection_name": self.milvus.collection_name,
                "dense_model": self._embedding_model_name(),
                "sparse_strategy": "milvus_bm25",
            },
        }

    def _check_cooperative_cancellation(
        self,
        cancellation_checker: Callable[[], bool] | None,
    ) -> None:
        """在关键阶段检查是否收到取消信号，实现协作式取消。"""

        if cancellation_checker is None:
            return
        if cancellation_checker():
            raise AppError(
                code="TASK_CANCELED",
                message="task canceled cooperatively",
                error_type="business_error",
            )
