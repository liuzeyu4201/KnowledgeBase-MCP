from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from knowledgebase.db.session import session_scope
from knowledgebase.domain.exceptions import AppError
from knowledgebase.repositories.staged_file_repository import StagedFileRepository
from knowledgebase.schemas.common import build_error_response, build_success_response
from knowledgebase.services.staged_file_service import StagedFileService


def register_staged_file_tools(mcp: Any) -> None:
    """注册暂存文件相关 MCP Tool。

    暂存文件是“已上传但尚未导入”的受控资源。
    Agent 可以通过这些 Tool 管理 staged_file 生命周期，但真正的知识库导入应走 `*_from_staged` 文档 Tool。
    """

    @mcp.tool(
        name="kb_staged_file_get",
        description="按主键或 staged_file_uid 查询暂存文件详情，适合确认上传结果和消费状态。",
    )
    async def kb_staged_file_get(
        id: int | None = None,
        staged_file_uid: str | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """读取单个暂存文件详情。

        Agent 使用建议：
        - 成功上传后可用本 Tool 校验状态是否为 `uploaded`
        - 被导入成功后状态通常会变为 `consumed`
        """
        payload = {
            "id": id,
            "staged_file_uid": staged_file_uid,
            "request_id": request_id,
            "trace_id": trace_id,
        }
        return await run_in_threadpool(_execute_read, payload=payload, action="get")

    @mcp.tool(
        name="kb_staged_file_list",
        description="分页查询暂存文件列表，适合遍历未消费、失败或待清理的上传文件。",
    )
    async def kb_staged_file_list(
        status: str | None = None,
        mime_type: str | None = None,
        linked_document_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """分页查询暂存文件列表。

        Agent 使用建议：
        - 可按 `status` 找到未消费文件
        - 可按 `linked_document_id` 追踪某份文档关联的暂存来源
        """
        payload = {
            "status": status,
            "mime_type": mime_type,
            "linked_document_id": linked_document_id,
            "page": page,
            "page_size": page_size,
            "request_id": request_id,
            "trace_id": trace_id,
        }
        return await run_in_threadpool(_execute_read, payload=payload, action="list")

    @mcp.tool(
        name="kb_staged_file_delete",
        description="删除未消费或已过期的暂存文件。已消费文件默认不允许删除。",
    )
    async def kb_staged_file_delete(
        id: int | None = None,
        staged_file_uid: str | None = None,
        request_id: str | None = None,
        operator: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """删除暂存文件。

        Agent 使用建议：
        - 只应删除明确不再使用的暂存文件
        - 若文件已经被导入消费，通常会返回业务错误而不是强制删除
        """
        payload = {
            "id": id,
            "staged_file_uid": staged_file_uid,
            "request_id": request_id,
            "operator": operator,
            "trace_id": trace_id,
        }
        return await run_in_threadpool(_execute_write, payload=payload)


def _execute_read(*, payload: dict[str, Any], action: str) -> dict[str, Any]:
    """执行读取类暂存文件 Tool。

    这些 Tool 只读，不会改变 staged_file 生命周期。
    """

    try:
        with session_scope() as session:
            service = StagedFileService(StagedFileRepository(session))
            if action == "get":
                staged_file = service.get_staged_file(payload)
                return build_success_response(
                    data={"staged_file": staged_file.model_dump(mode="json")},
                    request_id=payload.get("request_id"),
                    trace_id=payload.get("trace_id"),
                )
            if action == "list":
                items, pagination = service.list_staged_files(payload)
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


def _execute_write(*, payload: dict[str, Any]) -> dict[str, Any]:
    """执行写入类暂存文件 Tool。

    当前写入类能力只有删除，属于资源治理接口，不负责上传本体。
    """

    try:
        with session_scope() as session:
            service = StagedFileService(StagedFileRepository(session))
            staged_file = service.delete_staged_file(payload)
            return build_success_response(
                data={"staged_file": staged_file.model_dump(mode="json")},
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
