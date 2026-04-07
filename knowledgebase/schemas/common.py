from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    """生成统一的 UTC 时间字符串。"""

    return datetime.now(tz=timezone.utc).isoformat()


def build_success_response(
    *,
    data: dict[str, Any] | None = None,
    code: str = "OK",
    message: str = "success",
    request_id: str | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """构造统一成功响应。"""

    return {
        "success": True,
        "code": code,
        "message": message,
        "request_id": request_id,
        "trace_id": trace_id,
        "timestamp": utc_now_iso(),
        "data": data or {},
    }


def build_error_response(
    *,
    code: str,
    message: str,
    error_type: str,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """构造统一错误响应。"""

    return {
        "success": False,
        "code": code,
        "message": message,
        "request_id": request_id,
        "trace_id": trace_id,
        "timestamp": utc_now_iso(),
        "error": {
            "type": error_type,
            "details": details or {},
        },
    }
