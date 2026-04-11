from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from knowledgebase.models.storage_gc_task import StorageGCTaskModel


class StorageGCTaskRepository:
    """对象存储清理任务仓储。"""

    TERMINAL_STATUSES = {"success", "failed"}

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_delete_task(
        self,
        *,
        resource_type: str,
        resource_id: int | None,
        storage_backend: str,
        storage_uri: str,
        max_retry_count: int,
    ) -> StorageGCTaskModel:
        model = StorageGCTaskModel(
            resource_type=resource_type,
            resource_id=resource_id,
            storage_backend=storage_backend,
            storage_uri=storage_uri,
            action="delete",
            status="pending",
            retry_count=0,
            max_retry_count=max_retry_count,
            next_retry_at=datetime.utcnow(),
        )
        self.session.add(model)
        self.session.flush()
        self.session.refresh(model)
        return model

    def claim_next_task(
        self,
        *,
        lease_token: str,
        lease_seconds: int,
    ) -> StorageGCTaskModel | None:
        now = datetime.utcnow()
        stmt = (
            select(StorageGCTaskModel)
            .where(
                StorageGCTaskModel.action == "delete",
                StorageGCTaskModel.status == "pending",
                or_(
                    StorageGCTaskModel.next_retry_at.is_(None),
                    StorageGCTaskModel.next_retry_at <= now,
                ),
                or_(
                    StorageGCTaskModel.lease_expires_at.is_(None),
                    StorageGCTaskModel.lease_expires_at <= now,
                ),
            )
            .order_by(StorageGCTaskModel.id.asc())
            .with_for_update(skip_locked=True)
        )
        task = self.session.scalar(stmt)
        if task is None:
            return None
        task.status = "running"
        task.lease_token = lease_token
        task.lease_expires_at = now + timedelta(seconds=lease_seconds)
        self.session.add(task)
        self.session.flush()
        self.session.refresh(task)
        return task

    def get_for_execution(self, *, task_id: int, lease_token: str) -> StorageGCTaskModel | None:
        stmt = select(StorageGCTaskModel).where(
            StorageGCTaskModel.id == task_id,
            StorageGCTaskModel.lease_token == lease_token,
        )
        return self.session.scalar(stmt)

    def mark_success(self, task: StorageGCTaskModel) -> StorageGCTaskModel:
        task.status = "success"
        task.lease_token = None
        task.lease_expires_at = None
        task.next_retry_at = None
        task.last_error = None
        self.session.add(task)
        self.session.flush()
        self.session.refresh(task)
        return task

    def mark_failed(
        self,
        task: StorageGCTaskModel,
        *,
        error_message: str,
        retry_delay_seconds: int,
    ) -> StorageGCTaskModel:
        task.retry_count += 1
        task.lease_token = None
        task.lease_expires_at = None
        task.last_error = error_message
        if task.retry_count >= task.max_retry_count:
            task.status = "failed"
            task.next_retry_at = None
        else:
            task.status = "pending"
            task.next_retry_at = datetime.utcnow() + timedelta(seconds=retry_delay_seconds)
        self.session.add(task)
        self.session.flush()
        self.session.refresh(task)
        return task
