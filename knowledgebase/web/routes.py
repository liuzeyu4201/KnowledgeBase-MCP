from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
import logging
import re
from typing import Any

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse

from knowledgebase.domain.exceptions import AppError
from knowledgebase.schemas.common import build_error_response, build_success_response
from knowledgebase.web.mcp_gateway import MCPGateway


logger = logging.getLogger("knowledgebase.web")
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
PAGES_DIR = STATIC_DIR / "pages"

page_router = APIRouter()
api_router = APIRouter(prefix="/api/visualization", tags=["visualization"])
ws_router = APIRouter()


@page_router.get("/")
def web_home() -> FileResponse:
    """返回知识库可视化首页。"""

    return FileResponse(PAGES_DIR / "index.html")


@page_router.get("/ui")
def web_home_alias() -> FileResponse:
    """保留 `/ui` 作为前端首页别名。"""

    return FileResponse(PAGES_DIR / "index.html")


@page_router.get("/ui/categories/{category_id}")
def web_category_page(category_id: int) -> FileResponse:
    """返回分类文档列表页面。"""

    return FileResponse(PAGES_DIR / "category.html")


@page_router.get("/ui/documents/{document_id}")
def web_document_page(document_id: int) -> FileResponse:
    """返回文档原文详情页面。"""

    return FileResponse(PAGES_DIR / "document.html")


@page_router.get("/ui/documents/{document_id}/chunks")
def web_document_chunk_page(document_id: int) -> FileResponse:
    """返回文档 Chunk 原文页面。"""

    return FileResponse(PAGES_DIR / "document-chunks.html")


@api_router.get("/categories")
async def list_visual_categories(
    request: Request,
    keyword: str | None = None,
    category_code: str | None = None,
    name: str | None = None,
    status: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> JSONResponse:
    """返回首页分类卡片数据。

    这里会严格调用 MCP 的分类列表与文档列表接口，再在网页层做轻量聚合，
    例如补齐 `document_count` 和最近更新时间，避免网页直接绕开 MCP 读数据库。
    """

    context = _request_context(request)
    normalized_keyword = (keyword or "").strip() or None
    if normalized_keyword:
        if _is_category_code_keyword(normalized_keyword):
            category_code = normalized_keyword
            name = None
        else:
            name = normalized_keyword
            category_code = None
    try:
        async with MCPGateway() as gateway:
            category_payload = await gateway.list_categories(
                {
                    "category_code": category_code,
                    "name": name,
                    "status": status,
                    "page": page,
                    "page_size": page_size,
                    "request_id": context["request_id"],
                    "trace_id": context["trace_id"],
                }
            )
            categories = category_payload["data"]["items"]
            pagination = category_payload["data"]["pagination"]
            enriched_items = await asyncio.gather(
                *[
                    _enrich_category_card(gateway, category, context)
                    for category in categories
                ]
            )
        logger.info(
            "web business list categories count=%s request_id=%s trace_id=%s",
            len(enriched_items),
            context["request_id"],
            context["trace_id"],
        )
        return JSONResponse(
            content=build_success_response(
                data={"items": enriched_items, "pagination": pagination},
                request_id=context["request_id"],
                trace_id=context["trace_id"],
            )
        )
    except AppError as exc:
        return _error_response(exc, context)
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "web error list categories request_id=%s trace_id=%s",
            context["request_id"],
            context["trace_id"],
        )
        return _internal_error_response(exc, context)


