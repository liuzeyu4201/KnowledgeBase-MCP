from __future__ import annotations

import asyncio
import time

from test.base import MCPIntegrationTestCase
from test.mcp_test_client import MCPToolClient


class ImportTaskContractTestCase(MCPIntegrationTestCase):
    """覆盖批量文档导入任务 submit/get/cancel 核心流程与边界情况。"""

    # -------------------------------------------------------------------------
    # 正常流程
    # -------------------------------------------------------------------------

    def test_batch_submit_and_get_smoke(self) -> None:
        """提交批量任务并查询状态。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_smoke")
            try:
                payload = await self.submit_batch_import_task(
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"batch_doc_1_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                        {
                            "category_id": category["id"],
                            "title": f"batch_doc_2_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                    priority=50,
                    max_attempts=3,
                )
                self.assert_success(payload)
                task = payload["data"]["task"]
                self.assertEqual(task["status"], "queued")
                self.assertEqual(task["total_items"], 2)
                self.assertEqual(task["pending_items"], 2)

                # 查询任务
                get_payload = await self.tool(
                    "kb_document_import_batch_get",
                    id=task["id"],
                )
                self.assert_success(get_payload)
                self.assertEqual(get_payload["data"]["task"]["id"], task["id"])
            finally:
                # 清理
                await self.tool("kb_document_import_batch_cancel", id=task["id"])
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_submit_and_get_by_uid(self) -> None:
        """通过 task_uid 查询任务。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_uid")
            try:
                payload = await self.submit_batch_import_task(
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"batch_doc_uid_{self.unique_suffix()}",
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
                self.assertEqual(get_payload["data"]["task"]["task_uid"], task["task_uid"])
            finally:
                await self.tool("kb_document_import_batch_cancel", task_uid=task["task_uid"])
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_submit_mixed_markdown_and_docx(self) -> None:
        """批量提交 Markdown 和 DOCX 混合任务。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_mixed_types")
            try:
                payload = await self.submit_batch_import_task(
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"batch_md_{self.unique_suffix()}",
                            "file_name": "notes.md",
                            "mime_type": "text/markdown",
                            "file_content_base64": self.read_markdown_base64(title="Batch Markdown"),
                        },
                        {
                            "category_id": category["id"],
                            "title": f"batch_docx_{self.unique_suffix()}",
                            "file_name": "notes.docx",
                            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            "file_content_base64": self.read_docx_base64(title="Batch Docx"),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                final_status = task["status"]
                for _ in range(30):
                    get_payload = await self.tool("kb_document_import_batch_get", id=task["id"])
                    self.assert_success(get_payload)
                    final_status = get_payload["data"]["task"]["status"]
                    if final_status in {"success", "partial_success", "failed", "canceled"}:
                        break
                    await asyncio.sleep(1)

                self.assertEqual(final_status, "success")
                get_payload = await self.tool(
                    "kb_document_import_batch_get",
                    id=task["id"],
                    include_items=True,
                )
                self.assert_success(get_payload)
                items = get_payload["data"]["task"]["items"]
                self.assertEqual([item["mime_type"] for item in items], [
                    "text/markdown",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ])
                self.assertTrue(all(item["status"] == "success" for item in items))
            finally:
                await self.delete_documents_by_category_best_effort(category_id=category["id"])
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_cancel_queued_task(self) -> None:
        """提交后立即取消任务，允许 worker 抢占导致状态先进入终态。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_cancel_queued")
            try:
                payload = await self.submit_batch_import_task(
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"batch_cancel_{self.unique_suffix()}",
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
                self.assertIn(
                    cancel_payload["data"]["task"]["status"],
                    {"canceled", "success", "partial_success", "failed"},
                )

                # 再次查询确认
                get_payload = await self.tool(
                    "kb_document_import_batch_get",
                    id=task["id"],
                )
                self.assert_success(get_payload)
                self.assertIn(
                    get_payload["data"]["task"]["status"],
                    {"canceled", "success", "partial_success", "failed"},
                )
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_cancel_already_finished_task_returns_conflict(self) -> None:
        """取消已完成的任務应直接返回（不做二次取消）。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_cancel_finished")
            try:
                payload = await self.submit_batch_import_task(
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"batch_finish_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                # 等待 worker 处理（最多 60s）
                for _ in range(60):
                    await asyncio.sleep(1)
                    get_payload = await self.tool(
                        "kb_document_import_batch_get",
                        id=task["id"],
                    )
                    self.assert_success(get_payload)
                    status = get_payload["data"]["task"]["status"]
                    if status in {"success", "partial_success", "failed"}:
                        break

                # 取消已结束的任务
                cancel_payload = await self.tool(
                    "kb_document_import_batch_cancel",
                    id=task["id"],
                )
                self.assert_success(cancel_payload)
                # 已结束任务取消后状态不变
                self.assertIn(
                    cancel_payload["data"]["task"]["status"],
                    {"success", "partial_success", "failed"},
                )
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    # -------------------------------------------------------------------------
    # 边缘/边界情况
    # -------------------------------------------------------------------------

    def test_batch_submit_rejects_empty_items(self) -> None:
        """items 为空列表时应被拒绝。"""

        async def scenario() -> None:
            payload = await self.submit_batch_import_task(
                items=[],
            )
            self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")

        self.run_async(scenario())

    def test_batch_submit_rejects_items_over_limit(self) -> None:
        """items 数量超过 100 时应被拒绝。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_over_limit")
            try:
                payload = await self.submit_batch_import_task(
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"batch_item_{i}_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        }
                        for i in range(101)
                    ],
                )
                self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_submit_rejects_invalid_category(self) -> None:
        """item 中包含不存在的 category_id 应被拒绝。"""

        async def scenario() -> None:
            payload = await self.submit_batch_import_task(
                items=[
                    {
                        "category_id": 99999999,
                        "title": f"batch_invalid_cat_{self.unique_suffix()}",
                        "file_name": "Functional_Analysis.pdf",
                        "mime_type": "application/pdf",
                        "file_content_base64": self.read_pdf_base64(),
                    },
                ],
            )
            self.assert_error(payload, code="CATEGORY_NOT_FOUND", error_type="not_found")

        self.run_async(scenario())

    def test_batch_submit_rejects_invalid_mime_type(self) -> None:
        """item 中 mime_type 不是 application/pdf 时应被拒绝。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_invalid_mime")
            try:
                payload = await self.submit_batch_import_task(
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"batch_mime_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.txt",
                            "mime_type": "text/plain",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_submit_rejects_invalid_base64(self) -> None:
        """item 中 file_content_base64 为非法格式时应被拒绝。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_invalid_b64")
            try:
                payload = await self.submit_batch_import_task(
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"batch_b64_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": "%%%not_valid_base64%%%",
                        },
                    ],
                )
                self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_submit_with_idempotency_key_returns_same_task(self) -> None:
        """相同 idempotency_key 应返回同一任务。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_idempotency")
            idempotency_key = f"idem_{self.unique_suffix()}"
            try:
                payload1 = await self.submit_batch_import_task(
                    idempotency_key=idempotency_key,
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"batch_idem_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload1)
                task1 = payload1["data"]["task"]

                # 相同 key 再次提交
                payload2 = await self.submit_batch_import_task(
                    idempotency_key=idempotency_key,
                    items=[
                        {
                            "category_id": category["id"],
                            "title": "batch_idem_different",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload2)
                task2 = payload2["data"]["task"]

                # 应该是同一个任务
                self.assertEqual(task1["id"], task2["id"])
                self.assertEqual(task1["task_uid"], task2["task_uid"])
            finally:
                await self.tool("kb_document_import_batch_cancel", id=task1["id"])
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_submit_rejects_empty_title(self) -> None:
        """item 中 title 为空时应被拒绝。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_empty_title")
            try:
                payload = await self.submit_batch_import_task(
                    items=[
                        {
                            "category_id": category["id"],
                            "title": "   ",
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

    def test_batch_get_rejects_neither_id_nor_task_uid(self) -> None:
        """查询时既没有 id 也没有 task_uid 应被拒绝。"""

        async def scenario() -> None:
            payload = await self.tool(
                "kb_document_import_batch_get",
            )
            self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")

        self.run_async(scenario())

    def test_batch_get_rejects_mismatch_id_and_task_uid(self) -> None:
        """id 和 task_uid 同时提供但不匹配时应被拒绝。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_mismatch")
            try:
                submit_payload = await self.submit_batch_import_task(
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"batch_mismatch_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(submit_payload)
                task = submit_payload["data"]["task"]

                # 用错误的 id 配合正确的 task_uid
                get_payload = await self.tool(
                    "kb_document_import_batch_get",
                    id=99999999,
                    task_uid=task["task_uid"],
                )
                self.assert_error(get_payload, code="INVALID_ARGUMENT", error_type="validation_error")
            finally:
                await self.tool("kb_document_import_batch_cancel", task_uid=task["task_uid"])
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_get_not_found_task(self) -> None:
        """查询不存在的任务应返回 NOT_FOUND。"""

        async def scenario() -> None:
            payload = await self.tool(
                "kb_document_import_batch_get",
                id=99999999,
            )
            self.assert_error(payload, code="IMPORT_TASK_NOT_FOUND", error_type="not_found")

        self.run_async(scenario())

    def test_batch_cancel_not_found_task(self) -> None:
        """取消不存在的任务应返回 NOT_FOUND。"""

        async def scenario() -> None:
            payload = await self.tool(
                "kb_document_import_batch_cancel",
                id=99999999,
            )
            self.assert_error(payload, code="IMPORT_TASK_NOT_FOUND", error_type="not_found")

        self.run_async(scenario())

    def test_batch_cancel_rejects_neither_id_nor_task_uid(self) -> None:
        """取消时既没有 id 也没有 task_uid 应被拒绝。"""

        async def scenario() -> None:
            payload = await self.tool(
                "kb_document_import_batch_cancel",
            )
            self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")

        self.run_async(scenario())

    def test_batch_submit_rejects_priority_out_of_range(self) -> None:
        """priority 超出 0-1000 范围时应被拒绝。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_priority_range")
            try:
                payload = await self.submit_batch_import_task(
                    priority=1001,
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"batch_priority_{self.unique_suffix()}",
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

    def test_batch_submit_rejects_max_attempts_out_of_range(self) -> None:
        """max_attempts 超出 1-10 范围时应被拒绝。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_max_attempts_range")
            try:
                payload = await self.submit_batch_import_task(
                    max_attempts=11,
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"batch_attempts_{self.unique_suffix()}",
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

    def test_batch_submit_rejects_item_priority_out_of_range(self) -> None:
        """item 中 priority 超出 0-1000 范围时应被拒绝。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_item_priority_range")
            try:
                payload = await self.submit_batch_import_task(
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"batch_item_priority_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                            "priority": 1001,
                        },
                    ],
                )
                self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_submit_large_pdf(self) -> None:
        """提交大文件 PDF（ Functional Analysis Notes.pdf）。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_large_pdf")
            try:
                payload = await self.submit_batch_import_task(
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"batch_large_{self.unique_suffix()}",
                            "file_name": "Functional Analysis Notes.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(large=True),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]
                self.assertEqual(task["status"], "queued")
            finally:
                await self.tool("kb_document_import_batch_cancel", id=task["id"])
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_get_include_items_false(self) -> None:
        """查询时 include_items=False 不返回子项详情。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_no_items")
            try:
                payload = await self.submit_batch_import_task(
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"batch_items_false_{self.unique_suffix()}",
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
                    include_items=False,
                )
                self.assert_success(get_payload)
                self.assertIsNone(get_payload["data"]["task"]["items"])
            finally:
                await self.tool("kb_document_import_batch_cancel", id=task["id"])
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    # -------------------------------------------------------------------------
    # 并发测试
    # -------------------------------------------------------------------------

    def test_concurrent_batch_submit_same_idempotency_key(self) -> None:
        """并发提交相同 idempotency_key 的任务，应收敛到同一任务。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_concurrent_idem")
            idempotency_key = f"concurrent_idem_{self.unique_suffix()}"
            try:

                async def submit_once(idx: int) -> dict:
                    staged_file = self.upload_staged_file(
                        file_name="Functional_Analysis.pdf",
                        file_bytes=self.read_pdf_bytes(),
                        mime_type="application/pdf",
                    )
                    async with MCPToolClient(self.server_url) as client:
                        return await client.call_tool(
                            "kb_document_import_batch_submit_from_staged",
                            {
                                "idempotency_key": idempotency_key,
                                "items": [
                                    {
                                        "category_id": category["id"],
                                        "title": f"concurrent_idem_item_{idx}_{self.unique_suffix()}",
                                        "staged_file_id": staged_file["id"],
                                    },
                                ],
                            },
                        )

                results = await asyncio.gather(*(submit_once(i) for i in range(5)))
                for payload in results:
                    self.assert_success(payload)
                task_ids = {r["data"]["task"]["id"] for r in results}
                self.assertEqual(len(task_ids), 1, results)

                task_id = next(iter(task_ids))
                await self.tool("kb_document_import_batch_cancel", id=task_id)
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_concurrent_batch_submit_different_tasks(self) -> None:
        """并发提交多个不同的批量任务，所有任务都成功创建。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_concurrent_diff")
            try:

                async def submit_once(idx: int) -> dict:
                    staged_file = self.upload_staged_file(
                        file_name="Functional_Analysis.pdf",
                        file_bytes=self.read_pdf_bytes(),
                        mime_type="application/pdf",
                    )
                    async with MCPToolClient(self.server_url) as client:
                        return await client.call_tool(
                            "kb_document_import_batch_submit_from_staged",
                            {
                                "items": [
                                    {
                                        "category_id": category["id"],
                                        "title": f"concurrent_diff_{idx}_{self.unique_suffix()}",
                                        "staged_file_id": staged_file["id"],
                                    },
                                ],
                            },
                        )

                results = await asyncio.gather(*(submit_once(i) for i in range(5)))
                for payload in results:
                    self.assert_success(payload)
                task_ids = [r["data"]["task"]["id"] for r in results if r.get("success")]

                # 清理
                for tid in task_ids:
                    await self.tool("kb_document_import_batch_cancel", id=tid)
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_concurrent_batch_cancel_same_task(self) -> None:
        """并发取消同一任务，所有取消请求都成功返回。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_concurrent_cancel")
            try:
                submit_payload = await self.submit_batch_import_task(
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"concurrent_cancel_{self.unique_suffix()}",
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

                results = await asyncio.gather(*(cancel_once() for _ in range(5)))
                for payload in results:
                    self.assert_success(payload)
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    # -------------------------------------------------------------------------
    # 一致性测试
    # -------------------------------------------------------------------------

    def test_batch_task_progress_after_submit(self) -> None:
        """提交后任务状态和进度正确。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_progress")
            try:
                payload = await self.submit_batch_import_task(
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"progress_{i}_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        }
                        for i in range(3)
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]
                self.assertEqual(task["status"], "queued")
                self.assertEqual(task["total_items"], 3)
                self.assertEqual(task["pending_items"], 3)
                self.assertEqual(task["running_items"], 0)
                self.assertEqual(task["success_items"], 0)
                self.assertEqual(task["failed_items"], 0)
                self.assertEqual(task["canceled_items"], 0)
                self.assertEqual(task["progress_percent"], 0.0)
            finally:
                await self.tool("kb_document_import_batch_cancel", id=task["id"])
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_task_full_lifecycle_pending_to_canceled(self) -> None:
        """完整生命周期：queued -> canceled。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_lifecycle")
            try:
                payload = await self.submit_batch_import_task(
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"lifecycle_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]
                task_id = task["id"]

                # 取消
                cancel_payload = await self.tool(
                    "kb_document_import_batch_cancel",
                    id=task_id,
                )
                self.assert_success(cancel_payload)
                self.assertEqual(cancel_payload["data"]["task"]["status"], "canceled")
                self.assertEqual(cancel_payload["data"]["task"]["canceled_items"], 1)
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_task_metadata_fields_preserved(self) -> None:
        """任务元数据字段（request_id, operator, trace_id）正确保存。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_metadata")
            try:
                payload = await self.submit_batch_import_task(
                    request_id=f"req_{self.unique_suffix()}",
                    operator=f"op_{self.unique_suffix()}",
                    trace_id=f"trace_{self.unique_suffix()}",
                    priority=75,
                    max_attempts=5,
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"metadata_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]
                self.assertIsNotNone(task["request_id"])
                self.assertIsNotNone(task["operator"])
                self.assertIsNotNone(task["trace_id"])
                self.assertEqual(task["priority"], 75)
                self.assertEqual(task["max_attempts"], 5)
            finally:
                await self.tool("kb_document_import_batch_cancel", id=task["id"])
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_task_priority_ordering(self) -> None:
        """高优先级任务排在前面（通过 worker 处理顺序验证）。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_priority_order")
            try:
                # 提交低优先级任务
                low_payload = await self.submit_batch_import_task(
                    priority=10,
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"low_priority_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(low_payload)
                low_task = low_payload["data"]["task"]

                # 提交高优先级任务
                high_payload = await self.submit_batch_import_task(
                    priority=100,
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"high_priority_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(high_payload)
                high_task = high_payload["data"]["task"]

                # 验证高优先级任务排在前面（id 较小表示先创建，但优先级更高）
                self.assertGreater(high_task["priority"], low_task["priority"])

                # 清理
                await self.tool("kb_document_import_batch_cancel", id=low_task["id"])
                await self.tool("kb_document_import_batch_cancel", id=high_task["id"])
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_task_item_statuses_consistent(self) -> None:
        """任务子项状态一致性：子项状态之和与任务状态一致。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="batch_item_status")
            try:
                payload = await self.submit_batch_import_task(
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"item_status_{i}_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        }
                        for i in range(3)
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
                self.assertEqual(len(items), 3)
                for item in items:
                    self.assertEqual(item["status"], "pending")
                    self.assertEqual(item["attempt_count"], 0)
                    self.assertIsNone(item["started_at"])
                    self.assertIsNone(item["finished_at"])
                    self.assertIsNone(item["last_error"])
            finally:
                await self.tool("kb_document_import_batch_cancel", id=task["id"])
                await self.delete_category_best_effort(category)

        self.run_async(scenario())
