from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from knowledgebase.models.staged_file import StagedFileModel


class StagedFileRepository:
    """暂存文件数据访问层。"""

    DELETABLE_STATUSES = {"uploaded", "failed", "expired"}
    EXPIRABLE_STATUSES = {"uploaded", "failed", "expired"}

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        storage_backend: str,
        storage_uri: str,
        file_name: str,
        mime_type: str,
        source_type: str,
        file_size: int,
        file_sha256: str,
        expires_at: datetime | None,
    ) -> StagedFileModel:
        """创建暂存文件记录。"""

        now = datetime.utcnow()
        model = StagedFileModel(
            status="uploaded",
            storage_backend=storage_backend,
            storage_uri=storage_uri,
            file_name=file_name,
            mime_type=mime_type,
            source_type=source_type,
            file_size=file_size,
            file_sha256=file_sha256,
            upload_completed_at=now,
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
        )
        self.session.add(model)
        self.session.flush()
        self.session.refresh(model)
        return model

    def get_by_id(self, staged_file_id: int, *, include_deleted: bool = False) -> StagedFileModel | None:
        """按主键查询暂存文件。"""

        stmt = select(StagedFileModel).where(StagedFileModel.id == staged_file_id)
        if not include_deleted:
            stmt = stmt.where(StagedFileModel.deleted_at.is_(None))
        return self.session.scalar(stmt)

    def get_by_uid(self, staged_file_uid: str, *, include_deleted: bool = False) -> StagedFileModel | None:
        """按稳定标识查询暂存文件。"""

        stmt = select(StagedFileModel).where(StagedFileModel.staged_file_uid == staged_file_uid)
        if not include_deleted:
            stmt = stmt.where(StagedFileModel.deleted_at.is_(None))
        return self.session.scalar(stmt)

    def get_for_update(self, staged_file_id: int) -> StagedFileModel | None:
        """按主键加锁读取暂存文件。"""

        stmt = (
            select(StagedFileModel)
            .where(
                StagedFileModel.id == staged_file_id,
                StagedFileModel.deleted_at.is_(None),
            )
            .with_for_update()
        )
        return self.session.scalar(stmt)

    def list(
        self,
        *,
        status: str | None,
        mime_type: str | None,
        linked_document_id: int | None,
        page: int,
        page_size: int,
    ) -> tuple[list[StagedFileModel], int]:
        """按条件分页查询暂存文件。"""

        conditions = [StagedFileModel.deleted_at.is_(None)]
        if status:
            conditions.append(StagedFileModel.status == status)
        if mime_type:
            conditions.append(StagedFileModel.mime_type == mime_type)
        if linked_document_id is not None:
            conditions.append(StagedFileModel.linked_document_id == linked_document_id)

        data_stmt = (
            select(StagedFileModel)
            .where(*conditions)
            .order_by(StagedFileModel.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        count_stmt = select(func.count(StagedFileModel.id)).where(*conditions)

        items = list(self.session.scalars(data_stmt).all())
        total = self.session.scalar(count_stmt) or 0
        return items, total

    def mark_consuming(self, staged_file: StagedFileModel) -> StagedFileModel:
        """标记暂存文件进入消费中。"""

        staged_file.status = "consuming"
        staged_file.last_error = None
        self.session.add(staged_file)
        self.session.flush()
        self.session.refresh(staged_file)
        return staged_file

    def mark_consumed(
        self,
        staged_file: StagedFileModel,
        *,
        linked_document_id: int,
    ) -> StagedFileModel:
        """标记暂存文件已被消费。"""

        staged_file.status = "consumed"
        staged_file.consumed_at = datetime.utcnow()
        staged_file.linked_document_id = linked_document_id
        staged_file.last_error = None
        self.session.add(staged_file)
        self.session.flush()
        self.session.refresh(staged_file)
        return staged_file

    def link_task(self, staged_file: StagedFileModel, *, task_id: int) -> StagedFileModel:
        """关联暂存文件和批量任务。"""

        staged_file.linked_task_id = task_id
        self.session.add(staged_file)
        self.session.flush()
        self.session.refresh(staged_file)
        return staged_file

    def mark_deleted(self, staged_file: StagedFileModel) -> StagedFileModel:
        """软删除暂存文件记录。"""

        now = datetime.utcnow()
        staged_file.status = "deleted"
        staged_file.deleted_at = now
        self.session.add(staged_file)
        self.session.flush()
        self.session.refresh(staged_file)
        return staged_file

    def mark_expired(self, staged_file: StagedFileModel) -> StagedFileModel:
        """标记暂存文件已过期。"""

        staged_file.status = "expired"
        self.session.add(staged_file)
        self.session.flush()
        self.session.refresh(staged_file)
        return staged_file

    def claim_next_expired_for_cleanup(
        self,
        *,
        staged_file_id: int | None = None,
    ) -> StagedFileModel | None:
        """抢占下一条已过期暂存文件，并标记为 expired。"""

        now = datetime.utcnow()
        stmt = (
            select(StagedFileModel)
            .where(
                StagedFileModel.deleted_at.is_(None),
                StagedFileModel.expires_at.is_not(None),
                StagedFileModel.expires_at <= now,
                StagedFileModel.status.in_(self.EXPIRABLE_STATUSES),
            )
            .order_by(StagedFileModel.expires_at.asc(), StagedFileModel.id.asc())
            .with_for_update(skip_locked=True)
        )
        if staged_file_id is not None:
            stmt = stmt.where(StagedFileModel.id == staged_file_id)

        staged_file = self.session.scalar(stmt)
        if staged_file is None:
            return None
        if staged_file.status != "expired":
            staged_file.status = "expired"
            staged_file.last_error = None
            self.session.add(staged_file)
            self.session.flush()
            self.session.refresh(staged_file)
        return staged_file
