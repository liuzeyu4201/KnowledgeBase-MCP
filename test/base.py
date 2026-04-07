from __future__ import annotations

import asyncio
import base64
import os
import time
import unittest
from pathlib import Path
from typing import Any

from test.mcp_test_client import MCPToolClient


class MCPIntegrationTestCase(unittest.TestCase):
    """提供统一 MCP 测试入口、样例文件读取和测试辅助能力。"""

    server_url = os.getenv("KNOWLEDGEBASE_TEST_SERVER_URL", "http://127.0.0.1:8000/mcp")
    small_pdf_path = Path(
        os.getenv("KNOWLEDGEBASE_TEST_SMALL_PDF", "/app/data/Functional_Analysis.pdf")
    )
    large_pdf_path = Path(
        os.getenv("KNOWLEDGEBASE_TEST_LARGE_PDF", "/app/data/Functional Analysis Notes.pdf")
    )

    def run_async(self, coroutine):
        """在同步 unittest 用例中执行异步逻辑。"""

        return asyncio.run(coroutine)

    def unique_suffix(self) -> str:
        """生成唯一后缀，避免测试数据在共享环境中发生冲突。"""

        return f"{int(time.time() * 1000)}_{id(self)}"

    def read_pdf_base64(self, *, large: bool = False) -> str:
        """读取测试 PDF 并编码为 base64，直接用于文档导入接口。"""

        pdf_path = self.large_pdf_path if large else self.small_pdf_path
        return base64.b64encode(pdf_path.read_bytes()).decode("utf-8")

    async def tool(self, tool_name: str, **arguments: Any) -> dict[str, Any]:
        """统一调用 MCP Tool。"""

        async with MCPToolClient(self.server_url) as client:
            return await client.call_tool(tool_name, arguments)

    def assert_success(self, payload: dict[str, Any], *, code: str = "OK") -> None:
        """断言接口成功返回。"""

        self.assertTrue(payload.get("success"), payload)
        self.assertEqual(payload.get("code"), code, payload)

    def assert_error(
        self,
        payload: dict[str, Any],
        *,
        code: str | None = None,
        error_type: str | None = None,
    ) -> None:
        """断言接口失败返回，并可校验错误码与错误类型。"""

        self.assertFalse(payload.get("success"), payload)
        if code is not None:
            self.assertEqual(payload.get("code"), code, payload)
        if error_type is not None:
            self.assertEqual(payload.get("error", {}).get("type"), error_type, payload)

    async def create_category(self, *, prefix: str = "test_category") -> dict[str, Any]:
        """创建分类并登记清理信息。"""

        suffix = self.unique_suffix()
        payload = await self.tool(
            "kb_category_create",
            category_code=f"{prefix}_{suffix}",
            name=f"{prefix}_{suffix}",
            description="测试分类",
        )
        self.assert_success(payload)
        return payload["data"]["category"]

    async def import_document(
        self,
        *,
        category_id: int,
        title_prefix: str = "test_document",
        large: bool = False,
    ) -> dict[str, Any]:
        """导入测试文档并登记清理信息。"""

        suffix = self.unique_suffix()
        file_name = "Functional Analysis Notes.pdf" if large else "Functional_Analysis.pdf"
        payload = await self.tool(
            "kb_document_import",
            category_id=category_id,
            title=f"{title_prefix}_{suffix}",
            file_name=file_name,
            mime_type="application/pdf",
            file_content_base64=self.read_pdf_base64(large=large),
        )
        self.assert_success(payload)
        return payload["data"]["document"]

    async def delete_document_best_effort(self, document: dict[str, Any]) -> None:
        """尽最大努力删除测试文档，避免污染共享测试环境。"""

        await self.tool("kb_document_delete", id=document["id"])

    async def delete_category_best_effort(self, category: dict[str, Any]) -> None:
        """尽最大努力删除测试分类。"""

        await self.tool("kb_category_delete", id=category["id"])
