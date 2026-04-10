from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from knowledgebase.db.session import SessionFactory
from knowledgebase.domain.exceptions import AppError
from knowledgebase.repositories.category_repository import CategoryRepository
from knowledgebase.repositories.chunk_repository import ChunkRepository
from knowledgebase.repositories.document_repository import DocumentRepository
from knowledgebase.repositories.staged_file_repository import StagedFileRepository
from knowledgebase.schemas.common import build_error_response, build_success_response
from knowledgebase.services.document_service import DocumentService


def register_document_tools(mcp: Any) -> None:
    """注册文档相关 MCP Tool。

    文档 Tool 负责知识文档主实体的 CRUD。
    其中：
    - `*_from_staged` 是远端标准路径，推荐 Agent 始终优先使用
    - 直接 base64 直传的旧 Tool 已移除，避免远端大文件场景误用
    """

    @mcp.tool(
        name="kb_document_get",
        description="按主键或 document_uid 查询文档详情，返回文档元数据、状态和分类信息。",
    )
    def kb_document_get(
        id: int | None = None,
        document_uid: str | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """读取单个文档详情。

        Agent 使用建议：
        - `id` 与 `document_uid` 二选一
        - 适合在更新、删除、重建前确认文档当前状态
        """

        payload = {
            "id": id,
            "document_uid": document_uid,
            "request_id": request_id,
            "trace_id": trace_id,
        }
        return _execute_read(payload=payload, action="get")

    @mcp.tool(
        name="kb_document_list",
        description="分页查询文档列表，支持按分类、标题、文件名和处理状态过滤。",
    )
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
        """按过滤条件分页查询文档列表。

        Agent 使用建议：
        - 结果在 `data.items`
        - 适合在某个分类下浏览文档，或筛出失败文档做修复
        """

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

    @mcp.tool(
        name="kb_document_content_get",
        description="读取单个文档的原文视图和 chunk 原文，适合网页或 Agent 查看文档内容细节。",
    )
    def kb_document_content_get(
        id: int | None = None,
        document_uid: str | None = None,
        source_page: int = 1,
        source_page_size: int = 1,
        chunk_page: int = 1,
        chunk_page_size: int = 5,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """读取文档原文和 chunk 内容。

        Agent 使用建议：
        - `source_pages` 更接近原件解析后的内容
        - `chunks` 是系统真实入库并参与检索的文本片段
        """

        payload = {
            "id": id,
            "document_uid": document_uid,
            "source_page": source_page,
            "source_page_size": source_page_size,
            "chunk_page": chunk_page,
            "chunk_page_size": chunk_page_size,
            "request_id": request_id,
            "trace_id": trace_id,
        }
        return _execute_read(payload=payload, action="content_get")

    @mcp.tool(
        name="kb_document_import_from_staged",
        description="标准远端路径：引用 staged_file 导入文档并写入向量索引。",
    )
    def kb_document_import_from_staged(
        category_id: int,
        title: str,
        staged_file_id: int,
        request_id: str | None = None,
        operator: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """从暂存文件导入文档并构建向量索引。

        Agent 使用建议：
        - 先通过上传接口获得 `staged_file_id`
        - 再调用本 Tool 完成真正的知识库导入
        - 成功后对应暂存文件会被标记为已消费
        """

        payload = {
            "category_id": category_id,
            "title": title,
            "staged_file_id": staged_file_id,
            "request_id": request_id,
            "operator": operator,
            "trace_id": trace_id,
        }
        return _execute_write(payload, action="import_from_staged")

    @mcp.tool(
        name="kb_document_delete",
        description="按主键或 document_uid 删除文档，并级联清理切片、向量和源文件。",
    )
    def kb_document_delete(
        id: int | None = None,
        document_uid: str | None = None,
        request_id: str | None = None,
        operator: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """删除文档，并级联清理切片、向量和原始文件。

        Agent 使用建议：
        - 删除是高成本操作，会同步处理 PostgreSQL、Milvus 和文件存储
        - 适合在确定不再需要该文档时调用
        """

        payload = {
            "id": id,
            "document_uid": document_uid,
            "request_id": request_id,
            "operator": operator,
            "trace_id": trace_id,
        }
        return _execute_write(payload, action="delete")

    @mcp.tool(
        name="kb_document_update_from_staged",
        description="标准远端路径：使用 staged_file 整篇替换文档并重建切片与向量。",
    )
    def kb_document_update_from_staged(
        id: int | None = None,
        document_uid: str | None = None,
        category_id: int | None = None,
        title: str | None = None,
        staged_file_id: int | None = None,
        request_id: str | None = None,
        operator: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """通过暂存文件替换源文档内容。

        Agent 使用建议：
        - 这是远端更新大文件的推荐方式
        - 更新采用整篇重建，不做局部 patch
        """

        payload = {
            "id": id,
            "document_uid": document_uid,
            "category_id": category_id,
            "title": title,
            "staged_file_id": staged_file_id,
            "request_id": request_id,
            "operator": operator,
            "trace_id": trace_id,
        }
        return _execute_write(payload, action="update_from_staged")


def _execute_read(*, payload: dict[str, Any], action: str) -> dict[str, Any]:
    """执行读取类文档 Tool，并统一处理异常响应。

    读取类 Tool 不会产生副作用，适合 Agent 在编排前探测当前文档状态。
    """

    session = SessionFactory()
    service = DocumentService(
        category_repository=CategoryRepository(session),
        document_repository=DocumentRepository(session),
        chunk_repository=ChunkRepository(session),
        staged_file_repository=StagedFileRepository(session),
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
        if action == "content_get":
            content = service.get_document_content(payload)
            return build_success_response(
                data=content.model_dump(mode="json"),
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
    """执行文档写入类 Tool，并统一处理异常响应。

    写入类 Tool 会在成功提交数据库后，再执行必要的文件清理动作。
    Agent 可以把统一响应中的 `success/code/data` 当作稳定协议使用。
    """

    session = SessionFactory()
    service = DocumentService(
        category_repository=CategoryRepository(session),
        document_repository=DocumentRepository(session),
        chunk_repository=ChunkRepository(session),
        staged_file_repository=StagedFileRepository(session),
    )
    try:
        if action == "import_from_staged":
            result = service.import_document_from_staged(payload)
        elif action == "update_from_staged":
            result = service.update_document_from_staged(payload)
        elif action == "delete":
            result = service.delete_document(payload)
        else:
            raise RuntimeError(f"unsupported action: {action}")
        session.commit()
        service.clear_import_context()
        service.finalize_post_commit_cleanup()
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
    if action in {"update", "update_from_staged"}:
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
    if action == "import_from_staged":
        return service.rollback_import_side_effects(original_error=error)
    if action == "delete":
        return service.rollback_delete_side_effects(original_error=error)
    if action == "update":
        return service.rollback_update_side_effects(original_error=error)
    if action == "update_from_staged":
        return service.rollback_update_side_effects(original_error=error)
    return None
