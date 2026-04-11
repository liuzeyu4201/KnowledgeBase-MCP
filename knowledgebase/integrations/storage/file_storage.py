from __future__ import annotations

from base64 import b64decode
from dataclasses import dataclass
from datetime import datetime
from io import BufferedReader, BytesIO
import hashlib
from pathlib import Path
from typing import BinaryIO
from urllib.parse import urlparse
from uuid import uuid4

from minio import Minio
from minio.error import S3Error

from knowledgebase.app.config import get_settings
from knowledgebase.domain.exceptions import AppError


@dataclass(frozen=True)
class StoredObject:
    """统一描述一次对象写入结果。"""

    storage_backend: str
    storage_uri: str
    file_size: int
    file_sha256: str


class _TrackingReader:
    """包装输入流，在上传时同步统计大小并计算摘要。"""

    def __init__(self, file_stream: BinaryIO) -> None:
        self._reader = BufferedReader(file_stream) if not isinstance(file_stream, BufferedReader) else file_stream
        self._sha256 = hashlib.sha256()
        self.total_size = 0

    def read(self, size: int = -1) -> bytes:
        chunk = self._reader.read(size)
        if chunk:
            self._sha256.update(chunk)
            self.total_size += len(chunk)
        return chunk

    @property
    def file_sha256(self) -> str:
        return self._sha256.hexdigest()


class _LocalFileStorage:
    """本地文件存储实现，保留作为兼容后端。"""

    def __init__(self, root: Path, upload_chunk_size_bytes: int) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.task_root = (self.root / "_tasks").resolve()
        self.task_root.mkdir(parents=True, exist_ok=True)
        self.staged_root = (self.root / "_staged").resolve()
        self.staged_root.mkdir(parents=True, exist_ok=True)
        self.upload_chunk_size_bytes = upload_chunk_size_bytes

    def save_document_bytes(self, *, file_name: str, file_bytes: bytes) -> StoredObject:
        safe_name = self._build_internal_file_name(prefix=uuid4().hex, original_name=file_name)
        target = self.root / safe_name
        target.write_bytes(file_bytes)
        return StoredObject(
            storage_backend="local",
            storage_uri=str(target),
            file_size=len(file_bytes),
            file_sha256=hashlib.sha256(file_bytes).hexdigest(),
        )

    def save_staged_file_bytes(self, *, file_name: str, file_bytes: bytes) -> StoredObject:
        safe_name = self._build_internal_file_name(prefix=uuid4().hex, original_name=file_name)
        target = self.staged_root / safe_name
        target.write_bytes(file_bytes)
        return StoredObject(
            storage_backend="local",
            storage_uri=str(target),
            file_size=len(file_bytes),
            file_sha256=hashlib.sha256(file_bytes).hexdigest(),
        )

    def save_staged_file_stream(
        self,
        *,
        file_name: str,
        file_stream: BinaryIO,
    ) -> StoredObject:
        safe_name = self._build_internal_file_name(prefix=uuid4().hex, original_name=file_name)
        target = self.staged_root / safe_name
        sha256 = hashlib.sha256()
        total_size = 0

        with target.open("wb") as output:
            reader = BufferedReader(file_stream) if not isinstance(file_stream, BufferedReader) else file_stream
            while True:
                chunk = reader.read(self.upload_chunk_size_bytes)
                if not chunk:
                    break
                output.write(chunk)
                sha256.update(chunk)
                total_size += len(chunk)

        return StoredObject(
            storage_backend="local",
            storage_uri=str(target),
            file_size=total_size,
            file_sha256=sha256.hexdigest(),
        )

    def stage_task_file(
        self,
        *,
        task_uid: str,
        item_no: int,
        file_name: str,
        file_content_base64: str,
    ) -> tuple[str, str]:
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

    def read_file_bytes(self, storage_uri: str) -> bytes:
        target = self._ensure_within_storage_root(storage_uri)
        return target.read_bytes()

    def delete_file(self, storage_uri: str | None) -> None:
        if not storage_uri:
            return
        target = self._ensure_within_storage_root(storage_uri)
        if target.exists():
            target.unlink()

    def stage_delete_file(self, storage_uri: str | None) -> tuple[str | None, str | None]:
        if not storage_uri:
            return None, None
        target = self._ensure_within_storage_root(storage_uri, error_code="DELETE_FILE_STAGE_FAILED")
        if not target.exists():
            return str(target), None
        staged_target = target.with_name(f".delete_{uuid4().hex}_{target.name}")
        target.rename(staged_target)
        return str(target), str(staged_target)

    def restore_staged_file(self, *, original_path: str | None, staged_path: str | None) -> None:
        if not original_path or not staged_path:
            return
        original = Path(original_path).resolve()
        staged = Path(staged_path).resolve()
        if staged.exists():
            staged.rename(original)

    def finalize_staged_file_delete(self, staged_path: str | None) -> None:
        if not staged_path:
            return
        staged = Path(staged_path).resolve()
        if staged.exists():
            staged.unlink()

    def decode_base64_file(self, file_content_base64: str) -> bytes:
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

    def _ensure_within_storage_root(
        self,
        file_path: str,
        *,
        error_code: str = "CONSISTENCY_ROLLBACK_FAILED",
    ) -> Path:
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
        original_path = Path(original_name)
        extension = original_path.suffix or ".pdf"
        extension = extension[:16]
        max_component_length = 240
        reserved_length = len(prefix) + len(extension) + 2
        available_stem_length = max(8, max_component_length - reserved_length)
        normalized_stem = original_path.stem[:available_stem_length] or "document"
        return f"{prefix}_{normalized_stem}{extension}"


