from __future__ import annotations

from datetime import datetime, timedelta
from typing import BinaryIO

from pydantic import ValidationError

from knowledgebase.app.config import get_settings
from knowledgebase.domain.document_types import (
    infer_document_mime_type,
    is_supported_document_mime_type,
    resolve_document_source_type,
    supported_document_mime_type_message,
)
from knowledgebase.domain.exceptions import AppError
from knowledgebase.integrations.storage.file_storage import FileStorage
from knowledgebase.repositories.staged_file_repository import StagedFileRepository
from knowledgebase.repositories.storage_gc_task_repository import StorageGCTaskRepository
from knowledgebase.schemas.staged_file import (
    StagedFileDeleteInput,
    StagedFileGetInput,
    StagedFileListInput,
    StagedFileOutput,
)
from knowledgebase.services.storage_cleanup_service import StorageCleanupService


class StagedFileService:
    """暂存文件服务，负责上传记录治理和基础查询删除。"""

    def __init__(self, repository: StagedFileRepository) -> None:
        self.repository = repository
        self.storage = FileStorage()
        self.settings = get_settings()
        self.cleanup_service = StorageCleanupService(
            StorageGCTaskRepository(repository.session)
        )

    def create_from_stream(
        self,
        *,
        file_name: str,
        file_stream: BinaryIO,
        mime_type: str | None,
    ) -> StagedFileOutput:
        """把上传文件流写入暂存区并创建数据库记录。"""

        resolved_mime_type = self._resolve_supported_mime_type(file_name=file_name, mime_type=mime_type)

        try:
            if hasattr(file_stream, "seek"):
                file_stream.seek(0)
            storage_uri, file_size, file_sha256 = self.storage.save_staged_file_stream(
                file_name=file_name,
                file_stream=file_stream,
            )
        except Exception as exc:  # noqa: BLE001
            raise AppError(
                code="STAGED_FILE_UPLOAD_FAILED",
                message="staged file upload failed",
                error_type="system_error",
                details={"error": str(exc)},
            ) from exc

        if file_size <= 0:
            self.storage.delete_file(storage_uri)
            raise AppError(
                code="INVALID_ARGUMENT",
                message="file content is empty",
                error_type="validation_error",
            )

        try:
            model = self.repository.create(
                storage_backend=self.storage.resolve_storage_backend(storage_uri),
                storage_uri=storage_uri,
                file_name=file_name,
                mime_type=resolved_mime_type,
                source_type=resolve_document_source_type(resolved_mime_type),
                file_size=file_size,
                file_sha256=file_sha256,
                expires_at=datetime.utcnow() + timedelta(seconds=self.settings.staged_file_ttl_seconds),
            )
        except Exception as exc:  # noqa: BLE001
            self.storage.delete_file(storage_uri)
            if isinstance(exc, AppError):
                raise
            raise

        return StagedFileOutput.from_model(model)

    def create_from_bytes(
        self,
        *,
        file_name: str,
        file_bytes: bytes,
        mime_type: str,
    ) -> StagedFileOutput:
        """供兼容路径复用，直接从字节数组创建暂存文件。"""

        resolved_mime_type = self._resolve_supported_mime_type(file_name=file_name, mime_type=mime_type)
        if not file_bytes:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="file content is empty",
                error_type="validation_error",
            )

        storage_uri, file_size, file_sha256 = self.storage.save_staged_file_bytes(
            file_name=file_name,
            file_bytes=file_bytes,
        )
        try:
            model = self.repository.create(
                storage_backend=self.storage.resolve_storage_backend(storage_uri),
                storage_uri=storage_uri,
                file_name=file_name,
                mime_type=resolved_mime_type,
                source_type=resolve_document_source_type(resolved_mime_type),
                file_size=file_size,
                file_sha256=file_sha256,
                expires_at=datetime.utcnow() + timedelta(seconds=self.settings.staged_file_ttl_seconds),
            )
        except Exception:
            self.storage.delete_file(storage_uri)
            raise
        return StagedFileOutput.from_model(model)

    def get_staged_file(self, payload: dict) -> StagedFileOutput:
        """按主键或稳定标识查询单个暂存文件。"""

        try:
            data = StagedFileGetInput.model_validate(payload)
        except ValidationError as exc:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="暂存文件查询参数不合法",
                error_type="validation_error",
                details={"errors": exc.errors()},
            ) from exc

        model = self._resolve_staged_file(id=data.id, staged_file_uid=data.staged_file_uid)
        return StagedFileOutput.from_model(model)

    def list_staged_files(self, payload: dict) -> tuple[list[StagedFileOutput], dict]:
        """分页查询暂存文件列表。"""

        try:
            data = StagedFileListInput.model_validate(payload)
        except ValidationError as exc:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="暂存文件列表查询参数不合法",
                error_type="validation_error",
                details={"errors": exc.errors()},
            ) from exc

        items, total = self.repository.list(
            status=data.status,
            mime_type=data.mime_type,
            linked_document_id=data.linked_document_id,
            page=data.page,
            page_size=data.page_size,
        )
        outputs = [StagedFileOutput.from_model(item) for item in items]
        pagination = {
            "page": data.page,
            "page_size": data.page_size,
            "total": total,
            "has_next": data.page * data.page_size < total,
        }
        return outputs, pagination

    def delete_staged_file(self, payload: dict) -> StagedFileOutput:
        """删除未消费或已过期的暂存文件。"""

        try:
            data = StagedFileDeleteInput.model_validate(payload)
        except ValidationError as exc:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="暂存文件删除参数不合法",
                error_type="validation_error",
                details={"errors": exc.errors()},
            ) from exc

        model = self._resolve_staged_file(id=data.id, staged_file_uid=data.staged_file_uid)
        if model.status not in self.repository.DELETABLE_STATUSES:
            raise AppError(
                code="STAGED_FILE_STATUS_INVALID",
                message="staged file status does not allow delete",
                error_type="business_error",
                details={"status": model.status},
            )

        self.cleanup_service.delete_now_or_enqueue(
            resource_type="staged_file",
            resource_id=model.id,
            storage_uri=model.storage_uri,
            storage_backend=model.storage_backend,
        )
        model = self.repository.mark_deleted(model)
        return StagedFileOutput.from_model(model)

    def delete_staged_file_by_id(self, staged_file_id: int) -> None:
        """供后台清理流程复用，尽最大努力删除暂存文件。"""

        model = self.repository.get_by_id(staged_file_id)
        if model is None:
            return
        if model.status not in self.repository.DELETABLE_STATUSES:
            return
        self.cleanup_service.delete_now_or_enqueue(
            resource_type="staged_file",
            resource_id=model.id,
            storage_uri=model.storage_uri,
            storage_backend=model.storage_backend,
        )
        self.repository.mark_deleted(model)

    def _resolve_staged_file(
        self,
        *,
        id: int | None,
        staged_file_uid: str | None,
    ):
        """按主键或稳定标识解析暂存文件。"""

        if id is None and staged_file_uid is None:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="id or staged_file_uid is required",
                error_type="validation_error",
            )

        model = self.repository.get_by_id(id) if id is not None else None
        if staged_file_uid is not None:
            model_by_uid = self.repository.get_by_uid(staged_file_uid)
            if id is not None and model and model_by_uid and model.id != model_by_uid.id:
                raise AppError(
                    code="INVALID_ARGUMENT",
                    message="id and staged_file_uid do not match",
                    error_type="validation_error",
                )
            model = model_by_uid or model

        if model is None:
            raise AppError(
                code="STAGED_FILE_NOT_FOUND",
                message="staged file not found",
                error_type="not_found",
                details={"id": id, "staged_file_uid": staged_file_uid},
            )
        return model

    def _resolve_supported_mime_type(self, *, file_name: str, mime_type: str | None) -> str:
        """解析并校验可支持的 MIME 类型。"""

        resolved = infer_document_mime_type(file_name=file_name, provided_mime_type=mime_type)
        if not is_supported_document_mime_type(resolved):
            raise AppError(
                code="INVALID_ARGUMENT",
                message=supported_document_mime_type_message(),
                error_type="validation_error",
            )
        return resolved
