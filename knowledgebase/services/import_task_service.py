from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from knowledgebase.domain.exceptions import AppError
from knowledgebase.integrations.storage.file_storage import FileStorage
from knowledgebase.repositories.import_task_repository import ImportTaskRepository
from knowledgebase.schemas.import_task import (
    ImportTaskCancelInput,
    ImportTaskGetInput,
    ImportTaskOutput,
    ImportTaskSubmitInput,
)


class ImportTaskService:
    """批量文档导入任务服务。"""

    def __init__(self, repository: ImportTaskRepository) -> None:
        self.repository = repository
        self.storage = FileStorage()
        self._cleanup_after_commit_paths: list[str] = []

    def submit_task(self, payload: dict) -> ImportTaskOutput:
        """提交批量导入任务，并把原始文件落到任务暂存目录。"""

        try:
            data = ImportTaskSubmitInput.model_validate(payload)
        except ValidationError as exc:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="批量导入任务参数不合法",
                error_type="validation_error",
                details={"errors": exc.errors()},
            ) from exc

        if data.idempotency_key:
            existing = self.repository.get_by_idempotency_key(data.idempotency_key)
            if existing is not None:
                items = self.repository.list_items(existing.id)
                return ImportTaskOutput.from_model(existing, items=items)

        staged_file_paths: list[str] = []
        try:
            task = self.repository.create_task(
                priority=data.priority,
                total_items=len(data.items),
                request_id=data.request_id,
                operator=data.operator,
                trace_id=data.trace_id,
                idempotency_key=data.idempotency_key,
                max_attempts=data.max_attempts,
            )

            item_rows = []
            for index, item in enumerate(data.items, start=1):
                staged_file_uri, file_sha256 = self.storage.stage_task_pdf(
                    task_uid=task.task_uid,
                    item_no=index,
                    file_name=item.file_name,
                    file_content_base64=item.file_content_base64,
                )
                staged_file_paths.append(staged_file_uri)
                item_rows.append(
                    {
                        "task_id": task.id,
                        "item_no": index,
                        "status": "pending",
                        "priority": item.priority if item.priority is not None else data.priority,
                        "category_id": item.category_id,
                        "title": item.title,
                        "file_name": item.file_name,
                        "mime_type": item.mime_type,
                        "staged_file_uri": staged_file_uri,
                        "file_sha256": file_sha256,
                    }
                )

            items = self.repository.create_items(item_rows)
            task = self.repository.refresh_task_aggregate(task)
            return ImportTaskOutput.from_model(task, items=items)
        except Exception:
            # 任务提交失败时，主动清理已落盘的暂存文件，避免形成无主任务文件。
            for file_path in staged_file_paths:
                self.storage.delete_file(file_path)
            raise

    def get_task(self, payload: dict) -> ImportTaskOutput:
        """查询批量导入任务状态。"""

        try:
            data = ImportTaskGetInput.model_validate(payload)
        except ValidationError as exc:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="任务查询参数不合法",
                error_type="validation_error",
                details={"errors": exc.errors()},
            ) from exc

        task = self._resolve_task(id=data.id, task_uid=data.task_uid, include_items=data.include_items)
        items = list(task.items) if data.include_items else None
        return ImportTaskOutput.from_model(task, items=items)

    def cancel_task(self, payload: dict) -> ImportTaskOutput:
        """取消批量导入任务，未开始任务直接终止，运行中任务走协作式取消。"""

        try:
            data = ImportTaskCancelInput.model_validate(payload)
        except ValidationError as exc:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="任务取消参数不合法",
                error_type="validation_error",
                details={"errors": exc.errors()},
            ) from exc

        task = self._resolve_task(id=data.id, task_uid=data.task_uid, include_items=True)
        if task.status in {"success", "partial_success", "failed", "canceled"}:
            return ImportTaskOutput.from_model(task, items=list(task.items))

        if task.status == "queued":
            task = self.repository.mark_task_canceled_without_start(task)
            self._cleanup_after_commit_paths = [
                item.staged_file_uri
                for item in list(task.items)
                if getattr(item, "staged_file_uri", None)
            ]
            return ImportTaskOutput.from_model(task, items=list(task.items))

        task = self.repository.mark_cancel_requested(task)
        task = self.repository.refresh_task_aggregate(task)
        return ImportTaskOutput.from_model(task, items=list(task.items))

    def _resolve_task(
        self,
        *,
        id: int | None,
        task_uid: str | None,
        include_items: bool,
    ):
        """按主键或稳定任务标识解析任务。"""

        if id is None and task_uid is None:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="id or task_uid is required",
                error_type="validation_error",
            )

        task = None
        if id is not None:
            task = self.repository.get_by_id(id, include_items=include_items)
        if task_uid is not None:
            task_by_uid = self.repository.get_by_uid(task_uid, include_items=include_items)
            if id is not None and task and task_by_uid and task.id != task_by_uid.id:
                raise AppError(
                    code="INVALID_ARGUMENT",
                    message="id and task_uid do not match",
                    error_type="validation_error",
                )
            task = task_by_uid or task

        if task is None:
            raise AppError(
                code="IMPORT_TASK_NOT_FOUND",
                message="import task not found",
                error_type="not_found",
                details={"id": id, "task_uid": task_uid},
            )
        return task

    def _cleanup_items_staged_files(self, items: list[object]) -> None:
        """清理取消前尚未真正执行的任务暂存文件。"""

        for item in items:
            if getattr(item, "staged_file_uri", None):
                self.storage.delete_file(item.staged_file_uri)
                self._cleanup_task_dir_if_empty(item.staged_file_uri)

    def _cleanup_task_dir_if_empty(self, file_path: str) -> None:
        """如果任务目录已经空了，就顺手清理空目录，避免堆积。"""

        task_dir = Path(file_path).resolve().parent
        if task_dir.exists() and task_dir.is_dir() and not any(task_dir.iterdir()):
            task_dir.rmdir()

    def finalize_cancel_cleanup(self) -> None:
        """在数据库提交成功后，最终清理已取消未开始任务的暂存文件。"""

        for file_path in self._cleanup_after_commit_paths:
            self.storage.delete_file(file_path)
            self._cleanup_task_dir_if_empty(file_path)
        self._cleanup_after_commit_paths = []
