from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from knowledgebase.db.session import session_scope
from knowledgebase.domain.exceptions import AppError
from knowledgebase.repositories.category_repository import CategoryRepository
from knowledgebase.repositories.document_repository import DocumentRepository
from knowledgebase.repositories.import_task_repository import ImportTaskRepository
from knowledgebase.repositories.staged_file_repository import StagedFileRepository
from knowledgebase.schemas.common import build_error_response, build_success_response
from knowledgebase.services.import_task_service import ImportTaskService


def register_import_task_tools(mcp: Any) -> None:
    """注册文档异步任务相关 MCP Tool。

    这些 Tool 面向需要异步导入、异步更新和后台任务编排的 Agent。
    历史上的 `import_batch_*` 命名继续保留，新的通用文档任务入口同步提供。
    """

    @mcp.tool(
        name="kb_document_import_batch_submit_from_staged",
        description="标准远端路径：基于 staged_file 引用提交批量文档导入异步任务。",
    )
    async def kb_document_import_batch_submit_from_staged(
        items: list[dict[str, Any]],
        priority: int = 50,
        max_attempts: int = 3,
        idempotency_key: str | None = None,
        request_id: str | None = None,
        operator: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """提交基于暂存文件的批量导入任务。

        Agent 使用建议：
        - `items` 中每一项至少应包含 `category_id`、`title`、`staged_file_id`
        - 任务提交成功仅表示已入队，不表示文档已导入完成
        """

        payload = {
            "items": items,
            "priority": priority,
            "max_attempts": max_attempts,
            "idempotency_key": idempotency_key,
            "request_id": request_id,
            "operator": operator,
            "trace_id": trace_id,
        }
        return await run_in_threadpool(_execute_write, payload=payload, action="submit_from_staged")

    @mcp.tool(
        name="kb_document_import_batch_cancel",
        description="取消批量文档导入异步任务。支持 queued 直接取消，也支持 running 协作式取消。",
    )
    async def kb_document_import_batch_cancel(
        id: int | None = None,
        task_uid: str | None = None,
        request_id: str | None = None,
        operator: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """取消尚未完成的批量导入任务。

        Agent 使用建议：
        - `id` 和 `task_uid` 二选一
        - 任务若已完成，返回的是最终状态，不会强行改写历史结果
        """

        payload = {
            "id": id,
            "task_uid": task_uid,
            "request_id": request_id,
            "operator": operator,
            "trace_id": trace_id,
        }
        return await run_in_threadpool(_execute_write, payload=payload, action="cancel")

    @mcp.tool(
        name="kb_document_task_cancel",
        description="取消文档异步任务。兼容单文档导入、单文档更新和批量导入任务。",
    )
    async def kb_document_task_cancel(
        id: int | None = None,
        task_uid: str | None = None,
        request_id: str | None = None,
        operator: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "id": id,
            "task_uid": task_uid,
            "request_id": request_id,
            "operator": operator,
            "trace_id": trace_id,
        }
        return await run_in_threadpool(_execute_write, payload=payload, action="cancel")

    @mcp.tool(
        name="kb_document_import_batch_get",
        description="查询批量文档导入异步任务状态。可选择是否返回子项明细。",
    )
    async def kb_document_import_batch_get(
        id: int | None = None,
        task_uid: str | None = None,
        include_items: bool = True,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """读取任务状态及可选的子项明细。

        Agent 使用建议：
        - 轮询任务时可把 `include_items` 设为 `false`，降低返回体积
        - 诊断失败或做精细展示时再打开 `include_items`
        """

        payload = {
            "id": id,
            "task_uid": task_uid,
            "include_items": include_items,
            "request_id": request_id,
            "trace_id": trace_id,
        }
        return await run_in_threadpool(_execute_read, payload=payload)

    @mcp.tool(
        name="kb_document_task_get",
        description="查询文档异步任务状态。兼容单文档导入、单文档更新和批量导入任务。",
    )
    async def kb_document_task_get(
        id: int | None = None,
        task_uid: str | None = None,
        include_items: bool = True,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "id": id,
            "task_uid": task_uid,
            "include_items": include_items,
            "request_id": request_id,
            "trace_id": trace_id,
        }
        return await run_in_threadpool(_execute_read, payload=payload)


def _execute_write(*, payload: dict[str, Any], action: str) -> dict[str, Any]:
    """执行批量导入任务写入类 Tool，并统一处理异常。

    Agent 可假设：
    - `submit_from_staged` 成功表示任务已安全写入 PostgreSQL 真相源
    - `cancel` 成功表示系统已接收取消意图，并会尽力收敛到最终状态
    """

    try:
        with session_scope() as session:
            service = ImportTaskService(
                ImportTaskRepository(session),
                category_repository=CategoryRepository(session),
                staged_file_repository=StagedFileRepository(session),
                document_repository=DocumentRepository(session),
            )
            if action == "submit_from_staged":
                task = service.submit_task_from_staged(payload)
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
    """执行批量导入任务读取类 Tool，并统一处理异常。

    查询返回的是任务当前可见状态，不保证一定是终态。
    Agent 应以 `success/partial_success/failed/canceled` 作为终态判断。
    """

    try:
        with session_scope() as session:
            service = ImportTaskService(
                ImportTaskRepository(session),
                category_repository=CategoryRepository(session),
                staged_file_repository=StagedFileRepository(session),
                document_repository=DocumentRepository(session),
            )
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
