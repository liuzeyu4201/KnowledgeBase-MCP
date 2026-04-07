from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from knowledgebase.db.session import session_scope
from knowledgebase.domain.exceptions import AppError
from knowledgebase.repositories.category_repository import CategoryRepository
from knowledgebase.schemas.common import build_error_response, build_success_response
from knowledgebase.services.category_service import CategoryService


def register_category_tools(mcp: Any) -> None:
    """注册分类相关 MCP Tool。"""

    @mcp.tool(name="kb_category_create", description="新增知识分类")
    def kb_category_create(
        category_code: str,
        name: str,
        description: str | None = None,
        status: int = 1,
        request_id: str | None = None,
        operator: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """创建分类并返回分类详情。"""

        payload = {
            "category_code": category_code,
            "name": name,
            "description": description,
            "status": status,
            "request_id": request_id,
            "operator": operator,
            "trace_id": trace_id,
        }
        return _execute_write(payload=payload, action="create")

    @mcp.tool(name="kb_category_get", description="按主键或分类编码查询分类详情")
    def kb_category_get(
        id: int | None = None,
        category_code: str | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """读取单个分类详情。"""

        payload = {
            "id": id,
            "category_code": category_code,
            "request_id": request_id,
            "trace_id": trace_id,
        }
        return _execute_read(payload=payload, action="get")

    @mcp.tool(name="kb_category_update", description="更新知识分类")
    def kb_category_update(
        id: int | None = None,
        category_code: str | None = None,
        new_category_code: str | None = None,
        name: str | None = None,
        description: str | None = None,
        status: int | None = None,
        request_id: str | None = None,
        operator: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """更新分类并返回最新分类详情。"""

        payload = {
            "id": id,
            "category_code": category_code,
            "new_category_code": new_category_code,
            "name": name,
            "description": description,
            "status": status,
            "request_id": request_id,
            "operator": operator,
            "trace_id": trace_id,
        }
        return _execute_write(payload=payload, action="update")

    @mcp.tool(name="kb_category_delete", description="删除知识分类")
    def kb_category_delete(
        id: int | None = None,
        category_code: str | None = None,
        request_id: str | None = None,
        operator: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """删除分类，当前采用软删除。"""

        payload = {
            "id": id,
            "category_code": category_code,
            "request_id": request_id,
            "operator": operator,
            "trace_id": trace_id,
        }
        return _execute_write(payload=payload, action="delete")

    @mcp.tool(name="kb_category_list", description="分页查询分类列表")
    def kb_category_list(
        category_code: str | None = None,
        name: str | None = None,
        status: int | None = None,
        page: int = 1,
        page_size: int = 20,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """按过滤条件分页查询分类列表。"""

        payload = {
            "category_code": category_code,
            "name": name,
            "status": status,
            "page": page,
            "page_size": page_size,
            "request_id": request_id,
            "trace_id": trace_id,
        }
        return _execute_read(payload=payload, action="list")


def _execute_write(*, payload: dict[str, Any], action: str) -> dict[str, Any]:
    """执行写入类 Tool，并统一处理异常响应。"""

    try:
        with session_scope() as session:
            service = CategoryService(CategoryRepository(session))
            if action == "create":
                # 写入类操作统一走服务层，确保唯一性与业务规则集中处理。
                category = service.create_category(payload)
                return build_success_response(
                    data={"category": category.model_dump(mode="json")},
                    request_id=payload.get("request_id"),
                    trace_id=payload.get("trace_id"),
                )
            if action == "update":
                category = service.update_category(payload)
                return build_success_response(
                    data={"category": category.model_dump(mode="json")},
                    request_id=payload.get("request_id"),
                    trace_id=payload.get("trace_id"),
                )
            if action == "delete":
                deleted = service.delete_category(payload)
                return build_success_response(
                    data=deleted,
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


def _execute_read(*, payload: dict[str, Any], action: str) -> dict[str, Any]:
    """执行读取类 Tool，并统一处理异常响应。"""

    try:
        with session_scope() as session:
            service = CategoryService(CategoryRepository(session))
            if action == "get":
                category = service.get_category(payload)
                return build_success_response(
                    data={"category": category.model_dump(mode="json")},
                    request_id=payload.get("request_id"),
                    trace_id=payload.get("trace_id"),
                )
            if action == "list":
                items, pagination = service.list_categories(payload)
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
