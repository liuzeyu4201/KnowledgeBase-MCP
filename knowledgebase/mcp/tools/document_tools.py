from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from knowledgebase.db.session import SessionFactory
from knowledgebase.domain.exceptions import AppError
from knowledgebase.repositories.category_repository import CategoryRepository
from knowledgebase.repositories.chunk_repository import ChunkRepository
from knowledgebase.repositories.document_repository import DocumentRepository
from knowledgebase.schemas.common import build_error_response, build_success_response
from knowledgebase.services.document_service import DocumentService


def register_document_tools(mcp: Any) -> None:
    """注册文档相关 MCP Tool。"""

    @mcp.tool(name="kb_document_get", description="按主键或文档唯一标识查询文档详情")
    def kb_document_get(
        id: int | None = None,
        document_uid: str | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """读取单个文档详情。"""

        payload = {
            "id": id,
            "document_uid": document_uid,
            "request_id": request_id,
            "trace_id": trace_id,
        }
        return _execute_read(payload=payload, action="get")

    @mcp.tool(name="kb_document_list", description="分页查询文档列表")
    def kb_document_list(
        category_id: int | None = None,
        title: str | None = None,
        file_name: str | None = None,
        parse_status: str | None = None,
        vector_status: str | None = None,
        page: int = 1,
        page_size: int = 20,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """按过滤条件分页查询文档列表。"""

        payload = {
            "category_id": category_id,
            "title": title,
            "file_name": file_name,
            "parse_status": parse_status,
            "vector_status": vector_status,
            "page": page,
            "page_size": page_size,
            "request_id": request_id,
            "trace_id": trace_id,
        }
        return _execute_read(payload=payload, action="list")

    @mcp.tool(name="kb_document_import", description="导入 PDF 文档并写入向量索引")
    def kb_document_import(
        category_id: int,
        title: str,
        file_name: str,
        mime_type: str,
        file_content_base64: str,
        request_id: str | None = None,
        operator: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """导入 PDF 文档并构建稠密向量与 BM25 索引。"""

        payload = {
            "category_id": category_id,
            "title": title,
            "file_name": file_name,
            "mime_type": mime_type,
            "file_content_base64": file_content_base64,
            "request_id": request_id,
            "operator": operator,
            "trace_id": trace_id,
        }
        return _execute_write(payload)

    @mcp.tool(name="kb_document_delete", description="按主键或文档唯一标识删除文档")
    def kb_document_delete(
        id: int | None = None,
        document_uid: str | None = None,
        request_id: str | None = None,
        operator: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """删除文档，并级联清理切片、向量和原始文件。"""

        payload = {
            "id": id,
            "document_uid": document_uid,
            "request_id": request_id,
            "operator": operator,
            "trace_id": trace_id,
        }
        return _execute_write(payload, action="delete")

    @mcp.tool(name="kb_document_update", description="更新文档元数据，或整篇替换 PDF 并重建切片与向量")
    def kb_document_update(
        id: int | None = None,
        document_uid: str | None = None,
        category_id: int | None = None,
        title: str | None = None,
        file_name: str | None = None,
        mime_type: str | None = None,
        file_content_base64: str | None = None,
        request_id: str | None = None,
        operator: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """更新文档，可仅修改元数据，也可替换 PDF 触发整篇重建。"""

        payload = {
            "id": id,
            "document_uid": document_uid,
            "category_id": category_id,
            "title": title,
            "file_name": file_name,
            "mime_type": mime_type,
            "file_content_base64": file_content_base64,
            "request_id": request_id,
            "operator": operator,
            "trace_id": trace_id,
        }
        return _execute_write(payload, action="update")


def _execute_read(*, payload: dict[str, Any], action: str) -> dict[str, Any]:
    """执行读取类文档 Tool，并统一处理异常响应。"""

    session = SessionFactory()
    service = DocumentService(
        category_repository=CategoryRepository(session),
        document_repository=DocumentRepository(session),
        chunk_repository=ChunkRepository(session),
    )
    try:
        if action == "get":
            document = service.get_document(payload)
            return build_success_response(
                data={"document": document.model_dump(mode="json")},
                request_id=payload.get("request_id"),
                trace_id=payload.get("trace_id"),
            )
        if action == "list":
            items, pagination = service.list_documents(payload)
            return build_success_response(
                data={
                    "items": [item.model_dump(mode="json") for item in items],
                    "pagination": pagination,
                },
                request_id=payload.get("request_id"),
                trace_id=payload.get("trace_id"),
            )
        raise RuntimeError(f"unsupported action: {action}")
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
    finally:
        session.close()


def _execute_write(payload: dict[str, Any], action: str = "import") -> dict[str, Any]:
    """执行文档导入 Tool，并统一处理异常响应。"""

    session = SessionFactory()
    service = DocumentService(
        category_repository=CategoryRepository(session),
        document_repository=DocumentRepository(session),
        chunk_repository=ChunkRepository(session),
    )
    try:
        if action == "import":
            result = service.import_document(payload)
        elif action == "update":
            result = service.update_document(payload)
        elif action == "delete":
            result = service.delete_document(payload)
        else:
            raise RuntimeError(f"unsupported action: {action}")
        session.commit()
        service.clear_import_context()
    except AppError as exc:
        rollback_error = _rollback_write_action(service=service, action=action, error=exc)
        final_error = rollback_error or exc
        return build_error_response(
            code=final_error.code,
            message=final_error.message,
            error_type=final_error.error_type,
            details=final_error.details,
            request_id=payload.get("request_id"),
            trace_id=payload.get("trace_id"),
        )
    except (ValidationError, SQLAlchemyError) as exc:
        rollback_error = _rollback_write_action(service=service, action=action, error=exc)
        if rollback_error is not None:
            return build_error_response(
                code=rollback_error.code,
                message=rollback_error.message,
                error_type=rollback_error.error_type,
                details=rollback_error.details,
                request_id=payload.get("request_id"),
                trace_id=payload.get("trace_id"),
            )
        return build_error_response(
            code="DB_ERROR" if isinstance(exc, SQLAlchemyError) else "INVALID_ARGUMENT",
            message="database operation failed" if isinstance(exc, SQLAlchemyError) else "invalid request",
            error_type="system_error" if isinstance(exc, SQLAlchemyError) else "validation_error",
            details={"error": str(exc)},
            request_id=payload.get("request_id"),
            trace_id=payload.get("trace_id"),
        )
    except Exception as exc:
        rollback_error = _rollback_write_action(service=service, action=action, error=exc)
        if rollback_error is not None:
            return build_error_response(
                code=rollback_error.code,
                message=rollback_error.message,
                error_type=rollback_error.error_type,
                details=rollback_error.details,
                request_id=payload.get("request_id"),
                trace_id=payload.get("trace_id"),
            )
        return build_error_response(
            code="INTERNAL_ERROR",
            message="internal server error",
            error_type="system_error",
            details={"error": str(exc)},
            request_id=payload.get("request_id"),
            trace_id=payload.get("trace_id"),
        )
    finally:
        session.close()

    if action == "delete":
        try:
            service.finalize_delete_context()
        except Exception as exc:
            return build_error_response(
                code="DELETE_CLEANUP_FAILED",
                message="document deleted but cleanup failed",
                error_type="system_error",
                details={"error": str(exc)},
                request_id=payload.get("request_id"),
                trace_id=payload.get("trace_id"),
            )
    if action == "update":
        try:
            service.finalize_update_context()
        except Exception as exc:
            return build_error_response(
                code="UPDATE_CLEANUP_FAILED",
                message="document updated but cleanup failed",
                error_type="system_error",
                details={"error": str(exc)},
                request_id=payload.get("request_id"),
                trace_id=payload.get("trace_id"),
            )

    return build_success_response(
        data=result,
        request_id=payload.get("request_id"),
        trace_id=payload.get("trace_id"),
    )


def _rollback_write_action(
    *,
    service: DocumentService,
    action: str,
    error: Exception,
) -> AppError | None:
    """按写入动作类型选择对应的补偿逻辑。"""

    if action == "import":
        return service.rollback_import_side_effects(original_error=error)
    if action == "delete":
        return service.rollback_delete_side_effects(original_error=error)
    if action == "update":
        return service.rollback_update_side_effects(original_error=error)
    return None