@api_router.get("/categories/{category_id}/documents")
async def list_visual_documents(
    request: Request,
    category_id: int,
    title: str | None = None,
    file_name: str | None = None,
    parse_status: str | None = None,
    vector_status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> JSONResponse:
    """返回某个分类下的文档列表页面数据。"""

    context = _request_context(request)
    try:
        async with MCPGateway() as gateway:
            category_payload = await gateway.get_category(
                {
                    "id": category_id,
                    "request_id": context["request_id"],
                    "trace_id": context["trace_id"],
                }
            )
            document_payload = await gateway.list_documents(
                {
                    "category_id": category_id,
                    "title": title,
                    "file_name": file_name,
                    "parse_status": parse_status,
                    "vector_status": vector_status,
                    "page": page,
                    "page_size": page_size,
                    "request_id": context["request_id"],
                    "trace_id": context["trace_id"],
                }
            )
        items = [_build_document_card(item) for item in document_payload["data"]["items"]]
        logger.info(
            "web business list documents category_id=%s count=%s request_id=%s trace_id=%s",
            category_id,
            len(items),
            context["request_id"],
            context["trace_id"],
        )
        return JSONResponse(
            content=build_success_response(
                data={
                    "category": category_payload["data"]["category"],
                    "items": items,
                    "pagination": document_payload["data"]["pagination"],
                },
                request_id=context["request_id"],
                trace_id=context["trace_id"],
            )
        )
    except AppError as exc:
        return _error_response(exc, context)
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "web error list documents category_id=%s request_id=%s trace_id=%s",
            category_id,
            context["request_id"],
            context["trace_id"],
        )
        return _internal_error_response(exc, context)


@api_router.delete("/categories/{category_id}")
async def delete_visual_category(request: Request, category_id: int) -> JSONResponse:
    """删除分类。该操作保持 MCP 侧“先删文档再删分类”的业务约束。"""

    context = _request_context(request)
    try:
        async with MCPGateway() as gateway:
            payload = await gateway.delete_category(
                {
                    "id": category_id,
                    "request_id": context["request_id"],
                    "trace_id": context["trace_id"],
                }
            )
        logger.info(
            "web business delete category category_id=%s request_id=%s trace_id=%s",
            category_id,
            context["request_id"],
            context["trace_id"],
        )
        return JSONResponse(content=payload)
    except AppError as exc:
        return _error_response(exc, context)
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "web error delete category category_id=%s request_id=%s trace_id=%s",
            category_id,
            context["request_id"],
            context["trace_id"],
        )
        return _internal_error_response(exc, context)


@api_router.delete("/documents/{document_id}")
async def delete_visual_document(request: Request, document_id: int) -> JSONResponse:
    """删除文档。该操作会级联清理源文件、切片与向量。"""

    context = _request_context(request)
    try:
        async with MCPGateway() as gateway:
            payload = await gateway.delete_document(
                {
                    "id": document_id,
                    "request_id": context["request_id"],
                    "trace_id": context["trace_id"],
                }
            )
        logger.info(
            "web business delete document document_id=%s request_id=%s trace_id=%s",
            document_id,
            context["request_id"],
            context["trace_id"],
        )
        return JSONResponse(content=payload)
    except AppError as exc:
        return _error_response(exc, context)
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "web error delete document document_id=%s request_id=%s trace_id=%s",
            document_id,
            context["request_id"],
            context["trace_id"],
        )
        return _internal_error_response(exc, context)


@api_router.get("/import-tasks/{task_id}")
async def get_visual_import_task(request: Request, task_id: int) -> JSONResponse:
    """返回批量导入任务详情，供前端轮询或初始化 WebSocket 观察面板。"""

    context = _request_context(request)
    try:
        async with MCPGateway() as gateway:
            payload = await gateway.get_import_task(
                {
                    "id": task_id,
                    "request_id": context["request_id"],
                    "trace_id": context["trace_id"],
                }
            )
        task, items = _normalize_task_payload(payload["data"])
        return JSONResponse(
            content=build_success_response(
                data={"task": task, "items": items},
                request_id=context["request_id"],
                trace_id=context["trace_id"],
            )
        )
    except AppError as exc:
        return _error_response(exc, context)
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "web error get import task task_id=%s request_id=%s trace_id=%s",
            task_id,
            context["request_id"],
            context["trace_id"],
        )
        return _internal_error_response(exc, context)


