from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
import unittest

from knowledgebase.services.import_task_service import ImportTaskService


def build_task(*, status: str) -> SimpleNamespace:
    now = datetime.utcnow()
    return SimpleNamespace(
        id=1,
        task_uid="task-uid-1",
        task_type="document_import_batch",
        status=status,
        priority=50,
        cancel_requested=False,
        idempotency_key=None,
        request_id=None,
        operator=None,
        trace_id=None,
        total_items=1,
        pending_items=0,
        running_items=1 if status == "running" else 0,
        success_items=0,
        failed_items=0,
        canceled_items=0,
        progress_percent=0,
        attempt_count=1,
        max_attempts=3,
        started_at=now,
        finished_at=None,
        heartbeat_at=now,
        last_error=None,
        created_at=now,
        updated_at=now,
        items=[],
    )


class FakeImportTaskRepository:
    def __init__(self) -> None:
        self.mark_cancel_requested_called = False
        self.refresh_task_aggregate_called = False

    def mark_cancel_requested(self, task):
        self.mark_cancel_requested_called = True
        task.cancel_requested = True
        task.status = "cancel_requested"
        return task

    def refresh_task_aggregate(self, task):
        self.refresh_task_aggregate_called = True
        return task


class ImportTaskServiceUnitTestCase(unittest.TestCase):
    def test_cancel_running_task_returns_cancel_requested_immediately(self) -> None:
        repository = FakeImportTaskRepository()
        staged_file_repository = SimpleNamespace(session=SimpleNamespace())
        service = ImportTaskService(
            repository,
            category_repository=SimpleNamespace(),
            staged_file_repository=staged_file_repository,
        )
        running_task = build_task(status="running")
        service._resolve_task = lambda **_: running_task  # type: ignore[method-assign]

        result = service.cancel_task({"id": 1})

        self.assertTrue(repository.mark_cancel_requested_called)
        self.assertTrue(repository.refresh_task_aggregate_called)
        self.assertEqual(result.status, "cancel_requested")
        self.assertTrue(result.cancel_requested)
