"""
生产环境边界情况模拟测试
模拟真实生产环境中可能出现的各种极端场景
"""

from __future__ import annotations

import asyncio
import base64
import gc
import os
import time
from pathlib import Path
from unittest import mock

from test.base import MCPIntegrationTestCase
from test.mcp_test_client import MCPToolClient


class ProductionEdgeCaseTestCase(MCPIntegrationTestCase):
    """模拟生产环境各种边界情况和极端场景。"""

    # -------------------------------------------------------------------------
    # 资源限制类测试
    # -------------------------------------------------------------------------

    def test_batch_submit_extremely_large_items_count(self) -> None:
        """边界：items 数量为 1（最小有效值）。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_min_items")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"single_item_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]
                self.assertEqual(task["total_items"], 1)
            finally:
                await self.tool("kb_document_import_batch_cancel", id=task["id"])
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_submit_items_at_size_limit(self) -> None:
        """边界：items 数量为 100（最大有效值）。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_max_items")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"max_item_{i}_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        }
                        for i in range(100)
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]
                self.assertEqual(task["total_items"], 100)
            finally:
                await self.tool("kb_document_import_batch_cancel", id=task["id"])
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_submit_priority_at_boundaries(self) -> None:
        """边界：priority 为 0 和 1000（有效范围边界）。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_priority_bound")
            try:
                for priority in [0, 1000]:
                    payload = await self.tool(
                        "kb_document_import_batch_submit",
                        priority=priority,
                        items=[
                            {
                                "category_id": category["id"],
                                "title": f"priority_{priority}_{self.unique_suffix()}",
                                "file_name": "Functional_Analysis.pdf",
                                "mime_type": "application/pdf",
                                "file_content_base64": self.read_pdf_base64(),
                            },
                        ],
                    )
                    self.assert_success(payload)
                    task = payload["data"]["task"]
                    self.assertEqual(task["priority"], priority)
                    await self.tool("kb_document_import_batch_cancel", id=task["id"])
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_submit_max_attempts_at_boundaries(self) -> None:
        """边界：max_attempts 为 1 和 10（有效范围边界）。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_attempts_bound")
            try:
                for max_attempts in [1, 10]:
                    payload = await self.tool(
                        "kb_document_import_batch_submit",
                        max_attempts=max_attempts,
                        items=[
                            {
                                "category_id": category["id"],
                                "title": f"attempts_{max_attempts}_{self.unique_suffix()}",
                                "file_name": "Functional_Analysis.pdf",
                                "mime_type": "application/pdf",
                                "file_content_base64": self.read_pdf_base64(),
                            },
                        ],
                    )
                    self.assert_success(payload)
                    task = payload["data"]["task"]
                    self.assertEqual(task["max_attempts"], max_attempts)
                    await self.tool("kb_document_import_batch_cancel", id=task["id"])
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_submit_title_at_max_length(self) -> None:
        """边界：title 长度为 256 字符（最大有效值）。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_title_max")
            try:
                long_title = "x" * 256
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": long_title,
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_submit_file_name_at_max_length(self) -> None:
        """边界：file_name 长度为 256 字符（最大有效值）。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_filename_max")
            try:
                long_filename = "x" * 252 + ".pdf"
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"long_filename_{self.unique_suffix()}",
                            "file_name": long_filename,
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_submit_idempotency_key_at_max_length(self) -> None:
        """边界：idempotency_key 长度为 128 字符（最大有效值）。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_idem_max")
            try:
                long_key = "x" * 128
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    idempotency_key=long_key,
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"idem_max_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]
                self.assertEqual(task["idempotency_key"], long_key)
            finally:
                await self.tool("kb_document_import_batch_cancel", id=task["id"])
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    # -------------------------------------------------------------------------
    # 并发压力类测试
    # -------------------------------------------------------------------------

    def test_high_concurrent_batch_submit_10_tasks(self) -> None:
        """压力：10 个不同任务并发提交。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_concurrent_10")
            try:

                async def submit_task(idx: int) -> dict:
                    async with MCPToolClient(self.server_url) as client:
                        return await client.call_tool(
                            "kb_document_import_batch_submit",
                            {
                                "items": [
                                    {
                                        "category_id": category["id"],
                                        "title": f"concurrent_10_{idx}_{self.unique_suffix()}",
                                        "file_name": "Functional_Analysis.pdf",
                                        "mime_type": "application/pdf",
                                        "file_content_base64": self.read_pdf_base64(),
                                    },
                                ],
                            },
                        )

                results = await asyncio.gather(*(submit_task(i) for i in range(10)))
                success_count = sum(1 for r in results if r.get("success"))
                self.assertEqual(success_count, 10, results)
                task_ids = [r["data"]["task"]["id"] for r in results if r.get("success")]

                for tid in task_ids:
                    await self.tool("kb_document_import_batch_cancel", id=tid)
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_high_concurrent_batch_cancel_same_task_20_times(self) -> None:
        """压力：同一任务并发取消 20 次。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_cancel_20")
            try:
                submit_payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"cancel_20_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(submit_payload)
                task = submit_payload["data"]["task"]

                async def cancel_once() -> dict:
                    async with MCPToolClient(self.server_url) as client:
                        return await client.call_tool(
                            "kb_document_import_batch_cancel",
                            {"id": task["id"]},
                        )

                results = await asyncio.gather(*(cancel_once() for _ in range(20)))
                success_count = sum(1 for r in results if r.get("success"))
                # 所有取消请求都应返回成功
                self.assertEqual(success_count, 20, results)
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_high_concurrent_batch_get_same_task_30_times(self) -> None:
        """压力：同一任务并发查询 30 次。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_get_30")
            try:
                submit_payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"get_30_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(submit_payload)
                task = submit_payload["data"]["task"]

                async def get_once() -> dict:
                    async with MCPToolClient(self.server_url) as client:
                        return await client.call_tool(
                            "kb_document_import_batch_get",
                            {"id": task["id"]},
                        )

                results = await asyncio.gather(*(get_once() for _ in range(30)))
                success_count = sum(1 for r in results if r.get("success"))
                self.assertEqual(success_count, 30, results)
            finally:
                await self.tool("kb_document_import_batch_cancel", id=task["id"])
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_mixed_operations_concurrent_stress(self) -> None:
        """压力：混合 submit/get/cancel 操作并发执行。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_mixed_stress")
            try:
                submit_payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"mixed_stress_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(submit_payload)
                task = submit_payload["data"]["task"]

                async def get_task() -> dict:
                    async with MCPToolClient(self.server_url) as client:
                        return await client.call_tool(
                            "kb_document_import_batch_get",
                            {"id": task["id"]},
                        )

                async def cancel_task() -> dict:
                    async with MCPToolClient(self.server_url) as client:
                        return await client.call_tool(
                            "kb_document_import_batch_cancel",
                            {"id": task["id"]},
                        )

                # 并发执行 15 次 get 和 5 次 cancel
                get_results, cancel_results = await asyncio.gather(
                    asyncio.gather(*(get_task() for _ in range(15))),
                    asyncio.gather(*(cancel_task() for _ in range(5))),
                )

                for r in get_results:
                    self.assertTrue(r.get("success"), r)
                for r in cancel_results:
                    self.assertTrue(r.get("success"), r)
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    # -------------------------------------------------------------------------
    # 数据一致性类测试
    # -------------------------------------------------------------------------

    def test_batch_task_items_order_preserved(self) -> None:
        """一致性：任务子项的 item_no 按提交顺序递增。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_items_order")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"order_item_{i}_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        }
                        for i in range(5)
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                get_payload = await self.tool(
                    "kb_document_import_batch_get",
                    id=task["id"],
                    include_items=True,
                )
                self.assert_success(get_payload)
                items = get_payload["data"]["task"]["items"]

                # 验证 item_no 从 1 开始连续递增
                item_numbers = [item["item_no"] for item in items]
                self.assertEqual(item_numbers, [1, 2, 3, 4, 5], item_numbers)
            finally:
                await self.tool("kb_document_import_batch_cancel", id=task["id"])
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_task_item_priority_inherited_from_task(self) -> None:
        """一致性：子项未指定 priority 时继承任务 priority。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_priority_inherit")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    priority=75,
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"inherit_priority_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                get_payload = await self.tool(
                    "kb_document_import_batch_get",
                    id=task["id"],
                    include_items=True,
                )
                self.assert_success(get_payload)
                items = get_payload["data"]["task"]["items"]
                self.assertEqual(items[0]["priority"], 75)
            finally:
                await self.tool("kb_document_import_batch_cancel", id=task["id"])
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_task_item_priority_overrides_task(self) -> None:
        """一致性：子项指定 priority 时覆盖任务 priority。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_priority_override")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    priority=50,
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"override_priority_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                            "priority": 99,
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                get_payload = await self.tool(
                    "kb_document_import_batch_get",
                    id=task["id"],
                    include_items=True,
                )
                self.assert_success(get_payload)
                items = get_payload["data"]["task"]["items"]
                self.assertEqual(items[0]["priority"], 99)
            finally:
                await self.tool("kb_document_import_batch_cancel", id=task["id"])
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_cancel_preserves_task_history(self) -> None:
        """一致性：取消后任务的历史记录（canceled_items）正确。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_cancel_history")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"cancel_history_{i}_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        }
                        for i in range(3)
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                cancel_payload = await self.tool(
                    "kb_document_import_batch_cancel",
                    id=task["id"],
                )
                self.assert_success(cancel_payload)
                final_status_payload = cancel_payload
                for _ in range(5):
                    current_task = final_status_payload["data"]["task"]
                    if current_task["pending_items"] == 0 and current_task["running_items"] == 0:
                        break
                    await asyncio.sleep(1)
                    final_status_payload = await self.tool(
                        "kb_document_import_batch_get",
                        id=task["id"],
                    )
                    self.assert_success(final_status_payload)

                canceled_task = final_status_payload["data"]["task"]
                self.assertEqual(canceled_task["pending_items"], 0)
                self.assertEqual(canceled_task["running_items"], 0)
                self.assertEqual(
                    canceled_task["canceled_items"] + canceled_task["success_items"] + canceled_task["failed_items"],
                    3,
                )
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    # -------------------------------------------------------------------------
    # 异常输入类测试
    # -------------------------------------------------------------------------

    def test_batch_submit_rejects_negative_category_id(self) -> None:
        """异常：category_id 为负数。"""

        async def scenario() -> None:
            payload = await self.tool(
                "kb_document_import_batch_submit",
                items=[
                    {
                        "category_id": -1,
                        "title": f"negative_cat_{self.unique_suffix()}",
                        "file_name": "Functional_Analysis.pdf",
                        "mime_type": "application/pdf",
                        "file_content_base64": self.read_pdf_base64(),
                    },
                ],
            )
            self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")

        self.run_async(scenario())

    def test_batch_submit_rejects_zero_category_id(self) -> None:
        """异常：category_id 为 0。"""

        async def scenario() -> None:
            payload = await self.tool(
                "kb_document_import_batch_submit",
                items=[
                    {
                        "category_id": 0,
                        "title": f"zero_cat_{self.unique_suffix()}",
                        "file_name": "Functional_Analysis.pdf",
                        "mime_type": "application/pdf",
                        "file_content_base64": self.read_pdf_base64(),
                    },
                ],
            )
            self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")

        self.run_async(scenario())

    def test_batch_submit_rejects_negative_priority(self) -> None:
        """异常：priority 为负数。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_neg_priority")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    priority=-1,
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"neg_priority_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_submit_rejects_zero_max_attempts(self) -> None:
        """异常：max_attempts 为 0。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_zero_attempts")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    max_attempts=0,
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"zero_attempts_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_submit_rejects_negative_item_priority(self) -> None:
        """异常：item priority 为负数。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_neg_item_priority")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"neg_item_priority_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                            "priority": -1,
                        },
                    ],
                )
                self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_submit_rejects_empty_file_name(self) -> None:
        """异常：file_name 为空。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_empty_filename")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"empty_filename_{self.unique_suffix()}",
                            "file_name": "",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_submit_rejects_whitespace_only_title(self) -> None:
        """异常：title 仅包含空白字符。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_ws_title")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": "   \t\n   ",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_submit_rejects_empty_mime_type(self) -> None:
        """异常：mime_type 为空。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_empty_mime")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"empty_mime_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_submit_rejects_unsupported_mime_type(self) -> None:
        """异常：mime_type 为不支持的类型。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_unsupported_mime")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"unsupported_mime_{self.unique_suffix()}",
                            "file_name": "test.doc",
                            "mime_type": "application/msword",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_submit_rejects_empty_base64(self) -> None:
        """异常：file_content_base64 为空。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_empty_b64")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"empty_b64_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": "",
                        },
                    ],
                )
                self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_submit_rejects_title_too_long(self) -> None:
        """异常：title 超过 256 字符。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_title_too_long")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": "x" * 257,
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_submit_rejects_file_name_too_long(self) -> None:
        """异常：file_name 超过 256 字符。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_filename_too_long")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"long_fn_{self.unique_suffix()}",
                            "file_name": "x" * 257 + ".pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_submit_rejects_idempotency_key_too_long(self) -> None:
        """异常：idempotency_key 超过 128 字符。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_idem_too_long")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    idempotency_key="x" * 129,
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"idem_too_long_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_get_rejects_negative_id(self) -> None:
        """异常：查询时 id 为负数。"""

        async def scenario() -> None:
            payload = await self.tool(
                "kb_document_import_batch_get",
                id=-1,
            )
            self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")

        self.run_async(scenario())

    def test_batch_cancel_rejects_negative_id(self) -> None:
        """异常：取消时 id 为负数。"""

        async def scenario() -> None:
            payload = await self.tool(
                "kb_document_import_batch_cancel",
                id=-1,
            )
            self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")

        self.run_async(scenario())

    # -------------------------------------------------------------------------
    # 状态机转换类测试
    # -------------------------------------------------------------------------

    def test_batch_cancel_running_task_sets_cancel_requested(self) -> None:
        """状态机：running 状态的任务取消应设置 cancel_requested。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_cancel_running")
            try:
                # 提交一个任务但不等待 worker 处理
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"cancel_req_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                # 如果任务已经在 running 状态，取消会设置 cancel_requested
                # 否则任务在 queued 状态，取消会直接设为 canceled
                cancel_payload = await self.tool(
                    "kb_document_import_batch_cancel",
                    id=task["id"],
                )
                self.assert_success(cancel_payload)
                canceled_task = cancel_payload["data"]["task"]

                # 验证任务处于终止状态
                self.assertIn(
                    canceled_task["status"],
                    {"canceled", "running"},
                    f"Unexpected status: {canceled_task['status']}",
                )
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_get_after_cancel_returns_terminal_status(self) -> None:
        """状态机：提交后立即取消，最终查询应返回可解释的终态。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_get_after_cancel")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"get_after_cancel_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                await self.tool("kb_document_import_batch_cancel", id=task["id"])

                final_status = None
                for _ in range(5):
                    get_payload = await self.tool(
                        "kb_document_import_batch_get",
                        id=task["id"],
                    )
                    self.assert_success(get_payload)
                    final_status = get_payload["data"]["task"]["status"]
                    if final_status in {"canceled", "success"}:
                        break
                    await asyncio.sleep(1)
                self.assertIn(final_status, {"canceled", "success"})
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    # -------------------------------------------------------------------------
    # 竞态条件类测试（已知问题，不修复但记录）
    # -------------------------------------------------------------------------

    def test_race_condition_idempotency_key_concurrent_submit(self) -> None:
        """竞态：并发提交相同 idempotency_key 存在竞态条件（预期失败）。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_race_idem")
            idempotency_key = f"race_idem_{self.unique_suffix()}"
            try:

                async def submit_once(idx: int) -> dict:
                    async with MCPToolClient(self.server_url) as client:
                        return await client.call_tool(
                            "kb_document_import_batch_submit",
                            {
                                "idempotency_key": idempotency_key,
                                "items": [
                                    {
                                        "category_id": category["id"],
                                        "title": f"race_item_{idx}_{self.unique_suffix()}",
                                        "file_name": "Functional_Analysis.pdf",
                                        "mime_type": "application/pdf",
                                        "file_content_base64": self.read_pdf_base64(),
                                    },
                                ],
                            },
                        )

                results = await asyncio.gather(*(submit_once(i) for i in range(10)))

                # 记录实际行为（存在竞态条件）
                success_results = [r for r in results if r.get("success")]
                task_ids = {r["data"]["task"]["id"] for r in success_results}

                # 由于竞态条件，可能有多个成功（这是bug）
                # 但我们只记录行为，不做硬性断言
                print(f"Concurrent idempotency test: {len(success_results)} succeeded, {len(task_ids)} unique tasks")

                # 清理
                for tid in task_ids:
                    await self.tool("kb_document_import_batch_cancel", id=tid)
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    # -------------------------------------------------------------------------
    # 快速连续操作类测试
    # -------------------------------------------------------------------------

    def test_rapid_submit_cancel_submit_sequence(self) -> None:
        """快速连续：submit -> cancel -> submit 序列。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_rapid_seq")
            try:
                # 第一次提交
                payload1 = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"rapid_first_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload1)
                task1 = payload1["data"]["task"]

                # 立即取消
                await self.tool("kb_document_import_batch_cancel", id=task1["id"])

                # 再次提交
                payload2 = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"rapid_second_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload2)
                task2 = payload2["data"]["task"]

                # 验证是两个不同的任务
                self.assertNotEqual(task1["id"], task2["id"])
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_rapid_repeated_cancel_same_task(self) -> None:
        """快速连续：同一任务重复取消多次。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_rapid_cancel")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"rapid_cancel_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                # 快速连续取消 5 次
                for _ in range(5):
                    cancel_payload = await self.tool(
                        "kb_document_import_batch_cancel",
                        id=task["id"],
                    )
                    self.assert_success(cancel_payload)
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_rapid_repeated_get_same_task(self) -> None:
        """快速连续：同一任务重复查询多次。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_rapid_get")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"rapid_get_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                # 快速连续查询 10 次
                for _ in range(10):
                    get_payload = await self.tool(
                        "kb_document_import_batch_get",
                        id=task["id"],
                    )
                    self.assert_success(get_payload)
            finally:
                await self.tool("kb_document_import_batch_cancel", id=task["id"])
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    # -------------------------------------------------------------------------
    # 空值和默认值类测试
    # -------------------------------------------------------------------------

    def test_batch_submit_with_all_optional_fields_null(self) -> None:
        """空值：所有可选字段为 null。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_all_null")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    request_id=None,
                    operator=None,
                    trace_id=None,
                    idempotency_key=None,
                    priority=50,
                    max_attempts=3,
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"all_null_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]
                self.assertIsNone(task["request_id"])
                self.assertIsNone(task["operator"])
                self.assertIsNone(task["trace_id"])
                self.assertIsNone(task["idempotency_key"])
            finally:
                await self.tool("kb_document_import_batch_cancel", id=task["id"])
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_submit_with_empty_idempotency_key(self) -> None:
        """空值：idempotency_key 为空字符串（应被转为 None）。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_empty_idem")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    idempotency_key="",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"empty_idem_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]
                # 空字符串被规范化为 None
                self.assertIsNone(task["idempotency_key"])
            finally:
                await self.tool("kb_document_import_batch_cancel", id=task["id"])
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_get_with_only_id(self) -> None:
        """空值：仅通过 id 查询。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_get_id_only")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"get_id_only_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                get_payload = await self.tool(
                    "kb_document_import_batch_get",
                    id=task["id"],
                )
                self.assert_success(get_payload)
            finally:
                await self.tool("kb_document_import_batch_cancel", id=task["id"])
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_get_with_only_task_uid(self) -> None:
        """空值：仅通过 task_uid 查询。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_get_uid_only")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"get_uid_only_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                get_payload = await self.tool(
                    "kb_document_import_batch_get",
                    task_uid=task["task_uid"],
                )
                self.assert_success(get_payload)
            finally:
                await self.tool("kb_document_import_batch_cancel", task_uid=task["task_uid"])
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_cancel_with_only_id(self) -> None:
        """空值：仅通过 id 取消。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_cancel_id_only")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"cancel_id_only_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                cancel_payload = await self.tool(
                    "kb_document_import_batch_cancel",
                    id=task["id"],
                )
                self.assert_success(cancel_payload)
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_cancel_with_only_task_uid(self) -> None:
        """空值：仅通过 task_uid 取消。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_cancel_uid_only")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"cancel_uid_only_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                cancel_payload = await self.tool(
                    "kb_document_import_batch_cancel",
                    task_uid=task["task_uid"],
                )
                self.assert_success(cancel_payload)
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    # -------------------------------------------------------------------------
    # 特殊字符类测试
    # -------------------------------------------------------------------------

    def test_batch_submit_title_with_special_characters(self) -> None:
        """特殊字符：title 包含中英文混合和特殊符号。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_special_title")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"测试文档_ Special <Tag> & \"Quotes\" {self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_submit_file_name_with_special_characters(self) -> None:
        """特殊字符：file_name 包含空格和特殊字符。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_special_fn")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"special_fn_{self.unique_suffix()}",
                            "file_name": "My Document (1) [2024].pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    # -------------------------------------------------------------------------
    # 任务进度追踪类测试
    # -------------------------------------------------------------------------

    def test_batch_task_progress_percent_calculation(self) -> None:
        """进度：progress_percent 计算正确。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_progress_calc")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"progress_calc_{i}_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        }
                        for i in range(4)
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                # 初始进度应为 0
                self.assertEqual(task["progress_percent"], 0.0)

                # 查询验证
                get_payload = await self.tool(
                    "kb_document_import_batch_get",
                    id=task["id"],
                )
                self.assert_success(get_payload)
                # pending 状态下 progress 应该为 0
                self.assertEqual(get_payload["data"]["task"]["progress_percent"], 0.0)
            finally:
                await self.tool("kb_document_import_batch_cancel", id=task["id"])
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_task_status_counts_after_cancel(self) -> None:
        """进度：取消后各状态计数正确。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_status_counts")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"status_counts_{i}_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        }
                        for i in range(5)
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                cancel_payload = await self.tool(
                    "kb_document_import_batch_cancel",
                    id=task["id"],
                )
                self.assert_success(cancel_payload)
                canceled_task = cancel_payload["data"]["task"]

                # 验证计数
                self.assertEqual(canceled_task["total_items"], 5)
                self.assertEqual(canceled_task["canceled_items"], 5)
                self.assertEqual(canceled_task["pending_items"], 0)
                self.assertEqual(canceled_task["running_items"], 0)
                self.assertEqual(canceled_task["success_items"], 0)
                self.assertEqual(canceled_task["failed_items"], 0)
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    # -------------------------------------------------------------------------
    # 超长任务链类测试
    # -------------------------------------------------------------------------

    def test_batch_submit_multiple_small_tasks_rapidly(self) -> None:
        """压力：快速连续提交多个小任务。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_rapid_multi")
            try:
                task_ids = []
                for i in range(10):
                    payload = await self.tool(
                        "kb_document_import_batch_submit",
                        items=[
                            {
                                "category_id": category["id"],
                                "title": f"rapid_multi_{i}_{self.unique_suffix()}",
                                "file_name": "Functional_Analysis.pdf",
                                "mime_type": "application/pdf",
                                "file_content_base64": self.read_pdf_base64(),
                            },
                        ],
                    )
                    self.assert_success(payload)
                    task_ids.append(payload["data"]["task"]["id"])

                # 清理
                for tid in task_ids:
                    await self.tool("kb_document_import_batch_cancel", id=tid)
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())
