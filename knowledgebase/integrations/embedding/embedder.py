from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod

import httpx

from knowledgebase.app.config import get_settings
from knowledgebase.domain.exceptions import AppError


class BaseEmbedder(ABC):
    """Embedding 抽象基类。"""

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """批量生成稠密向量。"""


class MockEmbedder(BaseEmbedder):
    """用于本地开发的模拟向量服务。"""

    def __init__(self) -> None:
        self.dimension = get_settings().embedding_dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            values = []
            while len(values) < self.dimension:
                digest = hashlib.sha256(digest).digest()
                values.extend(((byte / 255.0) * 2.0 - 1.0) for byte in digest)
            vector = values[: self.dimension]
            norm = math.sqrt(sum(item * item for item in vector)) or 1.0
            vectors.append([item / norm for item in vector])
        return vectors


class AliyunEmbedder(BaseEmbedder):
    """阿里百炼在线向量服务。"""

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.embedding_api_key
        self.base_url = settings.embedding_base_url.rstrip("/")
        self.model = settings.embedding_model
        self.dimension = settings.embedding_dimension

        if not self.api_key:
            raise AppError(
                code="INTERNAL_ERROR",
                message="DASHSCOPE_API_KEY is not configured",
                error_type="system_error",
            )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """调用阿里百炼兼容模式 Embedding 接口生成稠密向量。"""

        vectors: list[list[float]] = []
        with httpx.Client(timeout=60.0) as client:
            for text in texts:
                response = client.post(
                    f"{self.base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "input": text,
                        "dimensions": self.dimension,
                        "encoding_format": "float",
                    },
                )
                if response.status_code >= 400:
                    raise AppError(
                        code="INTERNAL_ERROR",
                        message="embedding request failed",
                        error_type="system_error",
                        details={"status_code": response.status_code, "body": response.text},
                    )

                payload = response.json()
                data = payload.get("data") or []
                if not data:
                    raise AppError(
                        code="INTERNAL_ERROR",
                        message="embedding response is empty",
                        error_type="system_error",
                    )
                vectors.append(data[0]["embedding"])

        return vectors


def build_embedder() -> BaseEmbedder:
    """根据配置构建向量服务实现。"""

    provider = get_settings().embedding_provider.lower()
    if provider == "mock":
        return MockEmbedder()
    if provider == "aliyun":
        return AliyunEmbedder()
    raise AppError(
        code="INTERNAL_ERROR",
        message=f"unsupported embedding provider: {provider}",
        error_type="system_error",
    )
