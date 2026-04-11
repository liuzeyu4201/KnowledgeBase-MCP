from __future__ import annotations

from contextlib import AsyncExitStack
import json
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from knowledgebase.app.config import get_settings
from knowledgebase.domain.exceptions import AppError


class MCPGateway:
    """网页模块访问 MCP Server 的统一网关。

    网页后端不能绕过 MCP 直接拼装一套平行数据通路，因此所有分类、文档、
    批量任务查询都通过这里转成真实 MCP Tool 调用。
    """

    def __init__(self, server_url: str | None = None) -> None:
        settings = get_settings()
        self.server_url = server_url or f"http://127.0.0.1:{settings.mcp_port}{settings.mcp_path}"
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    async def __aenter__(self) -> "MCPGateway":
        self._stack = AsyncExitStack()
        read_stream, write_stream, _ = await self._stack.enter_async_context(
            streamablehttp_client(self.server_url)
        )
        self._session = await self._stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await self._session.initialize()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self._session = None
        if self._stack is not None:
            await self._stack.aclose()
            self._stack = None

    async def list_categories(self, payload: dict[str, Any]) -> dict[str, Any]:
        """调用分类列表 Tool。"""

        return await self.call_tool("kb_category_list", payload)

    async def get_category(self, payload: dict[str, Any]) -> dict[str, Any]:
        """调用分类详情 Tool。"""

        return await self.call_tool("kb_category_get", payload)

    async def delete_category(self, payload: dict[str, Any]) -> dict[str, Any]:
        """调用分类删除 Tool。"""

        return await self.call_tool("kb_category_delete", payload)

    async def list_documents(self, payload: dict[str, Any]) -> dict[str, Any]:
        """调用文档列表 Tool。"""

        return await self.call_tool("kb_document_list", payload)

    async def get_document_content(self, payload: dict[str, Any]) -> dict[str, Any]:
        """调用文档原文与 chunk 内容读取 Tool。"""

        return await self.call_tool("kb_document_content_get", payload)

    async def delete_document(self, payload: dict[str, Any]) -> dict[str, Any]:
        """调用文档删除 Tool。"""

        return await self.call_tool("kb_document_delete", payload)

    async def get_import_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        """调用批量导入任务详情 Tool。"""

        return await self.call_tool("kb_document_import_batch_get", payload)

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """统一执行 MCP Tool 并把文本结果解析成 JSON。"""

        if self._session is None:
            raise RuntimeError("MCP gateway is not initialized")

        result = await self._session.call_tool(tool_name, arguments)
        payload = self._parse_tool_result(result)
        if not payload.get("success", False):
            raise AppError(
                code=payload.get("code", "MCP_TOOL_ERROR"),
                message=payload.get("message", "mcp tool call failed"),
                error_type=payload.get("error", {}).get("type", "system_error"),
                details=payload.get("error", {}).get("details", {}),
            )
        return payload

    def _parse_tool_result(self, result: Any) -> dict[str, Any]:
        """把 MCP Tool 返回的文本内容解析成统一字典。"""

        parts: list[str] = []
        for item in result.content:
            text = getattr(item, "text", None)
            if text:
                parts.append(text)

        if not parts:
            raise AppError(
                code="MCP_EMPTY_RESULT",
                message="mcp tool returned empty content",
                error_type="system_error",
            )

        raw_text = "".join(parts)
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise AppError(
                code="MCP_INVALID_RESULT",
                message="mcp tool returned invalid json",
                error_type="system_error",
                details={"raw_text": raw_text},
            ) from exc
