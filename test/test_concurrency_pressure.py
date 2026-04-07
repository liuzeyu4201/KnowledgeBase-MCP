from __future__ import annotations

import asyncio

from test.base import MCPIntegrationTestCase
from test.mcp_test_client import MCPToolClient


class ConcurrencyAndPressureTestCase(MCPIntegrationTestCase):
    """覆盖高并发、重复提交和连续压力场景。"""

    def test_concurrent_duplicate_category_create_should_only_return_business_conflict(self) -> None:
        async def scenario() -> None:
            suffix = self.unique_suffix()
            category_code = f"concurrent_dup_{suffix}"
            name = f"concurrent_dup_{suffix}"

            async def create_once() -> dict:
                async with MCPToolClient(self.server_url) as client:
                    return await client.call_tool(
                        "kb_category_create",
                        {
                            "category_code": category_code,
                            "name": name,
                            "description": "并发重复创建测试",
                        },
                    )

            results = await asyncio.gather(*(create_once() for _ in range(8)))
            success_results = [item for item in results if item.get("success")]
            failed_results = [item for item in results if not item.get("success")]

            self.assertEqual(len(success_results), 1, results)
            created_category = success_results[0]["data"]["category"]
            try:
                self.assertTrue(failed_results, results)
                for payload in failed_results:
                    self.assertEqual(payload.get("code"), "CATEGORY_CODE_CONFLICT", results)
            finally:
                await self.delete_category_best_effort(created_category)

        self.run_async(scenario())

    def test_high_concurrency_search_requests_all_succeed(self) -> None:
        async def scenario() -> None:
            category = await self.create_category(prefix="search_concurrency")
            document = await self.import_document(
                category_id=category["id"],
                title_prefix="search_concurrency",
                large=True,
            )

            async def search_once(index: int) -> dict:
                async with MCPToolClient(self.server_url) as client:
                    return await client.call_tool(
                        "kb_search_retrieve",
                        {
                            "query": "Open Mapping Theorem" if index % 2 == 0 else "Hilbert space",
                            "alpha": 1.0,
                            "limit": 5,
                            "document_id": document["id"],
                        },
                    )

            try:
                results = await asyncio.gather(*(search_once(index) for index in range(20)))
                for payload in results:
                    self.assert_success(payload)
                    self.assertGreater(payload["data"]["total"], 0, payload)
            finally:
                await self.delete_document_best_effort(document)
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_sequential_search_pressure_burst(self) -> None:
        async def scenario() -> None:
            category = await self.create_category(prefix="search_pressure")
            document = await self.import_document(
                category_id=category["id"],
                title_prefix="search_pressure",
                large=True,
            )

            queries = [
                ("Open Mapping Theorem", 1.0),
                ("Hilbert space", 1.0),
                ("linear space definition", 1.0),
                ("where linear algebra meets analysis", 0.5),
                ("什么是希尔伯特空间", 0.5),
            ]

            try:
                for index in range(25):
                    query, alpha = queries[index % len(queries)]
                    payload = await self.tool(
                        "kb_search_retrieve",
                        query=query,
                        alpha=alpha,
                        limit=5,
                        document_id=document["id"],
                    )
                    self.assert_success(payload)
            finally:
                await self.delete_document_best_effort(document)
                await self.delete_category_best_effort(category)

        self.run_async(scenario())
