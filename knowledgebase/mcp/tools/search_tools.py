from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from knowledgebase.db.session import session_scope
from knowledgebase.domain.exceptions import AppError
from knowledgebase.repositories.chunk_repository import ChunkRepository
from knowledgebase.schemas.common import build_error_response, build_success_response
from knowledgebase.services.search_service import SearchService


def register_search_tools(mcp: Any) -> None:
    """注册检索相关 MCP Tool。

    检索粒度是 chunk，不是整篇文档。
    Agent 获得的结果已经过 PostgreSQL 回查，可直接用于问答、引用和后续重排。
    """

    @mcp.tool(
        name="kb_search_retrieve",
        description="执行知识库检索，支持语义检索、BM25 检索和混合检索，并返回结构化 chunk 命中结果。",
    )
    async def kb_search_retrieve(
        query: str,
        alpha: float = 0.0,
        limit: int = 10,
        category_id: int | None = None,
        document_id: int | None = None,
        request_id: str | None = None,
        operator: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """执行检索 Tool，并按照统一响应协议返回结果。

        Agent 使用建议：
        - `alpha=0.0` 为纯语义检索
        - `alpha=1.0` 为纯 BM25 词法检索
        - 中间值表示混合检索
        - `category_id` 与 `document_id` 可用于限定检索范围
        """

        payload = {
            "query": query,
            "alpha": alpha,
            "limit": limit,
            "category_id": category_id,
            "document_id": document_id,
            "request_id": request_id,
            "operator": operator,
            "trace_id": trace_id,
        }
        return await run_in_threadpool(_execute_search, payload)


def _execute_search(payload: dict[str, Any]) -> dict[str, Any]:
    """执行检索 Tool，并统一处理参数、数据库和系统异常。

    返回结果已经过滤掉已删除或状态异常的业务数据，Agent 不需要再自行二次清洗。
    """

    try:
        with session_scope() as session:
            service = SearchService(
                chunk_repository=ChunkRepository(session),
            )
            result = service.retrieve(payload)
            return build_success_response(
                data=result,
                request_id=payload.get("request_id"),
                trace_id=payload.get("trace_id"),
            )
    except AppError as exc:
        return build_error_response(
            code=exc.code,
            message=exc.message,
            error_type=exc.error_type,
            details=exc.details,
            request_id=payload.get("request_id"),
            trace_id=payload.get("trace_id"),
        )
    except (ValidationError, SQLAlchemyError) as exc:
        return build_error_response(
            code="DB_ERROR" if isinstance(exc, SQLAlchemyError) else "INVALID_ARGUMENT",
            message="database operation failed" if isinstance(exc, SQLAlchemyError) else "invalid request",
            error_type="system_error" if isinstance(exc, SQLAlchemyError) else "validation_error",
            details={"error": str(exc)},
            request_id=payload.get("request_id"),
            trace_id=payload.get("trace_id"),
        )
    except Exception as exc:
        return build_error_response(
            code="INTERNAL_ERROR",
            message="internal server error",
            error_type="system_error",
            details={"error": str(exc)},
            request_id=payload.get("request_id"),
            trace_id=payload.get("trace_id"),
        )
