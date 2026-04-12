from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class EmbeddingSettings:
    """Embedding 服务配置。"""

    provider: str
    api_key: str | None
    base_url: str
    model: str
    dimension: int
    timeout_seconds: float
    max_batch_size: int

    @property
    def asset_id(self) -> str:
        """返回用于标识持久化向量资产的稳定签名。"""

        return f"{self.provider}:{self.model}:{self.dimension}"


@dataclass(frozen=True)
class Settings:
    """应用配置。"""

    app_name: str
    database_url: str
    auto_init_schema: bool
    mcp_transport: str
    mcp_host: str
    mcp_port: int
    mcp_path: str
    milvus_host: str
    milvus_port: int
    milvus_collection_name: str
    milvus_dense_index_type: str
    milvus_dense_metric_type: str
    milvus_sparse_index_type: str
    milvus_analyzer: str
    milvus_recreate_collection: bool
    storage_root: str
    embedding: EmbeddingSettings
    chunk_size: int
    chunk_overlap: int
    task_worker_poll_interval_seconds: float
    task_worker_lease_seconds: int
    task_worker_heartbeat_interval_seconds: float
    task_worker_batch_size: int
    staged_file_ttl_seconds: int
    upload_chunk_size_bytes: int
    object_storage_provider: str
    minio_endpoint: str
    minio_access_key: str | None
    minio_secret_key: str | None
    minio_secure: bool
    minio_region: str | None
    minio_staged_bucket: str
    minio_document_bucket: str
    storage_gc_batch_size: int
    storage_gc_max_retry_count: int


def _read_text_env(name: str, default: str = "") -> str:
    """读取字符串环境变量并去除首尾空白。"""

    return os.getenv(name, default).strip()


def _read_optional_text_env(name: str) -> str | None:
    """读取可选字符串环境变量，空值统一视为未配置。"""

    value = _read_text_env(name)
    return value or None


def _read_int_env(name: str, default: int) -> int:
    """读取整型环境变量，非法值回落为约定默认值，由启动校验统一拦截。"""

    raw_value = _read_text_env(name)
    if not raw_value:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return -1


