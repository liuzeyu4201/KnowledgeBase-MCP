from __future__ import annotations

import os
import unittest
from unittest import mock

from knowledgebase.app.config import EmbeddingSettings, get_settings
from knowledgebase.domain.exceptions import AppError
from knowledgebase.integrations.embedding.embedder import (
    AliyunEmbedder,
    BaseEmbedder,
    OllamaEmbedder,
    build_embedder,
)
from knowledgebase.integrations.embedding.validator import EmbeddingStartupValidator


class FakeEmbedder(BaseEmbedder):
    """测试用固定向量 Embedder。"""

    def __init__(self, *, provider: str = "aliyun", model: str = "text-embedding-v4", dimension: int = 1024):
        self.provider = provider
        self.model = model
        self.dimension = dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self.dimension for _ in texts]


class EmbeddingStartupValidationTestCase(unittest.TestCase):
    """验证 Embedding 配置与启动校验逻辑。"""

    def setUp(self) -> None:
        get_settings.cache_clear()

    def tearDown(self) -> None:
        get_settings.cache_clear()

    def test_build_embedder_uses_unified_embedding_env_vars(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "KNOWLEDGEBASE_EMBEDDING_PROVIDER": "aliyun",
                "KNOWLEDGEBASE_EMBEDDING_BASE_URL": "https://example.com/v1",
                "KNOWLEDGEBASE_EMBEDDING_MODEL": "kb-embedding",
                "KNOWLEDGEBASE_EMBEDDING_DIMENSION": "2048",
                "KNOWLEDGEBASE_EMBEDDING_API_KEY": "secret",
                "KNOWLEDGEBASE_EMBEDDING_TIMEOUT_SECONDS": "45",
                "KNOWLEDGEBASE_EMBEDDING_MAX_BATCH_SIZE": "8",
            },
            clear=False,
        ):
            embedder = build_embedder()

        self.assertIsInstance(embedder, AliyunEmbedder)
        self.assertEqual(embedder.provider, "aliyun")
        self.assertEqual(embedder.base_url, "https://example.com/v1")
        self.assertEqual(embedder.model, "kb-embedding")
        self.assertEqual(embedder.dimension, 2048)
        self.assertEqual(embedder.timeout_seconds, 45.0)
        self.assertEqual(embedder.max_batch_size, 8)
        self.assertEqual(embedder.asset_id, "aliyun:kb-embedding:2048")

    def test_validator_rejects_mock_provider(self) -> None:
        validator = EmbeddingStartupValidator(
            EmbeddingSettings(
                provider="mock",
                api_key="secret",
                base_url="https://example.com/v1",
                model="kb-embedding",
                dimension=1024,
                timeout_seconds=60.0,
                max_batch_size=32,
            ),
            existing_model_loader=lambda: [],
            milvus_dimension_loader=lambda: None,
            embedder_factory=lambda: FakeEmbedder(),
        )

        with self.assertRaises(AppError) as context:
            validator.validate_or_raise()

        self.assertEqual(context.exception.code, "EMBEDDING_CONFIG_INVALID")
        self.assertIn("mock", context.exception.message)

    def test_build_embedder_supports_ollama_without_api_key(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "KNOWLEDGEBASE_EMBEDDING_PROVIDER": "ollama",
                "KNOWLEDGEBASE_EMBEDDING_BASE_URL": "http://host.docker.internal:11434/v1",
                "KNOWLEDGEBASE_EMBEDDING_MODEL": "qwen3-embedding:0.6b",
                "KNOWLEDGEBASE_EMBEDDING_DIMENSION": "1024",
                "KNOWLEDGEBASE_EMBEDDING_API_KEY": "",
                "KNOWLEDGEBASE_EMBEDDING_TIMEOUT_SECONDS": "60",
                "KNOWLEDGEBASE_EMBEDDING_MAX_BATCH_SIZE": "16",
            },
            clear=False,
        ):
            embedder = build_embedder()

        self.assertIsInstance(embedder, OllamaEmbedder)
        self.assertEqual(embedder.provider, "ollama")
        self.assertEqual(embedder.base_url, "http://host.docker.internal:11434/v1")
        self.assertEqual(embedder.model, "qwen3-embedding:0.6b")
        self.assertEqual(embedder.dimension, 1024)
        self.assertIsNone(embedder.api_key)

    def test_validator_rejects_persisted_asset_mismatch(self) -> None:
        validator = EmbeddingStartupValidator(
            EmbeddingSettings(
                provider="aliyun",
                api_key="secret",
                base_url="https://example.com/v1",
                model="text-embedding-v4",
                dimension=1024,
                timeout_seconds=60.0,
                max_batch_size=32,
            ),
            existing_model_loader=lambda: ["aliyun:text-embedding-v3:1024"],
            milvus_dimension_loader=lambda: 1024,
            embedder_factory=lambda: FakeEmbedder(dimension=1024),
        )

        with self.assertRaises(AppError) as context:
            validator.validate_or_raise()

        self.assertEqual(context.exception.code, "EMBEDDING_ASSET_MISMATCH")
        self.assertEqual(
            context.exception.details["configured_asset_id"],
            "aliyun:text-embedding-v4:1024",
        )

    def test_validator_rejects_probe_dimension_mismatch(self) -> None:
        validator = EmbeddingStartupValidator(
            EmbeddingSettings(
                provider="aliyun",
                api_key="secret",
                base_url="https://example.com/v1",
                model="text-embedding-v4",
                dimension=1024,
                timeout_seconds=60.0,
                max_batch_size=32,
            ),
            existing_model_loader=lambda: [],
            milvus_dimension_loader=lambda: None,
            embedder_factory=lambda: FakeEmbedder(dimension=768),
        )

        with self.assertRaises(AppError) as context:
            validator.validate_or_raise()

        self.assertEqual(context.exception.code, "EMBEDDING_PROBE_INVALID")
        self.assertEqual(context.exception.details["probe_dimension"], 768)

    def test_validator_logs_successful_startup_validation(self) -> None:
        validator = EmbeddingStartupValidator(
            EmbeddingSettings(
                provider="aliyun",
                api_key="secret",
                base_url="https://example.com/v1",
                model="text-embedding-v4",
                dimension=1024,
                timeout_seconds=60.0,
                max_batch_size=32,
            ),
            existing_model_loader=lambda: [],
            milvus_dimension_loader=lambda: None,
            embedder_factory=lambda: FakeEmbedder(dimension=1024),
        )

        with self.assertLogs("knowledgebase.embedding", level="INFO") as captured:
            validator.validate_or_raise()

        logs = "\n".join(captured.output)
        self.assertIn("embedding config loaded", logs)
        self.assertIn("embedding startup validation passed", logs)
