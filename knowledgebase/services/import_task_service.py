from __future__ import annotations

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from knowledgebase.db.session import session_scope
from knowledgebase.domain.exceptions import AppError
from knowledgebase.repositories.category_repository import CategoryRepository
from knowledgebase.repositories.document_repository import DocumentRepository
from knowledgebase.repositories.import_task_repository import ImportTaskRepository
from knowledgebase.repositories.staged_file_repository import StagedFileRepository
from knowledgebase.schemas.import_task import (
    ImportTaskCancelInput,
    ImportTaskGetInput,
    ImportTaskOutput,
    ImportTaskSubmitFromStagedInput,
    ImportTaskSubmitUpdateFromStagedInput,
)
from knowledgebase.services.staged_file_service import StagedFileService


class ImportTaskService:
    """批量文档导入任务服务。"""

    def __init__(
        self,
        repository: ImportTaskRepository,
        *,
        category_repository: CategoryRepository,
        staged_file_repository: StagedFileRepository,
        document_repository: DocumentRepository | None = None,
    ) -> None:
        self.repository = repository
        self.category_repository = category_repository
        self.staged_file_repository = staged_file_repository
        self.document_repository = document_repository
        self.staged_file_service = StagedFileService(staged_file_repository)
        self._cleanup_after_commit_ids: list[int] = []

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
            task_type="document_import_batch",
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
                self._build_staged_file_item_row(
                    task_id=task.id,
                    item_no=index,
                    priority=item.priority if item.priority is not None else data.priority,
                    category_id=item.category_id,
                    title=item.title,
                    staged_file=staged_file,
                )
            )
        items = self.repository.create_items(item_rows)
        return ImportTaskOutput.from_model(task, items=items)

    def submit_update_task_from_staged(self, payload: dict) -> ImportTaskOutput:
        """提交单文档异步更新任务。"""

        try:
            data = ImportTaskSubmitUpdateFromStagedInput.model_validate(payload)
        except ValidationError as exc:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="单文档更新任务参数不合法",
                error_type="validation_error",
                details={"errors": exc.errors()},
            ) from exc

        document = self._resolve_document(id=data.id, document_uid=data.document_uid)
        if data.category_id is not None:
            self._validate_category_exists(data.category_id)
        self._validate_staged_file_for_submit(data.staged_file_id)

        task = self._create_task_with_idempotency_fallback(
            task_type="document_update_batch",
            priority=data.priority,
            total_items=1,
            request_id=data.request_id,
            operator=data.operator,
            trace_id=data.trace_id,
            idempotency_key=data.idempotency_key,
            max_attempts=data.max_attempts,
        )
        if isinstance(task, ImportTaskOutput):
            return task

        staged_file = self.staged_file_repository.get_for_update(data.staged_file_id)
        if staged_file is None:
            raise AppError(
                code="STAGED_FILE_NOT_FOUND",
                message="staged file not found",
                error_type="not_found",
                details={"staged_file_id": data.staged_file_id},
            )
        self.staged_file_repository.link_task(staged_file, task_id=task.id)
        items = self.repository.create_items(
            [
                {
                    **self._build_staged_file_item_row(
                        task_id=task.id,
                        item_no=1,
                        priority=data.priority,
                        category_id=data.category_id or document.category_id,
                        title=data.title or document.title,
                        staged_file=staged_file,
                    ),
                    "document_id": document.id,
                    "document_uid": document.document_uid,
                }
            ]
        )
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
        """取消批量文档导入任务，未开始任务直接终止，运行中任务立即记录取消意图。"""

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

    def _validate_submit_categories_from_staged(self, data: ImportTaskSubmitFromStagedInput) -> None:
        """标准路径提交前同步校验全部分类。"""

        checked_category_ids: set[int] = set()
        for item in data.items:
            if item.category_id in checked_category_ids:
                continue
            self._validate_category_exists(item.category_id)
            checked_category_ids.add(item.category_id)

    def _validate_staged_files_for_submit(self, data: ImportTaskSubmitFromStagedInput) -> None:
        """校验全部暂存文件都可被当前批量任务消费。"""

        checked_staged_file_ids: set[int] = set()
        for item in data.items:
            if item.staged_file_id in checked_staged_file_ids:
                continue
            self._validate_staged_file_for_submit(item.staged_file_id)
            checked_staged_file_ids.add(item.staged_file_id)

    def _create_task_with_idempotency_fallback(
        self,
        *,
        task_type: str,
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
                task_type=task_type,
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

    def _validate_category_exists(self, category_id: int) -> None:
        """校验分类存在。"""

        category = self.category_repository.get_by_id(category_id)
        if category is None:
            raise AppError(
                code="CATEGORY_NOT_FOUND",
                message="category not found",
                error_type="not_found",
                details={"category_id": category_id},
            )

    def _validate_staged_file_for_submit(self, staged_file_id: int) -> None:
        """校验暂存文件可被后台任务消费。"""

        staged_file = self.staged_file_repository.get_by_id(staged_file_id)
        if staged_file is None:
            raise AppError(
                code="STAGED_FILE_NOT_FOUND",
                message="staged file not found",
                error_type="not_found",
                details={"staged_file_id": staged_file_id},
            )
        if staged_file.status not in {"uploaded", "failed"}:
            raise AppError(
                code="STAGED_FILE_STATUS_INVALID",
                message="staged file status does not allow batch submit",
                error_type="business_error",
                details={"staged_file_id": staged_file_id, "status": staged_file.status},
            )

    def _resolve_document(self, *, id: int | None, document_uid: str | None):
        """解析异步更新任务的目标文档。"""

        if self.document_repository is None:
            raise RuntimeError("document_repository is required for update task submission")

        if id is None and document_uid is None:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="id or document_uid is required",
                error_type="validation_error",
            )

        document_by_id = self.document_repository.get_by_id(id) if id is not None else None
        document_by_uid = self.document_repository.get_by_uid(document_uid) if document_uid is not None else None

        if id is not None and document_uid is not None:
            if document_by_id is None or document_by_uid is None or document_by_id.id != document_by_uid.id:
                raise AppError(
                    code="INVALID_ARGUMENT",
                    message="id and document_uid do not match",
                    error_type="validation_error",
                )
            document = document_by_id
        else:
            document = document_by_id or document_by_uid

        if document is None:
            raise AppError(
                code="DOCUMENT_NOT_FOUND",
                message="document not found",
                error_type="not_found",
                details={"id": id, "document_uid": document_uid},
            )
        return document

    def _build_staged_file_item_row(
        self,
        *,
        task_id: int,
        item_no: int,
        priority: int,
        category_id: int,
        title: str,
        staged_file,
    ) -> dict:
        """构造基于 staged_file 的任务子项。"""

        return {
            "task_id": task_id,
            "item_no": item_no,
            "status": "pending",
            "priority": priority,
            "category_id": category_id,
            "title": title,
            "file_name": staged_file.file_name,
            "mime_type": staged_file.mime_type,
            "staged_file_id": staged_file.id,
            "file_sha256": staged_file.file_sha256,
        }
