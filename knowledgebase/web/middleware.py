from __future__ import annotations

import logging
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


logger = logging.getLogger("knowledgebase.web")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """为网页模块注入请求追踪字段并记录访问日志。"""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        trace_id = request.headers.get("X-Trace-ID") or request_id
        request.state.request_id = request_id
        request.state.trace_id = trace_id

        started_at = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Trace-ID"] = trace_id
        logger.info(
            "web access method=%s path=%s status=%s duration_ms=%s request_id=%s trace_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
            trace_id,
        )
        return response

