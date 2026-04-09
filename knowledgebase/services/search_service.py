from __future__ import annotations

import re

from pydantic import ValidationError

from knowledgebase.domain.exceptions import AppError
from knowledgebase.integrations.embedding.embedder import BaseEmbedder, build_embedder
from knowledgebase.integrations.milvus.collection_manager import MilvusCollectionManager
from knowledgebase.repositories.chunk_repository import ChunkRepository
from knowledgebase.schemas.search import (
    SearchCategoryOutput,
    SearchDocumentOutput,
    SearchHitOutput,
    SearchRetrieveInput,
    SearchRetrieveOutput,
)


class SearchService:
    """检索领域服务。"""

    QUESTION_PREFIX_PATTERNS = [
        r"^\s*what\s+is\s+",
        r"^\s*what\s+are\s+",
        r"^\s*define\s+",
        r"^\s*explain\s+",
        r"^\s*tell\s+me\s+about\s+",
        r"^\s*请解释(?:一下)?",
        r"^\s*请介绍(?:一下)?",
        r"^\s*什么是",
    ]
    QUERY_ALIAS_MAP = {
        "希尔伯特空间": "Hilbert space",
        "巴拿赫空间": "Banach space",
        "开映射定理": "Open Mapping Theorem",
        "哈恩巴拿赫定理": "Hahn-Banach Theorem",
        "哈恩-巴拿赫定理": "Hahn-Banach Theorem",
        "一致有界原理": "Uniform Boundedness Principle",
        "闭图定理": "Closed Graph Theorem",
    }

    def __init__(self, *, chunk_repository: ChunkRepository) -> None:
        self.chunk_repository = chunk_repository
        self.milvus = MilvusCollectionManager()
        self._embedder: BaseEmbedder | None = None

    def retrieve(self, payload: dict) -> dict:
        """执行知识库检索，并在 Milvus 命中后回查 PostgreSQL 业务数据。"""

        try:
            data = SearchRetrieveInput.model_validate(payload)
        except ValidationError as exc:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="检索参数不合法",
                error_type="validation_error",
                details={"errors": exc.errors()},
            ) from exc

        normalized_query = self._normalize_query_for_retrieval(data.query)

        dense_query_vector: list[float] | None = None
        if data.alpha < 1.0:
            # 只在需要语义召回时才初始化 embedding 客户端，避免纯 BM25 检索依赖外部向量服务。
            dense_query_vector = self._get_embedder().embed_texts([normalized_query])[0]

        milvus_hits = self.milvus.search_chunks(
            query_text=normalized_query,
            limit=data.limit,
            alpha=data.alpha,
            dense_query_vector=dense_query_vector,
            category_id=data.category_id,
            document_id=data.document_id,
        )
        if not milvus_hits:
            return SearchRetrieveOutput(
                query=data.query,
                alpha=data.alpha,
                retrieval_mode=self._resolve_retrieval_mode(data.alpha),
                total=0,
                items=[],
            ).model_dump(mode="json")

        chunk_rows = self.chunk_repository.list_search_rows(
            [item["chunk_id"] for item in milvus_hits]
        )

        items: list[SearchHitOutput] = []
        for hit in milvus_hits:
            row = chunk_rows.get(hit["chunk_id"])
            if row is None:
                continue

            chunk, document, category = row
            items.append(
                SearchHitOutput(
                    chunk_id=chunk.id,
                    chunk_uid=chunk.chunk_uid,
                    chunk_no=chunk.chunk_no,
                    page_no=chunk.page_no,
                    score=hit["score"],
                    content=chunk.content,
                    document=SearchDocumentOutput(
                        id=document.id,
                        document_uid=document.document_uid,
                        title=document.title,
                        file_name=document.file_name,
                        category_id=document.category_id,
                        version=document.version,
                    ),
                    category=SearchCategoryOutput(
                        id=category.id,
                        category_code=category.category_code,
                        name=category.name,
                    ),
                )
            )
            if len(items) >= data.limit:
                break

        return SearchRetrieveOutput(
            query=data.query,
            alpha=data.alpha,
            retrieval_mode=self._resolve_retrieval_mode(data.alpha),
            total=len(items),
            items=items,
        ).model_dump(mode="json")

    def _get_embedder(self) -> BaseEmbedder:
        """延迟构建向量模型客户端，减少纯词法检索场景下的外部依赖。"""

        if self._embedder is None:
            self._embedder = build_embedder()
        return self._embedder

    def _resolve_retrieval_mode(self, alpha: float) -> str:
        """根据 alpha 输出当前检索模式，便于上层 Agent 识别执行语义。"""

        if alpha <= 0.0:
            return "semantic"
        if alpha >= 1.0:
            return "lexical_bm25"
        return "hybrid"

    def _normalize_query_for_retrieval(self, query: str) -> str:
        """清洗问句模板并补充跨语言术语别名，减少 BM25 被停用问句干扰。"""

        normalized = query.strip()
        lowered = normalized.lower()
        for pattern in self.QUESTION_PREFIX_PATTERNS:
            if re.match(pattern, normalized, flags=re.IGNORECASE):
                normalized = re.sub(pattern, "", normalized, count=1, flags=re.IGNORECASE).strip()
                lowered = normalized.lower()
                break

        normalized = normalized.strip(" ?!？。；;，,：:")
        expanded_terms: list[str] = [normalized]
        for alias, target in self.QUERY_ALIAS_MAP.items():
            if alias in normalized and target not in normalized:
                expanded_terms.append(target)

        # 英文问句规整到核心概念，避免 "what/is" 等高频词影响 BM25 排序。
        if lowered.startswith("hilbert space"):
            return "Hilbert space"
        if lowered.startswith("banach space"):
            return "Banach space"
        if lowered.startswith("open mapping theorem"):
            return "Open Mapping Theorem"

        return " ".join(term for term in expanded_terms if term).strip() or query.strip()