class _MinioFileStorage:
    """MinIO 对象存储实现。"""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.minio_access_key or not settings.minio_secret_key:
            raise AppError(
                code="OBJECT_STORAGE_CONFIG_INVALID",
                message="minio credentials are required",
                error_type="system_error",
            )
        self.settings = settings
        self.client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
            region=settings.minio_region,
        )
        self.part_size = max(settings.upload_chunk_size_bytes, 5 * 1024 * 1024)
        self._ensure_bucket(settings.minio_staged_bucket)
        self._ensure_bucket(settings.minio_document_bucket)

    def save_document_bytes(self, *, file_name: str, file_bytes: bytes) -> StoredObject:
        object_key = self._build_object_key(prefix="documents/global", file_name=file_name)
        self.client.put_object(
            self.settings.minio_document_bucket,
            object_key,
            BytesIO(file_bytes),
            length=len(file_bytes),
        )
        return StoredObject(
            storage_backend="minio",
            storage_uri=self._build_storage_uri(self.settings.minio_document_bucket, object_key),
            file_size=len(file_bytes),
            file_sha256=hashlib.sha256(file_bytes).hexdigest(),
        )

    def save_staged_file_bytes(self, *, file_name: str, file_bytes: bytes) -> StoredObject:
        object_key = self._build_object_key(prefix="staged/global", file_name=file_name)
        self.client.put_object(
            self.settings.minio_staged_bucket,
            object_key,
            BytesIO(file_bytes),
            length=len(file_bytes),
        )
        return StoredObject(
            storage_backend="minio",
            storage_uri=self._build_storage_uri(self.settings.minio_staged_bucket, object_key),
            file_size=len(file_bytes),
            file_sha256=hashlib.sha256(file_bytes).hexdigest(),
        )

    def save_staged_file_stream(
        self,
        *,
        file_name: str,
        file_stream: BinaryIO,
    ) -> StoredObject:
        object_key = self._build_object_key(prefix="staged/global", file_name=file_name)
        reader = _TrackingReader(file_stream)
        self.client.put_object(
            self.settings.minio_staged_bucket,
            object_key,
            reader,
            length=-1,
            part_size=self.part_size,
        )
        return StoredObject(
            storage_backend="minio",
            storage_uri=self._build_storage_uri(self.settings.minio_staged_bucket, object_key),
            file_size=reader.total_size,
            file_sha256=reader.file_sha256,
        )

    def read_file_bytes(self, storage_uri: str) -> bytes:
        bucket, object_key = self.parse_storage_uri(storage_uri)
        response = self.client.get_object(bucket, object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete_file(self, storage_uri: str | None) -> None:
        if not storage_uri:
            return
        bucket, object_key = self.parse_storage_uri(storage_uri)
        try:
            self.client.remove_object(bucket, object_key)
        except S3Error as exc:
            if exc.code in {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}:
                return
            raise

    def stage_delete_file(self, storage_uri: str | None) -> tuple[str | None, str | None]:
        return storage_uri, storage_uri

    def restore_staged_file(self, *, original_path: str | None, staged_path: str | None) -> None:
        return None

    def finalize_staged_file_delete(self, staged_path: str | None) -> None:
        self.delete_file(staged_path)

    def object_exists(self, storage_uri: str) -> bool:
        bucket, object_key = self.parse_storage_uri(storage_uri)
        try:
            self.client.stat_object(bucket, object_key)
            return True
        except S3Error as exc:
            if exc.code in {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}:
                return False
            raise

    def parse_storage_uri(self, storage_uri: str) -> tuple[str, str]:
        parsed = urlparse(storage_uri)
        if parsed.scheme != "s3" or not parsed.netloc or not parsed.path:
            raise AppError(
                code="OBJECT_STORAGE_URI_INVALID",
                message="storage_uri is not a valid s3 uri",
                error_type="system_error",
                details={"storage_uri": storage_uri},
            )
        return parsed.netloc, parsed.path.lstrip("/")

    def _build_object_key(self, *, prefix: str, file_name: str) -> str:
        safe_name = self._build_safe_file_name(file_name)
        now = datetime.utcnow()
        return (
            f"{prefix}/"
            f"{now.year:04d}/{now.month:02d}/{now.day:02d}/"
            f"{uuid4().hex}/{safe_name}"
        )

    def _build_safe_file_name(self, file_name: str) -> str:
        original_path = Path(file_name)
        extension = original_path.suffix or ".pdf"
        extension = extension[:16]
        normalized_stem = (original_path.stem[:128] or "document").replace("/", "_")
        return f"{normalized_stem}{extension}"

    def _build_storage_uri(self, bucket: str, object_key: str) -> str:
        return f"s3://{bucket}/{object_key}"

    def _ensure_bucket(self, bucket_name: str) -> None:
        if self.client.bucket_exists(bucket_name):
            return
        self.client.make_bucket(bucket_name)


class FileStorage:
    """统一文件存储门面，默认写入当前配置后端，同时兼容读取历史本地路径。"""

    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.local = _LocalFileStorage(
            root=Path(settings.storage_root),
            upload_chunk_size_bytes=settings.upload_chunk_size_bytes,
        )
        self.minio = _MinioFileStorage() if settings.object_storage_provider == "minio" else None

    def save_file(self, *, file_name: str, file_content_base64: str) -> tuple[str, bytes]:
        content = self.decode_base64_file(file_content_base64)
        return self.save_file_bytes(file_name=file_name, file_bytes=content)

    def decode_base64_file(self, file_content_base64: str) -> bytes:
        return self.local.decode_base64_file(file_content_base64)

    def save_file_bytes(self, *, file_name: str, file_bytes: bytes) -> tuple[str, bytes]:
        stored = self._writer().save_document_bytes(file_name=file_name, file_bytes=file_bytes)
        return stored.storage_uri, file_bytes

    def save_staged_file_bytes(self, *, file_name: str, file_bytes: bytes) -> tuple[str, int, str]:
        stored = self._writer().save_staged_file_bytes(file_name=file_name, file_bytes=file_bytes)
        return stored.storage_uri, stored.file_size, stored.file_sha256

    def save_staged_file_stream(
        self,
        *,
        file_name: str,
        file_stream: BinaryIO,
    ) -> tuple[str, int, str]:
        stored = self._writer().save_staged_file_stream(file_name=file_name, file_stream=file_stream)
        return stored.storage_uri, stored.file_size, stored.file_sha256

    def stage_task_file(
        self,
        *,
        task_uid: str,
        item_no: int,
        file_name: str,
        file_content_base64: str,
    ) -> tuple[str, str]:
        return self.local.stage_task_file(
            task_uid=task_uid,
            item_no=item_no,
            file_name=file_name,
            file_content_base64=file_content_base64,
        )

    def save_pdf(self, *, file_name: str, file_content_base64: str) -> tuple[str, bytes]:
        return self.save_file(file_name=file_name, file_content_base64=file_content_base64)

    def decode_base64_pdf(self, file_content_base64: str) -> bytes:
        return self.decode_base64_file(file_content_base64)

    def save_pdf_bytes(self, *, file_name: str, file_bytes: bytes) -> tuple[str, bytes]:
        return self.save_file_bytes(file_name=file_name, file_bytes=file_bytes)

    def stage_task_pdf(
        self,
        *,
        task_uid: str,
        item_no: int,
        file_name: str,
        file_content_base64: str,
    ) -> tuple[str, str]:
        return self.stage_task_file(
            task_uid=task_uid,
            item_no=item_no,
            file_name=file_name,
            file_content_base64=file_content_base64,
        )

    def read_file_bytes(self, file_path: str) -> bytes:
        return self._backend_for_uri(file_path).read_file_bytes(file_path)

    def delete_file(self, file_path: str | None) -> None:
        if not file_path:
            return
        self._backend_for_uri(file_path).delete_file(file_path)

    def stage_delete_file(self, file_path: str | None) -> tuple[str | None, str | None]:
        if not file_path:
            return None, None
        return self._backend_for_uri(file_path).stage_delete_file(file_path)

    def restore_staged_file(
        self,
        *,
        original_path: str | None,
        staged_path: str | None,
    ) -> None:
        target_path = staged_path or original_path
        if not target_path:
            return
        self._backend_for_uri(target_path).restore_staged_file(
            original_path=original_path,
            staged_path=staged_path,
        )

    def finalize_staged_file_delete(self, staged_path: str | None) -> None:
        if not staged_path:
            return
        self._backend_for_uri(staged_path).finalize_staged_file_delete(staged_path)

    def object_exists(self, storage_uri: str) -> bool:
        if self._is_s3_uri(storage_uri):
            if self.minio is None:
                raise AppError(
                    code="OBJECT_STORAGE_CONFIG_INVALID",
                    message="minio backend is not enabled",
                    error_type="system_error",
                )
            return self.minio.object_exists(storage_uri)
        return Path(storage_uri).exists()

    def resolve_storage_backend(self, storage_uri: str) -> str:
        return "minio" if self._is_s3_uri(storage_uri) else "local"

    def _writer(self):
        if self.settings.object_storage_provider == "minio":
            if self.minio is None:
                raise AppError(
                    code="OBJECT_STORAGE_CONFIG_INVALID",
                    message="minio backend is not initialized",
                    error_type="system_error",
                )
            return self.minio
        return self.local

    def _backend_for_uri(self, storage_uri: str):
        if self._is_s3_uri(storage_uri):
            if self.minio is None:
                raise AppError(
                    code="OBJECT_STORAGE_CONFIG_INVALID",
                    message="minio backend is not enabled",
                    error_type="system_error",
                )
            return self.minio
        return self.local

    def _is_s3_uri(self, storage_uri: str) -> bool:
        return storage_uri.startswith("s3://")
