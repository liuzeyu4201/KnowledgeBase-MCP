from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    """生成统一的 UTC 时间字符串。"""

    return datetime.now(tz=timezone.utc).isoformat()


def _make_json_safe(value: Any) -> Any:
    """把错误详情递归转换为可 JSON 序列化的结构。"""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, BaseException):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_make_json_safe(item) for item in value]
    return str(value)


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
            "details": _make_json_safe(details or {}),
        },
    }
