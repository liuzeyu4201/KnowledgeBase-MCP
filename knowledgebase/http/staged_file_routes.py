from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from knowledgebase.db.session import session_scope
from knowledgebase.domain.exceptions import AppError
from knowledgebase.repositories.staged_file_repository import StagedFileRepository
from knowledgebase.schemas.common import build_error_response, build_success_response
from knowledgebase.services.staged_file_service import StagedFileService

router = APIRouter(prefix="/api/staged-files", tags=["staged-files"])


@router.post("")
async def upload_staged_file(
    file: UploadFile = File(...),
    request_id: str | None = Form(default=None),
    operator: str | None = Form(default=None),
    trace_id: str | None = Form(default=None),
) -> JSONResponse:
    """接收 multipart 文件上传并创建暂存文件记录。

    这是远端大文件标准入口：
    1. 客户端先把文件传到这里
    2. 服务端流式落盘并创建 `staged_file`
    3. Agent 再用 `staged_file_id` 调用 `*_from_staged` 的 MCP Tool
    """

    payload = {
        "request_id": request_id,
        "operator": operator,
        "trace_id": trace_id,
    }

    try:
        with session_scope() as session:
            service = StagedFileService(StagedFileRepository(session))
            staged_file = service.create_from_stream(
                file_name=file.filename or "uploaded-file",
                file_stream=file.file,
                mime_type=file.content_type,
            )
            return JSONResponse(
                content=build_success_response(
                    data={"staged_file": staged_file.model_dump(mode="json")},
                    request_id=request_id,
                    trace_id=trace_id,
                )
            )
    except AppError as exc:
        return JSONResponse(
            status_code=400 if exc.error_type != "system_error" else 500,
            content=build_error_response(
                code=exc.code,
                message=exc.message,
                error_type=exc.error_type,
                details=exc.details,
                request_id=request_id,
                trace_id=trace_id,
            ),
        )
    except (ValidationError, SQLAlchemyError) as exc:
        return JSONResponse(
            status_code=500 if isinstance(exc, SQLAlchemyError) else 400,
            content=build_error_response(
                code="DB_ERROR" if isinstance(exc, SQLAlchemyError) else "INVALID_ARGUMENT",
                message="database operation failed" if isinstance(exc, SQLAlchemyError) else "invalid request",
                error_type="system_error" if isinstance(exc, SQLAlchemyError) else "validation_error",
                details={"error": str(exc)},
                request_id=request_id,
                trace_id=trace_id,
            ),
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=build_error_response(
                code="INTERNAL_ERROR",
                message="internal server error",
                error_type="system_error",
                details={"error": str(exc)},
                request_id=request_id,
                trace_id=trace_id,
            ),
        )
    finally:
        await file.close()


@router.get("/{staged_file_id}")
def get_staged_file(
    staged_file_id: int,
    request_id: str | None = None,
    trace_id: str | None = None,
) -> JSONResponse:
    """查询单个暂存文件。

    适合在上传完成后确认文件元数据、当前状态和是否已被消费。
    """

    payload = {
        "id": staged_file_id,
        "request_id": request_id,
        "trace_id": trace_id,
    }
    return _handle_read(payload=payload, action="get")


@router.get("")
def list_staged_files(
    status: str | None = None,
    mime_type: str | None = None,
    linked_document_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
    request_id: str | None = None,
    trace_id: str | None = None,
) -> JSONResponse:
    """分页查询暂存文件列表。

    适合用于后台治理、未消费文件排查和 Agent 的资源枚举。
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
    return _handle_read(payload=payload, action="list")


@router.delete("/{staged_file_id}")
def delete_staged_file(
    staged_file_id: int,
    request_id: str | None = None,
    operator: str | None = None,
    trace_id: str | None = None,
) -> JSONResponse:
    """删除未消费或已过期的暂存文件。

    这是治理接口，不会删除已经成为正式文档主文件的业务数据。
    """

    payload = {
        "id": staged_file_id,
        "request_id": request_id,
        "operator": operator,
        "trace_id": trace_id,
    }
    try:
        with session_scope() as session:
            service = StagedFileService(StagedFileRepository(session))
            staged_file = service.delete_staged_file(payload)
            return JSONResponse(
                content=build_success_response(
                    data={"staged_file": staged_file.model_dump(mode="json")},
                    request_id=request_id,
                    trace_id=trace_id,
                )
            )
    except AppError as exc:
        return JSONResponse(
            status_code=400 if exc.error_type != "system_error" else 500,
            content=build_error_response(
                code=exc.code,
                message=exc.message,
                error_type=exc.error_type,
                details=exc.details,
                request_id=request_id,
                trace_id=trace_id,
            ),
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=500,
            content=build_error_response(
                code="INTERNAL_ERROR",
                message="internal server error",
                error_type="system_error",
                details={"error": str(exc)},
                request_id=request_id,
                trace_id=trace_id,
            ),
        )


def _handle_read(*, payload: dict[str, Any], action: str) -> JSONResponse:
    """统一处理暂存文件读取类 HTTP 请求。"""

    try:
        with session_scope() as session:
            service = StagedFileService(StagedFileRepository(session))
            if action == "get":
                staged_file = service.get_staged_file(payload)
                content = build_success_response(
                    data={"staged_file": staged_file.model_dump(mode="json")},
                    request_id=payload.get("request_id"),
                    trace_id=payload.get("trace_id"),
                )
            elif action == "list":
                items, pagination = service.list_staged_files(payload)
                content = build_success_response(
                    data={
                        "items": [item.model_dump(mode="json") for item in items],
                        "pagination": pagination,
                    },
                    request_id=payload.get("request_id"),
                    trace_id=payload.get("trace_id"),
                )
            else:
                raise RuntimeError(f"unsupported action: {action}")
            return JSONResponse(content=content)
    except AppError as exc:
        return JSONResponse(
            status_code=400 if exc.error_type != "system_error" else 500,
            content=build_error_response(
                code=exc.code,
                message=exc.message,
                error_type=exc.error_type,
                details=exc.details,
                request_id=payload.get("request_id"),
                trace_id=payload.get("trace_id"),
            ),
        )
    except (ValidationError, SQLAlchemyError) as exc:
        return JSONResponse(
            status_code=500 if isinstance(exc, SQLAlchemyError) else 400,
            content=build_error_response(
                code="DB_ERROR" if isinstance(exc, SQLAlchemyError) else "INVALID_ARGUMENT",
                message="database operation failed" if isinstance(exc, SQLAlchemyError) else "invalid request",
                error_type="system_error" if isinstance(exc, SQLAlchemyError) else "validation_error",
                details={"error": str(exc)},
                request_id=payload.get("request_id"),
                trace_id=payload.get("trace_id"),
            ),
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=build_error_response(
                code="INTERNAL_ERROR",
                message="internal server error",
                error_type="system_error",
                details={"error": str(exc)},
                request_id=payload.get("request_id"),
                trace_id=payload.get("trace_id"),
            ),
        )
