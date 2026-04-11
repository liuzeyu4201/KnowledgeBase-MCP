from __future__ import annotations

import time
from uuid import uuid4

from knowledgebase.app.config import get_settings
from knowledgebase.db.bootstrap import init_schema
from knowledgebase.db.session import session_scope
from knowledgebase.domain.exceptions import AppError
from knowledgebase.integrations.storage.file_storage import FileStorage
from knowledgebase.repositories.category_repository import CategoryRepository
from knowledgebase.repositories.chunk_repository import ChunkRepository
from knowledgebase.repositories.document_repository import DocumentRepository
from knowledgebase.repositories.import_task_repository import ImportTaskRepository
from knowledgebase.repositories.staged_file_repository import StagedFileRepository
from knowledgebase.repositories.storage_gc_task_repository import StorageGCTaskRepository
from knowledgebase.services.staged_file_service import StagedFileService
from knowledgebase.services.document_service import DocumentService


class ImportTaskWorker:
    """批量文档导入后台 worker。"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.worker_token = uuid4().hex
        self.storage = FileStorage()

    def run_forever(self) -> None:
        """持续轮询 PostgreSQL 任务表并执行批量导入任务。"""

        if self.settings.auto_init_schema:
            init_schema()

        while True:
            expired_claimed = 0
            for _ in range(self.settings.storage_gc_batch_size):
                if not self._cleanup_next_expired_staged_file():
                    break
                expired_claimed += 1

            gc_claimed = 0
            for _ in range(self.settings.storage_gc_batch_size):
                gc_task_info = self._claim_next_gc_task()
                if gc_task_info is None:
                    break
                gc_claimed += 1
                self._process_gc_task(
                    task_id=gc_task_info["id"],
                    lease_token=gc_task_info["lease_token"],
                )

            claimed = 0
            for _ in range(self.settings.task_worker_batch_size):
                task_info = self._claim_next_task()
                if task_info is None:
                    break
                claimed += 1
                self._process_task(task_id=task_info["id"], lease_token=task_info["lease_token"])

            if claimed == 0 and gc_claimed == 0 and expired_claimed == 0:
                time.sleep(self.settings.task_worker_poll_interval_seconds)

    def _cleanup_next_expired_staged_file(self) -> bool:
        """清理一条已过期但未消费的暂存文件。"""

        with session_scope() as session:
            repository = StagedFileRepository(session)
            staged_file = repository.claim_next_expired_for_cleanup()
            if staged_file is None:
                return False

            service = StagedFileService(repository)
            service.delete_staged_file_by_id(staged_file.id)
            return True

    def _claim_next_gc_task(self) -> dict[str, str | int] | None:
        """抢占下一个待执行的对象清理任务。"""

        with session_scope() as session:
            repository = StorageGCTaskRepository(session)
            task = repository.claim_next_task(
                lease_token=self.worker_token,
                lease_seconds=self.settings.task_worker_lease_seconds,
            )
            if task is None:
                return None
            return {
                "id": task.id,
                "lease_token": task.lease_token or self.worker_token,
            }

    def _process_gc_task(self, *, task_id: int, lease_token: str) -> None:
        """执行单个对象删除任务。"""

        with session_scope() as session:
            repository = StorageGCTaskRepository(session)
            task = repository.get_for_execution(task_id=task_id, lease_token=lease_token)
            if task is None:
                return
            try:
                self.storage.delete_file(task.storage_uri)
                repository.mark_success(task)
            except Exception as exc:  # noqa: BLE001
                repository.mark_failed(
                    task,
                    error_message=str(exc),
                    retry_delay_seconds=30,
                )

    def _claim_next_task(self) -> dict[str, str | int] | None:
        """抢占下一个待执行任务。"""

        with session_scope() as session:
            repository = ImportTaskRepository(session)
            task = repository.claim_next_task(
                lease_token=self.worker_token,
                lease_seconds=self.settings.task_worker_lease_seconds,
            )
            if task is None:
                return None
            return {
                "id": task.id,
                "lease_token": task.lease_token or self.worker_token,
            }

    def _process_task(self, *, task_id: int, lease_token: str) -> None:
        """串行处理单个批量任务下的全部文档导入子项。"""

        while True:
            task = self._prepare_task_cycle(task_id=task_id, lease_token=lease_token)
            if task is None:
                return
            if task.status in ImportTaskRepository.TERMINAL_TASK_STATUSES:
                return

            item_info = self._claim_next_item(task_id=task_id, lease_token=lease_token)
            if item_info is None:
                with session_scope() as session:
                    repository = ImportTaskRepository(session)
                    task = repository.get_by_id(task_id)
                    if task is None:
                        return
                    repository.refresh_task_aggregate(task)
                return

            self._process_item(
                task_id=task_id,
                item_id=item_info["id"],
                lease_token=lease_token,
            )

    def _prepare_task_cycle(self, *, task_id: int, lease_token: str):
        """在每轮处理开始前续租任务并处理取消请求。"""

        with session_scope() as session:
            repository = ImportTaskRepository(session)
            task = repository.heartbeat_task(
                task_id=task_id,
                lease_token=lease_token,
                lease_seconds=self.settings.task_worker_lease_seconds,
            )
            if task is None:
                return None

            if task.cancel_requested:
                repository.cancel_pending_items(
                    task_id=task.id,
                    reason="task canceled by operator",
                )
                repository.refresh_task_aggregate(task)
            return task

    def _claim_next_item(self, *, task_id: int, lease_token: str) -> dict[str, int] | None:
        """抢占任务下一个可执行子项。"""

        with session_scope() as session:
            repository = ImportTaskRepository(session)
            item = repository.claim_next_item(
                task_id=task_id,
                lease_token=lease_token,
                lease_seconds=self.settings.task_worker_lease_seconds,
            )
            if item is None:
                return None
            return {"id": item.id}

    def _process_item(self, *, task_id: int, item_id: int, lease_token: str) -> None:
        """执行单个文档导入子项，并维护任务状态与重试逻辑。"""

        document_service: DocumentService | None = None
        with session_scope() as session:
            task_repository = ImportTaskRepository(session)
            item = task_repository.get_item_for_execution(
                task_id=task_id,
                item_id=item_id,
                lease_token=lease_token,
            )
            task = task_repository.get_by_id(task_id)
            if item is None or task is None:
                return

            document_service = DocumentService(
                category_repository=CategoryRepository(session),
                document_repository=DocumentRepository(session),
                chunk_repository=ChunkRepository(session),
                staged_file_repository=StagedFileRepository(session),
            )

            try:
                result = document_service.import_document_from_staged(
                    {
                        "category_id": item.category_id,
                        "title": item.title,
                        "staged_file_id": item.staged_file_id,
                        "request_id": task.request_id,
                        "operator": task.operator,
                        "trace_id": task.trace_id,
                    },
                    cancellation_checker=self._build_cancellation_checker(
                        task_id=task_id,
                        item_id=item_id,
                        lease_token=lease_token,
                    ),
                )
                task_repository.mark_item_success(
                    item=item,
                    document_id=result["document"]["id"],
                    document_uid=result["document"]["document_uid"],
                )
                task.last_error = None
            except AppError as exc:
                self._handle_item_error(
                    task_repository=task_repository,
                    task=task,
                    item=item,
                    error=exc,
                )
            except Exception as exc:  # noqa: BLE001
                self._handle_item_error(
                    task_repository=task_repository,
                    task=task,
                    item=item,
                    error=AppError(
                        code="DOCUMENT_IMPORT_FAILED",
                        message="document import failed in worker",
                        error_type="system_error",
                        details={"error": str(exc)},
                    ),
                )

            task_repository.refresh_task_aggregate(task)
        if document_service is not None:
            document_service.finalize_post_commit_cleanup()

    def _handle_item_error(
        self,
        *,
        task_repository: ImportTaskRepository,
        task,
        item,
        error: AppError,
    ) -> None:
        """根据错误类型和重试次数更新子任务状态。"""

        task.last_error = error.message
        if error.code == "TASK_CANCELED":
            task_repository.mark_item_canceled(item=item, reason=error.message)
            return

        if item.attempt_count < task.max_attempts:
            task_repository.requeue_item(item=item, error_message=error.message)
            return

        task_repository.mark_item_failed(item=item, error_message=error.message)

    def _build_cancellation_checker(
        self,
        *,
        task_id: int,
        item_id: int,
        lease_token: str,
    ):
        """构造协作式取消检查器，并在检查点顺便续租任务和子项。"""

        last_heartbeat_monotonic = 0.0

        def checker() -> bool:
            nonlocal last_heartbeat_monotonic

            now_monotonic = time.monotonic()
            should_heartbeat = (
                now_monotonic - last_heartbeat_monotonic
                >= self.settings.task_worker_heartbeat_interval_seconds
            )

            with session_scope() as session:
                repository = ImportTaskRepository(session)
                task = repository.heartbeat_task(
                    task_id=task_id,
                    lease_token=lease_token,
                    lease_seconds=self.settings.task_worker_lease_seconds,
                )
                if task is None:
                    return True

                if should_heartbeat:
                    item = repository.heartbeat_item(
                        item_id=item_id,
                        lease_token=lease_token,
                        lease_seconds=self.settings.task_worker_lease_seconds,
                    )
                    if item is None:
                        return True
                    last_heartbeat_monotonic = now_monotonic

                return task.cancel_requested

        return checker


def run() -> None:
    """启动批量文档导入后台 worker。"""

    ImportTaskWorker().run_forever()


if __name__ == "__main__":
    run()
