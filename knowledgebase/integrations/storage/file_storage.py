from __future__ import annotations

from base64 import b64decode
from io import BufferedReader
import hashlib
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from knowledgebase.app.config import get_settings
from knowledgebase.domain.exceptions import AppError


class FileStorage:
    """本地文件存储实现。"""

    def __init__(self) -> None:
        settings = get_settings()
        self.root = Path(settings.storage_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.task_root = (self.root / "_tasks").resolve()
        self.task_root.mkdir(parents=True, exist_ok=True)
        self.staged_root = (self.root / "_staged").resolve()
        self.staged_root.mkdir(parents=True, exist_ok=True)
        self.upload_chunk_size_bytes = settings.upload_chunk_size_bytes

    def save_file(self, *, file_name: str, file_content_base64: str) -> tuple[str, bytes]:
        """保存原始文件并返回文件路径与原始字节内容。"""

        content = self.decode_base64_file(file_content_base64)
        return self.save_file_bytes(file_name=file_name, file_bytes=content)

    def decode_base64_file(self, file_content_base64: str) -> bytes:
        """解码上传文件内容，并统一执行空内容校验。"""

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
        return content

    def save_file_bytes(self, *, file_name: str, file_bytes: bytes) -> tuple[str, bytes]:
        """保存已解码的文件字节内容，供同步导入和后台任务复用。"""

        safe_name = self._build_internal_file_name(
            prefix=uuid4().hex,
            original_name=file_name,
        )
        target = self.root / safe_name
        target.write_bytes(file_bytes)
        return str(target), file_bytes

    def save_staged_file_bytes(self, *, file_name: str, file_bytes: bytes) -> tuple[str, int, str]:
        """把文件字节写入暂存目录，返回路径、大小和摘要。"""

        safe_name = self._build_internal_file_name(
            prefix=uuid4().hex,
            original_name=file_name,
        )
        target = self.staged_root / safe_name
        target.write_bytes(file_bytes)
        return str(target), len(file_bytes), hashlib.sha256(file_bytes).hexdigest()

    def save_staged_file_stream(
        self,
        *,
        file_name: str,
        file_stream: BinaryIO,
    ) -> tuple[str, int, str]:
        """流式写入暂存文件，避免在服务端重复构造整块大字节数组。"""

        safe_name = self._build_internal_file_name(
            prefix=uuid4().hex,
            original_name=file_name,
        )
        target = self.staged_root / safe_name
        sha256 = hashlib.sha256()
        total_size = 0

        # 使用受控块大小写入，避免大文件请求在应用层继续膨胀。
        with target.open("wb") as output:
            reader = BufferedReader(file_stream) if not isinstance(file_stream, BufferedReader) else file_stream
            while True:
                chunk = reader.read(self.upload_chunk_size_bytes)
                if not chunk:
                    break
                output.write(chunk)
                sha256.update(chunk)
                total_size += len(chunk)

        return str(target), total_size, sha256.hexdigest()

    def stage_task_file(
        self,
        *,
        task_uid: str,
        item_no: int,
        file_name: str,
        file_content_base64: str,
    ) -> tuple[str, str]:
        """把批量导入文件先落到任务暂存目录，避免把大文件直接塞进数据库。"""

        file_bytes = self.decode_base64_file(file_content_base64)
        task_dir = (self.task_root / task_uid).resolve()
        task_dir.mkdir(parents=True, exist_ok=True)
        safe_name = self._build_internal_file_name(
            prefix=f"{item_no:06d}_{uuid4().hex}",
            original_name=file_name,
        )
        target = task_dir / safe_name
        target.write_bytes(file_bytes)
        return str(target), hashlib.sha256(file_bytes).hexdigest()

    def save_pdf(self, *, file_name: str, file_content_base64: str) -> tuple[str, bytes]:
        """兼容旧调用方，内部复用通用文件保存逻辑。"""

        return self.save_file(file_name=file_name, file_content_base64=file_content_base64)

    def decode_base64_pdf(self, file_content_base64: str) -> bytes:
        """兼容旧调用方，内部复用通用文件解码逻辑。"""

        return self.decode_base64_file(file_content_base64)

    def save_pdf_bytes(self, *, file_name: str, file_bytes: bytes) -> tuple[str, bytes]:
        """兼容旧调用方，内部复用通用文件保存逻辑。"""

        return self.save_file_bytes(file_name=file_name, file_bytes=file_bytes)

    def stage_task_pdf(
        self,
        *,
        task_uid: str,
        item_no: int,
        file_name: str,
        file_content_base64: str,
    ) -> tuple[str, str]:
        """兼容旧调用方，内部复用通用任务暂存逻辑。"""

        return self.stage_task_file(
            task_uid=task_uid,
            item_no=item_no,
            file_name=file_name,
            file_content_base64=file_content_base64,
        )

    def read_file_bytes(self, file_path: str) -> bytes:
        """读取任务暂存文件，用于后台 worker 真正执行导入。"""

        target = self._ensure_within_storage_root(file_path)
        return target.read_bytes()

    def delete_file(self, file_path: str | None) -> None:
        """删除本地存储文件，作为导入失败时的补偿动作。"""

        if not file_path:
            return

        target = self._ensure_within_storage_root(file_path)

        if target.exists():
            target.unlink()

    def stage_delete_file(self, file_path: str | None) -> tuple[str | None, str | None]:
        """把原始文件移动到暂存路径，等待数据库提交成功后再最终删除。"""

        if not file_path:
            return None, None

        target = self._ensure_within_storage_root(file_path, error_code="DELETE_FILE_STAGE_FAILED")

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

    def _ensure_within_storage_root(
        self,
        file_path: str,
        *,
        error_code: str = "CONSISTENCY_ROLLBACK_FAILED",
    ) -> Path:
        """校验目标文件必须位于受控存储根目录内，避免误删宿主机其他文件。"""

        target = Path(file_path).resolve()
        try:
            target.relative_to(self.root)
        except ValueError as exc:
            raise AppError(
                code=error_code,
                message="storage path is out of root",
                error_type="system_error",
                details={"file_path": file_path},
            ) from exc
        return target

    def _build_internal_file_name(self, *, prefix: str, original_name: str) -> str:
        """为内部存储生成受控文件名，避免宿主机文件名长度超限。"""

        original_path = Path(original_name)
        extension = original_path.suffix or ".pdf"
        extension = extension[:16]
        max_component_length = 240
        reserved_length = len(prefix) + len(extension) + 2
        available_stem_length = max(8, max_component_length - reserved_length)
        normalized_stem = original_path.stem[:available_stem_length] or "document"
        return f"{prefix}_{normalized_stem}{extension}"
