from __future__ import annotations

from base64 import b64decode
from pathlib import Path
from uuid import uuid4

from knowledgebase.app.config import get_settings
from knowledgebase.domain.exceptions import AppError


class FileStorage:
    """本地文件存储实现。"""

    def __init__(self) -> None:
        settings = get_settings()
        self.root = Path(settings.storage_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save_pdf(self, *, file_name: str, file_content_base64: str) -> tuple[str, bytes]:
        """保存 PDF 原文件并返回文件路径与原始字节内容。"""

        try:
            content = b64decode(file_content_base64, validate=True)
        except Exception as exc:  # noqa: BLE001
            raise AppError(
                code="INVALID_ARGUMENT",
                message="file_content_base64 is invalid",
                error_type="validation_error",
            ) from exc

        if not content:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="file content is empty",
                error_type="validation_error",
            )

        safe_name = f"{uuid4().hex}_{Path(file_name).name}"
        target = self.root / safe_name
        target.write_bytes(content)
        return str(target), content

    def delete_file(self, file_path: str | None) -> None:
        """删除本地存储文件，作为导入失败时的补偿动作。"""

        if not file_path:
            return

        target = Path(file_path).resolve()
        try:
            target.relative_to(self.root)
        except ValueError as exc:
            raise AppError(
                code="CONSISTENCY_ROLLBACK_FAILED",
                message="storage rollback path is out of root",
                error_type="system_error",
                details={"file_path": file_path},
            ) from exc

        if target.exists():
            target.unlink()

    def stage_delete_file(self, file_path: str | None) -> tuple[str | None, str | None]:
        """把原始文件移动到暂存路径，等待数据库提交成功后再最终删除。"""

        if not file_path:
            return None, None

        target = Path(file_path).resolve()
        try:
            target.relative_to(self.root)
        except ValueError as exc:
            raise AppError(
                code="DELETE_FILE_STAGE_FAILED",
                message="storage delete path is out of root",
                error_type="system_error",
                details={"file_path": file_path},
            ) from exc

        if not target.exists():
            return str(target), None

        staged_target = target.with_name(f".delete_{uuid4().hex}_{target.name}")
        target.rename(staged_target)
        return str(target), str(staged_target)

    def restore_staged_file(
        self,
        *,
        original_path: str | None,
        staged_path: str | None,
    ) -> None:
        """删除回滚时把暂存文件恢复到原始路径。"""

        if not original_path or not staged_path:
            return

        original = Path(original_path).resolve()
        staged = Path(staged_path).resolve()
        if staged.exists():
            staged.rename(original)

    def finalize_staged_file_delete(self, staged_path: str | None) -> None:
        """数据库提交成功后最终删除暂存文件。"""

        if not staged_path:
            return

        staged = Path(staged_path).resolve()
        if staged.exists():
            staged.unlink()
