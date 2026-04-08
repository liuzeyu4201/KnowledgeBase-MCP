from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from knowledgebase.db.session import session_scope
from knowledgebase.domain.exceptions import AppError
from knowledgebase.repositories.import_task_repository import ImportTaskRepository
from knowledgebase.schemas.common import build_error_response, build_success_response
from knowledgebase.services.import_task_service import ImportTaskService


def register_import_task_tools(mcp: Any) -> None:
    """注册批量文档导入任务相关 MCP Tool。"""

    @mcp.tool(name="kb_document_import_batch_submit", description="提交批量文档导入异步任务")
    def kb_document_import_batch_submit(
        items: list[dict[str, Any]],
        priority: int = 50,
        max_attempts: int = 3,
        idempotency_key: str | None = None,
        request_id: str | None = None,
        operator: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """提交批量文档导入任务，并返回任务状态。"""

        payload = {
            "items": items,
            "priority": priority,
            "max_attempts": max_attempts,
            "idempotency_key": idempotency_key,
            "request_id": request_id,
            "operator": operator,
            "trace_id": trace_id,
        }
        return _execute_write(payload=payload, action="submit")

    @mcp.tool(name="kb_document_import_batch_cancel", description="取消批量文档导入异步任务")
    def kb_document_import_batch_cancel(
        id: int | None = None,
        task_uid: str | None = None,
        request_id: str | None = None,
        operator: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """取消尚未完成的批量导入任务。"""

        payload = {
            "id": id,
            "task_uid": task_uid,
            "request_id": request_id,
            "operator": operator,
            "trace_id": trace_id,
        }
        return _execute_write(payload=payload, action="cancel")

    @mcp.tool(name="kb_document_import_batch_get", description="查询批量文档导入异步任务状态")
    def kb_document_import_batch_get(
        id: int | None = None,
        task_uid: str | None = None,
        include_items: bool = True,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """读取任务状态及可选的子项明细。"""

        payload = {
            "id": id,
            "task_uid": task_uid,
            "include_items": include_items,
            "request_id": request_id,
            "trace_id": trace_id,
        }
        return _execute_read(payload=payload)


def _execute_write(*, payload: dict[str, Any], action: str) -> dict[str, Any]:
    """执行批量导入任务写入类 Tool，并统一处理异常。"""

    try:
        with session_scope() as session:
            service = ImportTaskService(ImportTaskRepository(session))
            if action == "submit":
                task = service.submit_task(payload)
            elif action == "cancel":
                task = service.cancel_task(payload)
            else:
                raise RuntimeError(f"unsupported action: {action}")
        if action == "cancel":
            service.finalize_cancel_cleanup()
        return build_success_response(
                data={"task": task.model_dump(mode="json")},
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


def _execute_read(*, payload: dict[str, Any]) -> dict[str, Any]:
    """执行批量导入任务读取类 Tool，并统一处理异常。"""

    try:
        with session_scope() as session:
            service = ImportTaskService(ImportTaskRepository(session))
            task = service.get_task(payload)
            return build_success_response(
                data={"task": task.model_dump(mode="json")},
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