def _read_float_env(name: str, default: float) -> float:
    """读取浮点环境变量，非法值回落为约定默认值，由启动校验统一拦截。"""

    raw_value = _read_text_env(name)
    if not raw_value:
        return default
    try:
        return float(raw_value)
    except ValueError:
        return -1.0


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """读取运行配置，统一通过环境变量覆盖默认值。"""

    raw_transport = os.getenv("KNOWLEDGEBASE_MCP_TRANSPORT", "stdio")
    transport = "streamable-http" if raw_transport == "http" else raw_transport

    return Settings(
        app_name=os.getenv("KNOWLEDGEBASE_APP_NAME", "KnowledgeBase MCP Server"),
        database_url=os.getenv(
            "KNOWLEDGEBASE_DATABASE_URL",
            "postgresql+psycopg://knowledgebase:knowledgebase@localhost:5432/knowledgebase",
        ),
        auto_init_schema=os.getenv("KNOWLEDGEBASE_AUTO_INIT_SCHEMA", "true").lower()
        in {"1", "true", "yes", "on"},
        mcp_transport=transport,
        mcp_host=os.getenv("KNOWLEDGEBASE_MCP_HOST", "0.0.0.0"),
        mcp_port=int(os.getenv("KNOWLEDGEBASE_MCP_PORT", "8000")),
        mcp_path=os.getenv("KNOWLEDGEBASE_MCP_PATH", "/mcp"),
        milvus_host=os.getenv("KNOWLEDGEBASE_MILVUS_HOST", "localhost"),
        milvus_port=int(os.getenv("KNOWLEDGEBASE_MILVUS_PORT", "19530")),
        milvus_collection_name=os.getenv(
            "KNOWLEDGEBASE_MILVUS_COLLECTION_NAME",
            "kb_chunk_vector_v1",
        ),
        milvus_dense_index_type=os.getenv(
            "KNOWLEDGEBASE_MILVUS_DENSE_INDEX_TYPE",
            "AUTOINDEX",
        ),
        milvus_dense_metric_type=os.getenv(
            "KNOWLEDGEBASE_MILVUS_DENSE_METRIC_TYPE",
            "COSINE",
        ),
        milvus_sparse_index_type=os.getenv(
            "KNOWLEDGEBASE_MILVUS_SPARSE_INDEX_TYPE",
            "SPARSE_INVERTED_INDEX",
        ),
        milvus_analyzer=os.getenv("KNOWLEDGEBASE_MILVUS_ANALYZER", "language_identifier"),
        milvus_recreate_collection=os.getenv(
            "KNOWLEDGEBASE_MILVUS_RECREATE_COLLECTION",
            "false",
        ).lower()
        in {"1", "true", "yes", "on"},
        storage_root=os.getenv("KNOWLEDGEBASE_STORAGE_ROOT", "./data/storage"),
        embedding=EmbeddingSettings(
            provider=_read_text_env("KNOWLEDGEBASE_EMBEDDING_PROVIDER").lower(),
            api_key=_read_optional_text_env("KNOWLEDGEBASE_EMBEDDING_API_KEY"),
            base_url=_read_text_env("KNOWLEDGEBASE_EMBEDDING_BASE_URL"),
            model=_read_text_env("KNOWLEDGEBASE_EMBEDDING_MODEL"),
            dimension=_read_int_env("KNOWLEDGEBASE_EMBEDDING_DIMENSION", 0),
            timeout_seconds=_read_float_env("KNOWLEDGEBASE_EMBEDDING_TIMEOUT_SECONDS", 60.0),
            max_batch_size=_read_int_env("KNOWLEDGEBASE_EMBEDDING_MAX_BATCH_SIZE", 32),
        ),
        chunk_size=int(os.getenv("KNOWLEDGEBASE_CHUNK_SIZE", "800")),
        chunk_overlap=int(os.getenv("KNOWLEDGEBASE_CHUNK_OVERLAP", "100")),
        task_worker_poll_interval_seconds=float(
            os.getenv("KNOWLEDGEBASE_TASK_WORKER_POLL_INTERVAL_SECONDS", "1.0")
        ),
        task_worker_lease_seconds=int(
            os.getenv("KNOWLEDGEBASE_TASK_WORKER_LEASE_SECONDS", "60")
        ),
        task_worker_heartbeat_interval_seconds=float(
            os.getenv("KNOWLEDGEBASE_TASK_WORKER_HEARTBEAT_INTERVAL_SECONDS", "10.0")
        ),
        task_worker_batch_size=int(
            os.getenv("KNOWLEDGEBASE_TASK_WORKER_BATCH_SIZE", "1")
        ),
        staged_file_ttl_seconds=int(
            os.getenv("KNOWLEDGEBASE_STAGED_FILE_TTL_SECONDS", "300")
        ),
        upload_chunk_size_bytes=int(
            os.getenv("KNOWLEDGEBASE_UPLOAD_CHUNK_SIZE_BYTES", "1048576")
        ),
        object_storage_provider=os.getenv("KNOWLEDGEBASE_OBJECT_STORAGE_PROVIDER", "local"),
        minio_endpoint=os.getenv("KNOWLEDGEBASE_MINIO_ENDPOINT", "localhost:9000"),
        minio_access_key=os.getenv("KNOWLEDGEBASE_MINIO_ACCESS_KEY"),
        minio_secret_key=os.getenv("KNOWLEDGEBASE_MINIO_SECRET_KEY"),
        minio_secure=os.getenv("KNOWLEDGEBASE_MINIO_SECURE", "false").lower()
        in {"1", "true", "yes", "on"},
        minio_region=os.getenv("KNOWLEDGEBASE_MINIO_REGION"),
        minio_staged_bucket=os.getenv(
            "KNOWLEDGEBASE_MINIO_STAGED_BUCKET",
            "kb-staged-files",
        ),
        minio_document_bucket=os.getenv(
            "KNOWLEDGEBASE_MINIO_DOCUMENT_BUCKET",
            "kb-documents",
        ),
        storage_gc_batch_size=int(
            os.getenv("KNOWLEDGEBASE_STORAGE_GC_BATCH_SIZE", "10")
        ),
        storage_gc_max_retry_count=int(
            os.getenv("KNOWLEDGEBASE_STORAGE_GC_MAX_RETRY_COUNT", "20")
        ),
    )