@api_router.get("/documents/{document_id}/content")
async def get_visual_document_content(request: Request, document_id: int) -> JSONResponse:
    """返回单个文档的原文视图和 chunk 原文。"""

    context = _request_context(request)
    source_page = max(1, int(request.query_params.get("source_page", "1")))
    source_page_size = max(1, min(20, int(request.query_params.get("source_page_size", "1"))))
    chunk_page = max(1, int(request.query_params.get("chunk_page", "1")))
    chunk_page_size = max(1, min(50, int(request.query_params.get("chunk_page_size", "5"))))
    try:
        async with MCPGateway() as gateway:
            payload = await gateway.get_document_content(
                {
                    "id": document_id,
                    "source_page": source_page,
                    "source_page_size": source_page_size,
                    "chunk_page": chunk_page,
                    "chunk_page_size": chunk_page_size,
                    "request_id": context["request_id"],
                    "trace_id": context["trace_id"],
                }
            )
        data = payload["data"]
        document = data["document"]
        logger.info(
            "web business get document content document_id=%s chunks=%s request_id=%s trace_id=%s",
            document_id,
            len(data["chunks"]),
            context["request_id"],
            context["trace_id"],
        )
        return JSONResponse(
            content=build_success_response(
                data={
                    "document": document,
                    "source_available": data["source_available"],
                    "source_error": data["source_error"],
                    "source_pages": data["source_pages"],
                    "source_pagination": data["source_pagination"],
                    "chunks": data["chunks"],
                    "chunk_pagination": data["chunk_pagination"],
                },
                request_id=context["request_id"],
                trace_id=context["trace_id"],
            )
        )
    except AppError as exc:
        return _error_response(exc, context)
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "web error get document content document_id=%s request_id=%s trace_id=%s",
            document_id,
            context["request_id"],
            context["trace_id"],
        )
        return _internal_error_response(exc, context)


@api_router.get("/documents/{document_id}/chunks")
async def get_visual_document_chunks(request: Request, document_id: int) -> JSONResponse:
    """返回单个文档的 chunk 原文分页视图。"""

    context = _request_context(request)
    chunk_page = max(1, int(request.query_params.get("chunk_page", "1")))
    chunk_page_size = max(1, min(50, int(request.query_params.get("chunk_page_size", "5"))))
    try:
        async with MCPGateway() as gateway:
            payload = await gateway.get_document_content(
                {
                    "id": document_id,
                    "source_page": 1,
                    "source_page_size": 1,
                    "chunk_page": chunk_page,
                    "chunk_page_size": chunk_page_size,
                    "request_id": context["request_id"],
                    "trace_id": context["trace_id"],
                }
            )
        data = payload["data"]
        document = data["document"]
        logger.info(
            "web business get document chunks document_id=%s chunks=%s request_id=%s trace_id=%s",
            document_id,
            len(data["chunks"]),
            context["request_id"],
            context["trace_id"],
        )
        return JSONResponse(
            content=build_success_response(
                data={
                    "document": document,
                    "chunks": data["chunks"],
                    "chunk_pagination": data["chunk_pagination"],
                },
                request_id=context["request_id"],
                trace_id=context["trace_id"],
            )
        )
    except AppError as exc:
        return _error_response(exc, context)
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "web error get document chunks document_id=%s request_id=%s trace_id=%s",
            document_id,
            context["request_id"],
            context["trace_id"],
        )
        return _internal_error_response(exc, context)


@ws_router.websocket("/ws/import-tasks/{task_id}")
async def import_task_websocket(websocket: WebSocket, task_id: int) -> None:
    """把批量导入任务状态持续推送给前端。

    第一版采用服务端轮询 MCP Tool，再通过 WebSocket 推送，保证网页看到的任务状态
    与 MCP Server 对外暴露的状态完全一致。
    """

    await websocket.accept()
    request_id = websocket.headers.get("x-request-id") or f"ws-{task_id}"
    trace_id = websocket.headers.get("x-trace-id") or request_id
    logger.info(
        "web websocket connected task_id=%s request_id=%s trace_id=%s",
        task_id,
        request_id,
        trace_id,
    )
    try:
        async with MCPGateway() as gateway:
            while True:
                payload = await gateway.get_import_task(
                    {"id": task_id, "request_id": request_id, "trace_id": trace_id}
                )
                task, items = _normalize_task_payload(payload["data"])
                await websocket.send_json(
                    build_success_response(
                        data={"task": task, "items": items},
                        request_id=request_id,
                        trace_id=trace_id,
                    )
                )
                if task["status"] in {"success", "failed", "partial_success", "canceled"}:
                    break
                await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        logger.info(
            "web websocket disconnected task_id=%s request_id=%s trace_id=%s",
            task_id,
            request_id,
            trace_id,
        )
    except AppError as exc:
        await websocket.send_json(
            build_error_response(
                code=exc.code,
                message=exc.message,
                error_type=exc.error_type,
                details=exc.details,
                request_id=request_id,
                trace_id=trace_id,
            )
        )
        await websocket.close(code=1011)
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "web websocket error task_id=%s request_id=%s trace_id=%s",
            task_id,
            request_id,
            trace_id,
        )
        await websocket.send_json(
            build_error_response(
                code="INTERNAL_ERROR",
                message="internal server error",
                error_type="system_error",
                details={"error": str(exc)},
                request_id=request_id,
                trace_id=trace_id,
            )
        )
        await websocket.close(code=1011)


