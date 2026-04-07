from __future__ import annotations

from contextlib import AsyncExitStack
import json
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


def parse_tool_result(result: Any) -> dict[str, Any]:
    """把 MCP Tool 返回的文本内容解析为统一的 JSON 字典。"""

    parts: list[str] = []
    for item in result.content:
        text = getattr(item, "text", None)
        if text:
            parts.append(text)

    if not parts:
        raise RuntimeError(f"unexpected tool result content: {result!r}")

    raw_text = "".join(parts)
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        if getattr(result, "isError", False):
            return {
                "success": False,
                "code": "MCP_TOOL_EXECUTION_ERROR",
                "message": raw_text,
                "error": {
                    "type": "tool_execution_error",
                    "details": {},
                },
            }
        raise


class MCPToolClient:
    """封装 MCP HTTP 客户端，供测试用例复用。"""

    def __init__(self, server_url: str) -> None:
        self.server_url = server_url
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    async def __aenter__(self) -> "MCPToolClient":
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

    async def list_tools(self) -> list[str]:
        """返回当前 MCP Server 暴露的 Tool 名称列表。"""

        if self._session is None:
            raise RuntimeError("MCP session is not initialized")
        result = await self._session.list_tools()
        return [tool.name for tool in result.tools]

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """调用 MCP Tool 并解析为统一 JSON 响应。"""

        if self._session is None:
            raise RuntimeError("MCP session is not initialized")
        result = await self._session.call_tool(tool_name, arguments)
        return parse_tool_result(result)
