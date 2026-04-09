from __future__ import annotations

import time

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from knowledgebase.db.session import session_scope
from knowledgebase.domain.exceptions import AppError
from knowledgebase.repositories.category_repository import CategoryRepository
from knowledgebase.repositories.import_task_repository import ImportTaskRepository
from knowledgebase.repositories.staged_file_repository import StagedFileRepository
from knowledgebase.schemas.import_task import (
    ImportTaskCancelInput,
    ImportTaskGetInput,
    ImportTaskOutput,
    ImportTaskSubmitFromStagedInput,
    ImportTaskSubmitInput,
)
from knowledgebase.services.staged_file_service import StagedFileService


class ImportTaskService:
    """批量文档导入任务服务。"""

    CANCEL_SETTLE_TIMEOUT_SECONDS = 1.5
    CANCEL_SETTLE_POLL_INTERVAL_SECONDS = 0.1

    def __init__(
        self,
        repository: ImportTaskRepository,
        *,
        category_repository: CategoryRepository,
        staged_file_repository: StagedFileRepository,
    ) -> None:
        self.repository = repository
        self.category_repository = category_repository
        self.staged_file_repository = staged_file_repository
        self.staged_file_service = StagedFileService(staged_file_repository)
        self._cleanup_after_commit_ids: list[int] = []

    def submit_task(self, payload: dict) -> ImportTaskOutput:
        """兼容旧入口：接收 base64 文档内容并提交批量异步导入任务。"""

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

        self._validate_submit_categories(data)

        created_staged_file_ids: list[int] = []
        try:
            task = self._create_task_with_idempotency_fallback(
                priority=data.priority,
                total_items=len(data.items),
                request_id=data.request_id,
                operator=data.operator,
                trace_id=data.trace_id,
                idempotency_key=data.idempotency_key,
                max_attempts=data.max_attempts,
            )
            if isinstance(task, ImportTaskOutput):
                return task

            item_rows = []
            for index, item in enumerate(data.items, start=1):
                file_bytes = self.staged_file_service.storage.decode_base64_file(item.file_content_base64)
                staged_file = self.staged_file_service.create_from_bytes(
                    file_name=item.file_name,
                    file_bytes=file_bytes,
                    mime_type=item.mime_type,
                )
                created_staged_file_ids.append(staged_file.id)
                staged_model = self.staged_file_repository.get_for_update(staged_file.id)
                if staged_model is not None:
                    self.staged_file_repository.link_task(staged_model, task_id=task.id)
                item_rows.append(
                    {
                        "task_id": task.id,
                        "item_no": index,
                        "status": "pending",
                        "priority": item.priority if item.priority is not None else data.priority,
                        "category_id": item.category_id,
                        "title": item.title,
                        "file_name": staged_file.file_name,
                        "mime_type": staged_file.mime_type,
                        "staged_file_id": staged_file.id,
                        "file_sha256": staged_file.file_sha256,
                    }
                )

            items = self.repository.create_items(item_rows)
            return ImportTaskOutput.from_model(task, items=items)
        except Exception:
            for staged_file_id in created_staged_file_ids:
                self.staged_file_service.delete_staged_file_by_id(staged_file_id)
            raise

    def submit_task_from_staged(self, payload: dict) -> ImportTaskOutput:
        """标准入口：基于既有暂存文件提交批量异步导入任务。"""

        try:
            data = ImportTaskSubmitFromStagedInput.model_validate(payload)
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

        self._validate_submit_categories_from_staged(data)
        self._validate_staged_files_for_submit(data)

        task = self._create_task_with_idempotency_fallback(
            priority=data.priority,
            total_items=len(data.items),
            request_id=data.request_id,
            operator=data.operator,
            trace_id=data.trace_id,
            idempotency_key=data.idempotency_key,
            max_attempts=data.max_attempts,
        )
        if isinstance(task, ImportTaskOutput):
            return task

        item_rows = []
        for index, item in enumerate(data.items, start=1):
            staged_file = self.staged_file_repository.get_for_update(item.staged_file_id)
            if staged_file is None:
                raise AppError(
                    code="STAGED_FILE_NOT_FOUND",
                    message="staged file not found",
                    error_type="not_found",
                    details={"staged_file_id": item.staged_file_id},
                )
            self.staged_file_repository.link_task(staged_file, task_id=task.id)
            item_rows.append(
                {
                    "task_id": task.id,
                    "item_no": index,
                    "status": "pending",
                    "priority": item.priority if item.priority is not None else data.priority,
                    "category_id": item.category_id,
                    "title": item.title,
                    "file_name": staged_file.file_name,
                    "mime_type": staged_file.mime_type,
                    "staged_file_id": staged_file.id,
                    "file_sha256": staged_file.file_sha256,
                }
            )
        items = self.repository.create_items(item_rows)
        return ImportTaskOutput.from_model(task, items=items)

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
        """取消批量文档导入任务，未开始任务直接终止，运行中任务走协作式取消。"""

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
            self._cleanup_after_commit_ids = [
                item.staged_file_id
                for item in list(task.items)
                if getattr(item, "staged_file_id", None)
            ]
            return ImportTaskOutput.from_model(task, items=list(task.items))

        task = self.repository.mark_cancel_requested(task)
        task = self.repository.refresh_task_aggregate(task)
        task = self._wait_for_cancel_terminal_state(task.id)
        return ImportTaskOutput.from_model(task, items=list(task.items))

    def finalize_cancel_cleanup(self) -> None:
        """在数据库提交成功后，最终清理已取消未开始任务对应的暂存文件。"""

        for staged_file_id in self._cleanup_after_commit_ids:
            with session_scope() as session:
                service = StagedFileService(StagedFileRepository(session))
                service.delete_staged_file_by_id(staged_file_id)
        self._cleanup_after_commit_ids = []

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

        task_by_id = self.repository.get_by_id(id, include_items=include_items) if id is not None else None
        task_by_uid = self.repository.get_by_uid(task_uid, include_items=include_items) if task_uid is not None else None

        if id is not None and task_uid is not None:
            if task_by_id is None or task_by_uid is None or task_by_id.id != task_by_uid.id:
                raise AppError(
                    code="INVALID_ARGUMENT",
                    message="id and task_uid do not match",
                    error_type="validation_error",
                )
            task = task_by_id
        else:
            task = task_by_id or task_by_uid

        if task is None:
            raise AppError(
                code="IMPORT_TASK_NOT_FOUND",
                message="import task not found",
                error_type="not_found",
                details={"id": id, "task_uid": task_uid},
            )
        return task

    def _wait_for_cancel_terminal_state(self, task_id: int):
        """对快速收敛的取消请求做短暂轮询，尽量统一返回最终状态。"""

        deadline = time.monotonic() + self.CANCEL_SETTLE_TIMEOUT_SECONDS
        task = self.repository.get_by_id(task_id, include_items=True)
        while task is not None and task.status == "cancel_requested" and time.monotonic() < deadline:
            time.sleep(self.CANCEL_SETTLE_POLL_INTERVAL_SECONDS)
            self.repository.session.expire_all()
            task = self.repository.get_by_id(task_id, include_items=True)
        return task if task is not None else self._resolve_task(id=task_id, task_uid=None, include_items=True)

    def _validate_submit_categories(self, data: ImportTaskSubmitInput) -> None:
        """提交前同步校验全部分类，避免把必然失败的任务写入任务表。"""

        checked_category_ids: set[int] = set()
        for item in data.items:
            if item.category_id in checked_category_ids:
                continue
            category = self.category_repository.get_by_id(item.category_id)
            if category is None:
                raise AppError(
                    code="CATEGORY_NOT_FOUND",
                    message="category not found",
                    error_type="not_found",
                    details={"category_id": item.category_id},
                )
            checked_category_ids.add(item.category_id)

    def _validate_submit_categories_from_staged(self, data: ImportTaskSubmitFromStagedInput) -> None:
        """标准路径提交前同步校验全部分类。"""

        checked_category_ids: set[int] = set()
        for item in data.items:
            if item.category_id in checked_category_ids:
                continue
            category = self.category_repository.get_by_id(item.category_id)
            if category is None:
                raise AppError(
                    code="CATEGORY_NOT_FOUND",
                    message="category not found",
                    error_type="not_found",
                    details={"category_id": item.category_id},
                )
            checked_category_ids.add(item.category_id)

    def _validate_staged_files_for_submit(self, data: ImportTaskSubmitFromStagedInput) -> None:
        """校验全部暂存文件都可被当前批量任务消费。"""

        checked_staged_file_ids: set[int] = set()
        for item in data.items:
            if item.staged_file_id in checked_staged_file_ids:
                continue
            staged_file = self.staged_file_repository.get_by_id(item.staged_file_id)
            if staged_file is None:
                raise AppError(
                    code="STAGED_FILE_NOT_FOUND",
                    message="staged file not found",
                    error_type="not_found",
                    details={"staged_file_id": item.staged_file_id},
                )
            if staged_file.status not in {"uploaded", "failed"}:
                raise AppError(
                    code="STAGED_FILE_STATUS_INVALID",
                    message="staged file status does not allow batch submit",
                    error_type="business_error",
                    details={"staged_file_id": item.staged_file_id, "status": staged_file.status},
                )
            checked_staged_file_ids.add(item.staged_file_id)

    def _create_task_with_idempotency_fallback(
        self,
        *,
        priority: int,
        total_items: int,
        request_id: str | None,
        operator: str | None,
        trace_id: str | None,
        idempotency_key: str | None,
        max_attempts: int,
    ):
        """创建任务主记录，并在并发幂等冲突时返回已有任务。"""

        try:
            return self.repository.create_task(
                priority=priority,
                total_items=total_items,
                request_id=request_id,
                operator=operator,
                trace_id=trace_id,
                idempotency_key=idempotency_key,
                max_attempts=max_attempts,
            )
        except IntegrityError as exc:
            if not idempotency_key:
                raise
            self.repository.session.rollback()
            existing = self.repository.get_by_idempotency_key(idempotency_key)
            if existing is None:
                raise exc
            items = self.repository.list_items(existing.id)
            return ImportTaskOutput.from_model(existing, items=items)