async def _enrich_category_card(
    gateway: MCPGateway,
    category: dict[str, Any],
    context: dict[str, str],
) -> dict[str, Any]:
    """为分类卡片补齐文档总数和最近更新时间。"""

    documents_payload = await gateway.list_documents(
        {
            "category_id": category["id"],
            "page": 1,
            "page_size": 1,
            "request_id": context["request_id"],
            "trace_id": context["trace_id"],
        }
    )
    pagination = documents_payload["data"]["pagination"]
    latest_document = documents_payload["data"]["items"][0] if documents_payload["data"]["items"] else None
    updated_at = latest_document["updated_at"] if latest_document else category["updated_at"]
    return {
        "id": category["id"],
        "category_code": category["category_code"],
        "name": category["name"],
        "description": category["description"],
        "status": category["status"],
        "document_count": pagination["total"],
        "created_at": category["created_at"],
        "updated_at": updated_at,
    }


def _build_document_card(document: dict[str, Any]) -> dict[str, Any]:
    """裁剪文档列表页需要的字段。"""

    return {
        "id": document["id"],
        "document_uid": document["document_uid"],
        "title": document["title"],
        "file_name": document["file_name"],
        "mime_type": document["mime_type"],
        "parse_status": document["parse_status"],
        "vector_status": document["vector_status"],
        "version": document["version"],
        "chunk_count": document["chunk_count"],
        "storage_uri": document["storage_uri"],
        "updated_at": document["updated_at"],
        "created_at": document["created_at"],
    }


def _request_context(request: Request) -> dict[str, str]:
    """提取统一请求上下文。"""

    return {
        "request_id": getattr(request.state, "request_id", "unknown"),
        "trace_id": getattr(request.state, "trace_id", "unknown"),
    }


def _is_category_code_keyword(value: str) -> bool:
    """判断关键字是否符合分类编码格式。"""

    return re.fullmatch(r"[A-Za-z0-9_-]+", value) is not None


def _normalize_task_payload(data: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """把批量任务详情整理成稳定的 `task + items` 结构。"""

    task = data["task"]
    items = data.get("items")
    if items is None:
        items = task.get("items", [])
    return task, items


def _error_response(exc: AppError, context: dict[str, str]) -> JSONResponse:
    """构造领域错误响应。"""

    logger.warning(
        "web business error code=%s message=%s request_id=%s trace_id=%s",
        exc.code,
        exc.message,
        context["request_id"],
        context["trace_id"],
    )
    if exc.error_type == "system_error":
        status_code = 500
    elif exc.error_type == "not_found":
        status_code = 404
    else:
        status_code = 400
    return JSONResponse(
        status_code=status_code,
        content=build_error_response(
            code=exc.code,
            message=exc.message,
            error_type=exc.error_type,
            details=exc.details,
            request_id=context["request_id"],
            trace_id=context["trace_id"],
        ),
    )


def _internal_error_response(exc: Exception, context: dict[str, str]) -> JSONResponse:
    """构造系统异常响应。"""

    return JSONResponse(
        status_code=500,
        content=build_error_response(
            code="INTERNAL_ERROR",
            message="internal server error",
            error_type="system_error",
            details={"error": str(exc)},
            request_id=context["request_id"],
            trace_id=context["trace_id"],
        ),
    )


def format_datetime(value: str) -> str:
    """把 ISO 时间格式化为更适合前端展示的字符串。"""

    return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
