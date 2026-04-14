from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from knowledgebase.app.config import get_settings
from knowledgebase.domain.exceptions import AppError


class BaseEmbedder(ABC):
    """Embedding 抽象基类。"""

    provider: str
    model: str
    dimension: int

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """批量生成稠密向量。"""

    @property
    def asset_id(self) -> str:
        """返回当前向量资产签名。"""

        return f"{self.provider}:{self.model}:{self.dimension}"


class OpenAICompatibleEmbedder(BaseEmbedder):
    """兼容 OpenAI Embeddings API 的向量服务。"""

    def __init__(self, *, require_api_key: bool) -> None:
        embedding_settings = get_settings().embedding
        self.provider = embedding_settings.provider
        self.api_key = embedding_settings.api_key
        self.base_url = embedding_settings.base_url.rstrip("/")
        self.model = embedding_settings.model
        self.dimension = embedding_settings.dimension
        self.timeout_seconds = embedding_settings.timeout_seconds
        self.max_batch_size = embedding_settings.max_batch_size
        self.require_api_key = require_api_key

        if self.require_api_key and not self.api_key:
            raise AppError(
                code="INTERNAL_ERROR",
                message="KNOWLEDGEBASE_EMBEDDING_API_KEY is not configured",
                error_type="system_error",
            )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """调用阿里百炼兼容模式 Embedding 接口生成稠密向量。"""

        if not texts:
            return []

        vectors: list[list[float]] = []
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                for start in range(0, len(texts), self.max_batch_size):
                    batch = texts[start : start + self.max_batch_size]
                    response = client.post(
                        f"{self.base_url}/embeddings",
                        headers=self._build_headers(),
                        json={
                            "model": self.model,
                            "input": batch,
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
                    if len(data) != len(batch):
                        raise AppError(
                            code="INTERNAL_ERROR",
                            message="embedding response size mismatch",
                            error_type="system_error",
                            details={"expected": len(batch), "actual": len(data)},
                        )
                    for item in sorted(data, key=lambda row: row.get("index", 0)):
                        vectors.append(item["embedding"])
        except httpx.HTTPError as exc:
            raise AppError(
                code="INTERNAL_ERROR",
                message="embedding request failed",
                error_type="system_error",
                details={"reason": str(exc)},
            ) from exc

        return vectors

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


class AliyunEmbedder(OpenAICompatibleEmbedder):
    """阿里百炼在线向量服务。"""

    def __init__(self) -> None:
        super().__init__(require_api_key=True)


class OllamaEmbedder(OpenAICompatibleEmbedder):
    """Ollama OpenAI 兼容 Embedding 服务。"""

    def __init__(self) -> None:
        super().__init__(require_api_key=False)


def build_embedder() -> BaseEmbedder:
    """根据配置构建向量服务实现。"""

    provider = get_settings().embedding.provider.lower()
    if provider == "aliyun":
        return AliyunEmbedder()
    if provider == "ollama":
        return OllamaEmbedder()
    raise AppError(
        code="INTERNAL_ERROR",
        message=f"unsupported embedding provider: {provider}",
        error_type="system_error",
    )
