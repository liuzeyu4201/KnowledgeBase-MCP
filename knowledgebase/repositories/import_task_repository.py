from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from knowledgebase.models.import_task import ImportTaskItemModel, ImportTaskModel


class ImportTaskRepository:
    """批量导入任务数据访问层。"""

    TERMINAL_TASK_STATUSES = {"success", "partial_success", "failed", "canceled"}
    TERMINAL_ITEM_STATUSES = {"success", "failed", "canceled"}

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, task_id: int, *, include_items: bool = False) -> ImportTaskModel | None:
        """按主键读取任务，可按需加载子项。"""

        stmt = select(ImportTaskModel).where(ImportTaskModel.id == task_id)
        if include_items:
            stmt = stmt.options(selectinload(ImportTaskModel.items))
        return self.session.scalar(stmt)

    def get_by_uid(self, task_uid: str, *, include_items: bool = False) -> ImportTaskModel | None:
        """按稳定任务标识读取任务。"""

        stmt = select(ImportTaskModel).where(ImportTaskModel.task_uid == task_uid)
        if include_items:
            stmt = stmt.options(selectinload(ImportTaskModel.items))
        return self.session.scalar(stmt)

    def get_by_idempotency_key(self, idempotency_key: str) -> ImportTaskModel | None:
        """按幂等键查询已有任务。"""

        stmt = select(ImportTaskModel).where(ImportTaskModel.idempotency_key == idempotency_key)
        return self.session.scalar(stmt)

    def create_task(
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
    ) -> ImportTaskModel:
        """创建任务主记录。"""

        now = datetime.utcnow()
        task = ImportTaskModel(
            task_type=task_type,
            status="queued",
            priority=priority,
            idempotency_key=idempotency_key,
            request_id=request_id,
            operator=operator,
            trace_id=trace_id,
            total_items=total_items,
            pending_items=total_items,
            progress_percent=0,
            max_attempts=max_attempts,
            created_at=now,
            updated_at=now,
        )
        self.session.add(task)
        self.session.flush()
        self.session.refresh(task)
        return task

    def create_items(self, rows: list[dict]) -> list[ImportTaskItemModel]:
        """批量创建任务子项。"""

        now = datetime.utcnow()
        items = [
            ImportTaskItemModel(
                **row,
                created_at=now,
                updated_at=now,
            )
            for row in rows
        ]
        self.session.add_all(items)
        self.session.flush()
        return items

    def list_items(self, task_id: int) -> list[ImportTaskItemModel]:
        """读取任务下全部子项。"""

        stmt = (
            select(ImportTaskItemModel)
            .where(ImportTaskItemModel.task_id == task_id)
            .order_by(ImportTaskItemModel.item_no.asc())
        )
        return list(self.session.scalars(stmt).all())

    def mark_cancel_requested(self, task: ImportTaskModel) -> ImportTaskModel:
        """标记任务已收到取消请求。"""

        task.cancel_requested = True
        if task.status == "queued":
            task.status = "cancel_requested"
        self.session.add(task)
        self.session.flush()
        self.session.refresh(task)
        return task

    def mark_task_canceled_without_start(self, task: ImportTaskModel) -> ImportTaskModel:
        """对于尚未执行的任务，直接终止并取消全部待执行子项。"""

        now = datetime.utcnow()
        task.cancel_requested = True
        task.status = "canceled"
        task.pending_items = 0
        task.running_items = 0
        task.canceled_items = task.total_items
        task.progress_percent = 100
        task.finished_at = now
        self.session.add(task)
        self.session.flush()

        stmt = select(ImportTaskItemModel).where(
            ImportTaskItemModel.task_id == task.id,
            ImportTaskItemModel.status == "pending",
        )
        items = list(self.session.scalars(stmt).all())
        for item in items:
            item.status = "canceled"
            item.finished_at = now
            item.last_error = "task canceled before execution"
            self.session.add(item)

        self.session.flush()
        self.session.refresh(task)
        return task

    def claim_next_task(self, *, lease_token: str, lease_seconds: int) -> ImportTaskModel | None:
        """按优先级抢占下一个可执行任务，并写入租约信息。"""

        now = datetime.utcnow()
        stmt: Select[tuple[ImportTaskModel]] = (
            select(ImportTaskModel)
            .where(
                or_(
                    ImportTaskModel.status == "queued",
                    (
                        ImportTaskModel.status.in_(("running", "cancel_requested"))
                        & (ImportTaskModel.lease_expires_at.is_not(None))
                        & (ImportTaskModel.lease_expires_at < now)
                    ),
                ),
            )
            .order_by(
                ImportTaskModel.priority.desc(),
                ImportTaskModel.created_at.asc(),
                ImportTaskModel.id.asc(),
            )
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        task = self.session.scalar(stmt)
        if task is None:
            return None

        task.lease_token = lease_token
        task.lease_expires_at = now + timedelta(seconds=lease_seconds)
        task.heartbeat_at = now
        task.started_at = task.started_at or now
        task.attempt_count += 1
        task.status = "cancel_requested" if task.cancel_requested else "running"

        self.session.add(task)
        self.session.flush()
        self.session.refresh(task)
        return task

    def heartbeat_task(
        self,
        *,
        task_id: int,
        lease_token: str,
        lease_seconds: int,
    ) -> ImportTaskModel | None:
        """续租任务，避免其他 worker 抢占仍在执行的任务。"""

        stmt = (
            select(ImportTaskModel)
            .where(
                ImportTaskModel.id == task_id,
                ImportTaskModel.lease_token == lease_token,
            )
            .with_for_update()
        )
        task = self.session.scalar(stmt)
        if task is None:
            return None

        now = datetime.utcnow()
        task.heartbeat_at = now
        task.lease_expires_at = now + timedelta(seconds=lease_seconds)
        self.session.add(task)
        self.session.flush()
        self.session.refresh(task)
        return task

    def claim_next_item(
        self,
        *,
        task_id: int,
        lease_token: str,
        lease_seconds: int,
    ) -> ImportTaskItemModel | None:
        """抢占任务下一个待执行子项，支持租约过期后重新接管。"""

        now = datetime.utcnow()
        stmt = (
            select(ImportTaskItemModel)
            .where(
                ImportTaskItemModel.task_id == task_id,
                or_(
                    ImportTaskItemModel.status == "pending",
                    (
                        (ImportTaskItemModel.status == "running")
                        & (ImportTaskItemModel.lease_expires_at.is_not(None))
                        & (ImportTaskItemModel.lease_expires_at < now)
                    ),
                ),
            )
            .order_by(
                ImportTaskItemModel.priority.desc(),
                ImportTaskItemModel.item_no.asc(),
                ImportTaskItemModel.id.asc(),
            )
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        item = self.session.scalar(stmt)
        if item is None:
            return None

        item.status = "running"
        item.attempt_count += 1
        item.started_at = item.started_at or now
        item.lease_token = lease_token
        item.lease_expires_at = now + timedelta(seconds=lease_seconds)
        self.session.add(item)
        self.session.flush()
        self.session.refresh(item)
        return item

    def heartbeat_item(
        self,
        *,
        item_id: int,
        lease_token: str,
        lease_seconds: int,
    ) -> ImportTaskItemModel | None:
        """续租子任务，避免长文档导入时被其他 worker 重复接管。"""

        stmt = (
            select(ImportTaskItemModel)
            .where(
                ImportTaskItemModel.id == item_id,
                ImportTaskItemModel.lease_token == lease_token,
                ImportTaskItemModel.status == "running",
            )
            .with_for_update()
        )
        item = self.session.scalar(stmt)
        if item is None:
            return None

        now = datetime.utcnow()
        item.lease_expires_at = now + timedelta(seconds=lease_seconds)
        self.session.add(item)
        self.session.flush()
        self.session.refresh(item)
        return item

    def get_item_for_execution(
        self,
        *,
        task_id: int,
        item_id: int,
        lease_token: str,
    ) -> ImportTaskItemModel | None:
        """校验当前 worker 仍然持有该子项执行权。"""

        stmt = (
            select(ImportTaskItemModel)
            .where(
                ImportTaskItemModel.id == item_id,
                ImportTaskItemModel.task_id == task_id,
                ImportTaskItemModel.lease_token == lease_token,
                ImportTaskItemModel.status == "running",
            )
        )
        return self.session.scalar(stmt)

    def mark_item_success(
        self,
        *,
        item: ImportTaskItemModel,
        document_id: int,
        document_uid: str,
    ) -> ImportTaskItemModel:
        """标记子任务成功。"""

        item.status = "success"
        item.document_id = document_id
        item.document_uid = document_uid
        item.finished_at = datetime.utcnow()
        item.last_error = None
        item.lease_token = None
        item.lease_expires_at = None
        self.session.add(item)
        self.session.flush()
        self.session.refresh(item)
        return item

    def mark_item_failed(self, *, item: ImportTaskItemModel, error_message: str) -> ImportTaskItemModel:
        """标记子任务失败。"""

        item.status = "failed"
        item.finished_at = datetime.utcnow()
        item.last_error = error_message
        item.lease_token = None
        item.lease_expires_at = None
        self.session.add(item)
        self.session.flush()
        self.session.refresh(item)
        return item

    def mark_item_canceled(self, *, item: ImportTaskItemModel, reason: str) -> ImportTaskItemModel:
        """标记子任务取消。"""

        item.status = "canceled"
        item.finished_at = datetime.utcnow()
        item.last_error = reason
        item.lease_token = None
        item.lease_expires_at = None
        self.session.add(item)
        self.session.flush()
        self.session.refresh(item)
        return item

    def requeue_item(self, *, item: ImportTaskItemModel, error_message: str) -> ImportTaskItemModel:
        """在未超过最大尝试次数时，把子任务重新放回待执行队列。"""

        item.status = "pending"
        item.last_error = error_message
        item.lease_token = None
        item.lease_expires_at = None
        self.session.add(item)
        self.session.flush()
        self.session.refresh(item)
        return item

    def cancel_pending_items(self, *, task_id: int, reason: str) -> int:
        """把任务下尚未执行的子项统一标记为取消。"""

        now = datetime.utcnow()
        stmt = (
            select(ImportTaskItemModel)
            .where(
                ImportTaskItemModel.task_id == task_id,
                ImportTaskItemModel.status == "pending",
            )
            .with_for_update(skip_locked=True)
        )
        items = list(self.session.scalars(stmt).all())
        for item in items:
            item.status = "canceled"
            item.finished_at = now
            item.last_error = reason
            self.session.add(item)
        self.session.flush()
        return len(items)

    def refresh_task_aggregate(self, task: ImportTaskModel) -> ImportTaskModel:
        """根据子任务状态聚合主任务进度与终态。"""

        counts = self._count_item_statuses(task.id)
        task.pending_items = counts["pending"]
        task.running_items = counts["running"]
        task.success_items = counts["success"]
        task.failed_items = counts["failed"]
        task.canceled_items = counts["canceled"]

        finished_items = task.success_items + task.failed_items + task.canceled_items
        task.progress_percent = round((finished_items / task.total_items) * 100, 2) if task.total_items else 100

        if task.pending_items == 0 and task.running_items == 0:
            task.finished_at = datetime.utcnow()
            task.lease_token = None
            task.lease_expires_at = None
            task.heartbeat_at = None
            if task.cancel_requested:
                task.status = "canceled"
            elif task.failed_items > 0 and task.success_items > 0:
                task.status = "partial_success"
            elif task.failed_items > 0:
                task.status = "failed"
            else:
                task.status = "success"
        else:
            if task.cancel_requested:
                task.status = "cancel_requested"
            elif task.started_at is None and task.running_items == 0:
                task.status = "queued"
            else:
                task.status = "running"

        self.session.add(task)
        self.session.flush()
        self.session.refresh(task)
        return task

    def release_task(self, task: ImportTaskModel) -> ImportTaskModel:
        """释放任务租约，但保留当前状态。"""

        task.lease_token = None
        task.lease_expires_at = None
        task.heartbeat_at = None
        self.session.add(task)
        self.session.flush()
        self.session.refresh(task)
        return task

    def _count_item_statuses(self, task_id: int) -> dict[str, int]:
        """统计任务下各子任务状态数量。"""

        stmt = (
            select(ImportTaskItemModel.status, func.count(ImportTaskItemModel.id))
            .where(ImportTaskItemModel.task_id == task_id)
            .group_by(ImportTaskItemModel.status)
        )
        rows = self.session.execute(stmt).all()
        counts = {
            "pending": 0,
            "running": 0,
            "success": 0,
            "failed": 0,
            "canceled": 0,
        }
        for status, count in rows:
            counts[status] = count
        return counts
