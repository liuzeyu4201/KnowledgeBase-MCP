from __future__ import annotations

from pymilvus import MilvusClient

from knowledgebase.app.config import get_settings


def build_milvus_client() -> MilvusClient:
    """构建 Milvus 客户端。"""

    settings = get_settings()
    return MilvusClient(uri=f"http://{settings.milvus_host}:{settings.milvus_port}")
