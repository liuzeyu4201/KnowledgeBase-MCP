from __future__ import annotations

import logging
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from knowledgebase.app.config import EmbeddingSettings, get_settings
from knowledgebase.db.session import session_scope
from knowledgebase.domain.exceptions import AppError
from knowledgebase.integrations.embedding.embedder import BaseEmbedder, build_embedder
from knowledgebase.integrations.milvus.collection_manager import MilvusCollectionManager
from knowledgebase.models.chunk import ChunkModel

logger = logging.getLogger("knowledgebase.embedding")

_SUPPORTED_PROVIDERS = {"aliyun", "ollama"}
_PROVIDERS_REQUIRE_API_KEY = {"aliyun"}
_STARTUP_PROBE_TEXT = "knowledgebase embedding startup probe"


class EmbeddingStartupValidator:
    """Embedding 启动校验器。"""

    def __init__(
        self,
        settings: EmbeddingSettings,
        *,
        embedder_factory: Callable[[], BaseEmbedder] | None = None,
        existing_model_loader: Callable[[], list[str]] | None = None,
        milvus_dimension_loader: Callable[[], int | None] | None = None,
    ) -> None:
        self.settings = settings
        self._embedder_factory = embedder_factory or build_embedder
        self._existing_model_loader = existing_model_loader or self._load_existing_models
        self._milvus_dimension_loader = (
            milvus_dimension_loader or self._load_existing_milvus_dimension
        )

    def validate_or_raise(self) -> None:
        """执行 Embedding 启动校验并输出结构化日志。"""

        logger.info(
            "embedding config loaded provider=%s model=%s dimension=%s base_url=%s timeout_seconds=%s max_batch_size=%s api_key_configured=%s asset_id=%s",
            self.settings.provider or "<empty>",
            self.settings.model or "<empty>",
            self.settings.dimension,
            self.settings.base_url or "<empty>",
            self.settings.timeout_seconds,
            self.settings.max_batch_size,
            bool(self.settings.api_key),
            self.settings.asset_id,
        )

        try:
            self._validate_config()
            self._validate_existing_assets()
            self._validate_milvus_dimension()
            self._validate_remote_probe()
        except AppError as exc:
            logger.error(
                "embedding startup validation failed code=%s message=%s details=%s asset_id=%s",
                exc.code,
                exc.message,
                exc.details,
                self.settings.asset_id,
            )
            raise

        logger.info(
            "embedding startup validation passed provider=%s model=%s dimension=%s asset_id=%s",
            self.settings.provider,
            self.settings.model,
            self.settings.dimension,
            self.settings.asset_id,
        )

    def _validate_config(self) -> None:
        if not self.settings.provider:
            raise AppError(
                code="EMBEDDING_CONFIG_INVALID",
                message="embedding provider is required",
                error_type="system_error",
            )
        if self.settings.provider == "mock":
            raise AppError(
                code="EMBEDDING_CONFIG_INVALID",
                message="mock embedding provider is not allowed in current stage",
                error_type="system_error",
                details={"provider": self.settings.provider},
            )
        if self.settings.provider not in _SUPPORTED_PROVIDERS:
            raise AppError(
                code="EMBEDDING_CONFIG_INVALID",
                message="unsupported embedding provider",
                error_type="system_error",
                details={
                    "provider": self.settings.provider,
                    "supported_providers": sorted(_SUPPORTED_PROVIDERS),
                },
            )
        if not self.settings.base_url:
            raise AppError(
                code="EMBEDDING_CONFIG_INVALID",
                message="embedding base url is required",
                error_type="system_error",
            )
        if not self.settings.model:
            raise AppError(
                code="EMBEDDING_CONFIG_INVALID",
                message="embedding model is required",
                error_type="system_error",
            )
        if self.settings.provider in _PROVIDERS_REQUIRE_API_KEY and not self.settings.api_key:
            raise AppError(
                code="EMBEDDING_CONFIG_INVALID",
                message="embedding api key is required",
                error_type="system_error",
                details={"provider": self.settings.provider},
            )
        if self.settings.dimension <= 0:
            raise AppError(
                code="EMBEDDING_CONFIG_INVALID",
                message="embedding dimension must be a positive integer",
                error_type="system_error",
                details={"dimension": self.settings.dimension},
            )
        if self.settings.timeout_seconds <= 0:
            raise AppError(
                code="EMBEDDING_CONFIG_INVALID",
                message="embedding timeout_seconds must be positive",
                error_type="system_error",
                details={"timeout_seconds": self.settings.timeout_seconds},
            )
        if self.settings.max_batch_size <= 0:
            raise AppError(
                code="EMBEDDING_CONFIG_INVALID",
                message="embedding max_batch_size must be positive",
                error_type="system_error",
                details={"max_batch_size": self.settings.max_batch_size},
            )

    def _validate_existing_assets(self) -> None:
        existing_models = self._existing_model_loader()
        if not existing_models:
            logger.info("embedding asset validation skipped because no persisted chunk vectors exist")
            return
        if existing_models != [self.settings.asset_id]:
            raise AppError(
                code="EMBEDDING_ASSET_MISMATCH",
                message="persisted embedding asset does not match current configuration",
                error_type="system_error",
                details={
                    "configured_asset_id": self.settings.asset_id,
                    "persisted_asset_ids": existing_models,
                },
            )

    def _validate_milvus_dimension(self) -> None:
        existing_dimension = self._milvus_dimension_loader()
        if existing_dimension is None:
            logger.info("embedding milvus validation skipped because collection is not initialized yet")
            return
        if existing_dimension != self.settings.dimension:
            raise AppError(
                code="EMBEDDING_DIMENSION_MISMATCH",
                message="milvus dense vector dimension does not match embedding configuration",
                error_type="system_error",
                details={
                    "configured_dimension": self.settings.dimension,
                    "milvus_dimension": existing_dimension,
                },
            )

    def _validate_remote_probe(self) -> None:
        vector = self._embedder_factory().embed_texts([_STARTUP_PROBE_TEXT])[0]
        if len(vector) != self.settings.dimension:
            raise AppError(
                code="EMBEDDING_PROBE_INVALID",
                message="embedding startup probe dimension mismatch",
                error_type="system_error",
                details={
                    "configured_dimension": self.settings.dimension,
                    "probe_dimension": len(vector),
                },
            )

    def _load_existing_models(self) -> list[str]:
        try:
            with session_scope() as session:
                result = session.execute(
                    select(ChunkModel.embedding_model)
                    .where(ChunkModel.deleted_at.is_(None))
                    .distinct()
                    .order_by(ChunkModel.embedding_model)
                )
                return [str(item) for item in result.scalars().all() if item]
        except SQLAlchemyError as exc:
            raise AppError(
                code="EMBEDDING_ASSET_VALIDATION_FAILED",
                message="failed to inspect persisted embedding assets",
                error_type="system_error",
                details={"reason": str(exc)},
            ) from exc

    def _load_existing_milvus_dimension(self) -> int | None:
        try:
            return MilvusCollectionManager().get_existing_dense_vector_dimension()
        except Exception as exc:  # noqa: BLE001
            raise AppError(
                code="EMBEDDING_ASSET_VALIDATION_FAILED",
                message="failed to inspect milvus collection dimension",
                error_type="system_error",
                details={"reason": str(exc)},
            ) from exc


def validate_embedding_startup() -> None:
    """执行默认 Embedding 启动校验。"""

    EmbeddingStartupValidator(get_settings().embedding).validate_or_raise()
