from __future__ import annotations

import json
from typing import Any

from pymilvus import AnnSearchRequest, DataType, Function, FunctionType, WeightedRanker

from knowledgebase.app.config import get_settings
from knowledgebase.integrations.milvus.client import build_milvus_client


class MilvusCollectionManager:
    """Milvus Collection 管理器。"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = build_milvus_client()
        self.collection_name = self.settings.milvus_collection_name

    def ensure_collection(self) -> None:
        """确保文档切片 Collection 已存在，并包含 BM25 与稠密向量索引。"""

        if self.client.has_collection(self.collection_name):
            if self.settings.milvus_recreate_collection and self._collection_needs_recreate():
                self.client.drop_collection(self.collection_name)
                self._create_collection()
                return
            self.client.load_collection(self.collection_name)
            return

        self._create_collection()

    def _create_collection(self) -> None:
        """创建文档切片 Collection，并配置分析器、函数和索引。"""

        schema = self.client.create_schema(auto_id=False, enable_dynamic_field=False)
        schema.add_field("chunk_id", DataType.INT64, is_primary=True)
        schema.add_field("document_id", DataType.INT64)
        schema.add_field("category_id", DataType.INT64)
        schema.add_field("chunk_no", DataType.INT32)
        schema.add_field("page_no", DataType.INT32)
        schema.add_field(
            "content",
            DataType.VARCHAR,
            max_length=65535,
            enable_analyzer=True,
            analyzer_params=self._build_analyzer_params(),
            enable_match=True,
        )
        schema.add_field(
            "dense_vector",
            DataType.FLOAT_VECTOR,
            dim=self.settings.embedding_dimension,
        )
        schema.add_field("sparse_vector", DataType.SPARSE_FLOAT_VECTOR)

        # 使用 Milvus BM25 内建函数从 content 自动生成稀疏向量。
        schema.add_function(
            Function(
                name="content_bm25_fn",
                input_field_names=["content"],
                output_field_names=["sparse_vector"],
                function_type=FunctionType.BM25,
            )
        )

        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="dense_vector",
            index_type=self.settings.milvus_dense_index_type,
            metric_type=self.settings.milvus_dense_metric_type,
        )
        index_params.add_index(
            field_name="sparse_vector",
            index_type=self.settings.milvus_sparse_index_type,
            metric_type="BM25",
        )

        self.client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params,
        )
        self.client.load_collection(self.collection_name)

    def insert_chunks(self, rows: list[dict[str, Any]]) -> None:
        """插入切片向量数据到 Milvus。"""

        if not rows:
            return
        self.ensure_collection()
        self.client.insert(collection_name=self.collection_name, data=rows)
        # 导入链路在返回前主动 flush，避免后续统计和检索可见性出现短暂滞后。
        self.client.flush(collection_name=self.collection_name)

    def search_chunks(
        self,
        *,
        query_text: str,
        limit: int,
        alpha: float,
        dense_query_vector: list[float] | None = None,
        category_id: int | None = None,
        document_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """执行 Milvus 检索，并根据 alpha 在语义检索与 BM25 之间切换或融合。"""

        self.ensure_collection()
        expr = self._build_filter_expr(category_id=category_id, document_id=document_id)
        search_limit = min(max(limit * 3, limit), 100)
        output_fields = ["chunk_id", "document_id", "category_id", "chunk_no", "page_no"]

        if alpha <= 0.0:
            if dense_query_vector is None:
                raise ValueError("dense_query_vector is required when alpha <= 0")
            result = self.client.search(
                collection_name=self.collection_name,
                data=[dense_query_vector],
                anns_field="dense_vector",
                filter=expr,
                limit=search_limit,
                output_fields=output_fields,
                search_params={"metric_type": self.settings.milvus_dense_metric_type},
            )
            return self._normalize_hits(result)

        if alpha >= 1.0:
            result = self.client.search(
                collection_name=self.collection_name,
                data=[query_text],
                anns_field="sparse_vector",
                filter=expr,
                limit=search_limit,
                output_fields=output_fields,
                search_params={"metric_type": "BM25"},
            )
            return self._normalize_hits(result)

        if dense_query_vector is None:
            raise ValueError("dense_query_vector is required when 0 < alpha < 1")

        req_dense = AnnSearchRequest(
            data=[dense_query_vector],
            anns_field="dense_vector",
            param={"metric_type": self.settings.milvus_dense_metric_type},
            limit=search_limit,
            expr=expr,
        )
        req_sparse = AnnSearchRequest(
            data=[query_text],
            anns_field="sparse_vector",
            param={"metric_type": "BM25"},
            limit=search_limit,
            expr=expr,
        )
        result = self.client.hybrid_search(
            collection_name=self.collection_name,
            reqs=[req_dense, req_sparse],
            ranker=WeightedRanker(1.0 - alpha, alpha),
            limit=search_limit,
            output_fields=output_fields,
        )
        return self._normalize_hits(result)

    def delete_chunks(self, chunk_ids: list[int]) -> None:
        """按切片主键删除 Milvus 中已写入的向量记录。"""

        if not chunk_ids:
            return
        if not self.client.has_collection(self.collection_name):
            return
        self.client.delete(
            collection_name=self.collection_name,
            ids=chunk_ids,
        )
        self.client.flush(collection_name=self.collection_name)

    def fetch_chunks(self, chunk_ids: list[int]) -> list[dict[str, Any]]:
        """读取 Milvus 中已有切片记录，用于删除失败后的补偿恢复。"""

        if not chunk_ids:
            return []
        if not self.client.has_collection(self.collection_name):
            return []
        result = self.client.query(
            collection_name=self.collection_name,
            ids=chunk_ids,
            output_fields=[
                "chunk_id",
                "document_id",
                "category_id",
                "chunk_no",
                "page_no",
                "content",
                "dense_vector",
            ],
        )
        return list(result)

    def _build_analyzer_params(self) -> dict[str, Any]:
        """构建 BM25 文本分析器参数。"""

        analyzer = self.settings.milvus_analyzer.lower()
        if analyzer == "language_identifier":
            return {
                "tokenizer": {
                    "type": "language_identifier",
                    "identifier": "whatlang",
                    "analyzers": {
                        "default": {
                            "tokenizer": "standard",
                            "filter": ["lowercase"],
                        },
                        "English": {
                            "tokenizer": "standard",
                            "filter": ["lowercase"],
                        },
                        "Mandarin": {
                            "tokenizer": "jieba",
                            "filter": ["removepunct"],
                        },
                    },
                }
            }
        if analyzer == "jieba":
            return {
                "tokenizer": "jieba",
                "filter": ["removepunct"],
            }
        if analyzer == "standard":
            return {
                "tokenizer": "standard",
                "filter": ["lowercase"],
            }
        return {"tokenizer": analyzer}

    def _build_filter_expr(
        self,
        *,
        category_id: int | None,
        document_id: int | None,
    ) -> str:
        """根据业务过滤条件构建 Milvus 表达式。"""

        clauses: list[str] = []
        if category_id is not None:
            clauses.append(f"category_id == {category_id}")
        if document_id is not None:
            clauses.append(f"document_id == {document_id}")
        return " && ".join(clauses)

    def _collection_needs_recreate(self) -> bool:
        """检查现有 Collection 是否与期望的分析器配置一致。"""

        schema = self.client.describe_collection(collection_name=self.collection_name)
        content_field = next(
            (field for field in schema.get("fields", []) if field.get("name") == "content"),
            None,
        )
        if content_field is None:
            return True

        raw_analyzer = (
            content_field.get("params", {}).get("analyzer_params")
            or "{}"
        )
        try:
            current_analyzer = json.loads(raw_analyzer)
        except json.JSONDecodeError:
            return True

        return current_analyzer != self._build_analyzer_params()

    def _normalize_hits(self, result: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        """把 Milvus 返回结果整理成统一结构，便于服务层回查业务数据。"""

        hits = result[0] if result else []
        normalized: list[dict[str, Any]] = []
        for item in hits:
            entity = item.get("entity") or {}
            normalized.append(
                {
                    "chunk_id": entity.get("chunk_id", item.get("id")),
                    "document_id": entity.get("document_id"),
                    "category_id": entity.get("category_id"),
                    "chunk_no": entity.get("chunk_no"),
                    "page_no": entity.get("page_no"),
                    "score": item.get("distance"),
                }
            )
        return normalized
