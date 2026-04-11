from __future__ import annotations

from knowledgebase.app.config import get_settings
from knowledgebase.integrations.storage.file_storage import FileStorage
from knowledgebase.repositories.storage_gc_task_repository import StorageGCTaskRepository


class StorageCleanupService:
    """对象存储删除与补偿清理服务。"""

    def __init__(self, repository: StorageGCTaskRepository) -> None:
        self.repository = repository
        self.storage = FileStorage()
        self.settings = get_settings()

    def delete_now_or_enqueue(
        self,
        *,
        resource_type: str,
        resource_id: int | None,
        storage_uri: str | None,
        storage_backend: str | None = None,
    ) -> None:
        if not storage_uri:
            return
        backend = storage_backend or self.storage.resolve_storage_backend(storage_uri)
        try:
            self.storage.delete_file(storage_uri)
        except Exception:  # noqa: BLE001
            self.enqueue_delete(
                resource_type=resource_type,
                resource_id=resource_id,
                storage_uri=storage_uri,
                storage_backend=backend,
            )

    def enqueue_delete(
        self,
        *,
        resource_type: str,
        resource_id: int | None,
        storage_uri: str,
        storage_backend: str,
    ) -> None:
        self.repository.create_delete_task(
            resource_type=resource_type,
            resource_id=resource_id,
            storage_backend=storage_backend,
            storage_uri=storage_uri,
            max_retry_count=self.settings.storage_gc_max_retry_count,
        )
