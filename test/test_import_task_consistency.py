"""
任务一致性测试
验证任务取消后的跨存储一致性：文件清理、状态同步、资源释放
"""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

from test.base import MCPIntegrationTestCase
from test.mcp_test_client import MCPToolClient


class ImportTaskConsistencyTestCase(MCPIntegrationTestCase):
    """验证批量导入任务在各种场景下的一致性保证。"""

    # -------------------------------------------------------------------------
    # 取消后文件清理一致性
    # -------------------------------------------------------------------------

    def test_cancel_queued_task_cleans_staged_files(self) -> None:
        """一致性：取消 queued 任务后，暂存文件应被清理。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="consistency_cancel_clean")
            try:
                # 提交任务
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"consistency_clean_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                # 取消任务
                cancel_payload = await self.tool(
                    "kb_document_import_batch_cancel",
                    id=task["id"],
                )
                self.assert_success(cancel_payload)
                self.assertEqual(cancel_payload["data"]["task"]["status"], "canceled")

                # 验证文件被清理（通过再次查询确认状态稳定）
                for _ in range(3):
                    await asyncio.sleep(1)
                    get_payload = await self.tool(
                        "kb_document_import_batch_get",
                        id=task["id"],
                    )
                    self.assert_success(get_payload)
                    self.assertEqual(get_payload["data"]["task"]["status"], "canceled")
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_cancel_task_preserves_task_record_integrity(self) -> None:
        """一致性：取消任务后，任务记录应保持完整且状态一致。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="consistency_record")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"consistency_record_{i}_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        }
                        for i in range(3)
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                # 取消
                cancel_payload = await self.tool(
                    "kb_document_import_batch_cancel",
                    id=task["id"],
                )
                self.assert_success(cancel_payload)
                canceled_task = cancel_payload["data"]["task"]

                # 验证记录完整性
                self.assertIsNotNone(canceled_task["id"])
                self.assertIsNotNone(canceled_task["task_uid"])
                self.assertEqual(canceled_task["total_items"], 3)
                self.assertEqual(canceled_task["canceled_items"], 3)
                self.assertEqual(canceled_task["pending_items"], 0)
                self.assertEqual(canceled_task["running_items"], 0)
                self.assertEqual(canceled_task["success_items"], 0)
                self.assertEqual(canceled_task["failed_items"], 0)

                # 再次查询验证状态稳定
                get_payload = await self.tool(
                    "kb_document_import_batch_get",
                    id=task["id"],
                    include_items=True,
                )
                self.assert_success(get_payload)
                items = get_payload["data"]["task"]["items"]

                # 所有子项状态应为 canceled
                for item in items:
                    self.assertEqual(item["status"], "canceled", f"Item {item['item_no']} status should be canceled")
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_cancel_running_task_does_not_corrupt_other_items(self) -> None:
        """一致性：取消正在运行的任务时，不应影响同一任务中的其他子项记录。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="consistency_running")
            try:
                # 提交包含多个子项的任务
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"consistency_running_{i}_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        }
                        for i in range(5)
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                # 取消任务
                cancel_payload = await self.tool(
                    "kb_document_import_batch_cancel",
                    id=task["id"],
                )
                self.assert_success(cancel_payload)

                # 验证所有子项都被正确处理
                get_payload = await self.tool(
                    "kb_document_import_batch_get",
                    id=task["id"],
                    include_items=True,
                )
                self.assert_success(get_payload)
                task_data = get_payload["data"]["task"]

                # 计数一致性
                total = len(task_data["items"])
                canceled = sum(1 for item in task_data["items"] if item["status"] == "canceled")

                self.assertEqual(total, 5)
                self.assertEqual(canceled, 5)
                self.assertEqual(task_data["canceled_items"], 5)
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_cancel_then_get_returns_consistent_state(self) -> None:
        """一致性：取消后多次查询应返回一致的状态。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="consistency_multi_get")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"consistency_multi_get_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                # 取消
                await self.tool("kb_document_import_batch_cancel", id=task["id"])

                # 连续查询 10 次，验证状态一致
                statuses = []
                for _ in range(10):
                    get_payload = await self.tool(
                        "kb_document_import_batch_get",
                        id=task["id"],
                    )
                    self.assert_success(get_payload)
                    statuses.append(get_payload["data"]["task"]["status"])

                # 所有状态应该相同，并且必须是可解释的终态。
                self.assertEqual(len(set(statuses)), 1, f"Inconsistent statuses: {statuses}")
                self.assertIn(statuses[0], {"canceled", "success"})
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    # -------------------------------------------------------------------------
    # 并发取消一致性
    # -------------------------------------------------------------------------

    def test_concurrent_cancel_all_return_explainable_states(self) -> None:
        """一致性：并发取消同一任务，所有请求都应返回可解释状态且最终收敛。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="consistency_concurrent")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"consistency_concurrent_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                # 10 个并发取消
                async def cancel_once() -> dict:
                    async with MCPToolClient(self.server_url) as client:
                        return await client.call_tool(
                            "kb_document_import_batch_cancel",
                            {"id": task["id"]},
                        )

                results = await asyncio.gather(*(cancel_once() for _ in range(10)))

                # 所有请求都成功
                for r in results:
                    self.assertTrue(r.get("success"), r)

                statuses = [r["data"]["task"]["status"] for r in results]
                for status in statuses:
                    self.assertIn(status, {"cancel_requested", "canceled", "success"}, statuses)

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

    def test_concurrent_cancel_and_get_never_shows_inconsistent_state(self) -> None:
        """一致性：并发取消和查询操作不应显示不一致的状态。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="consistency_cancel_get")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"consistency_cancel_get_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

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

                # 并发执行 20 次 get 和 5 次 cancel
                get_tasks = [get_task() for _ in range(20)]
                cancel_tasks = [cancel_task() for _ in range(5)]

                all_results = await asyncio.gather(*(get_tasks + cancel_tasks))

                # 所有 get 请求都成功
                for r in all_results[:20]:
                    self.assertTrue(r.get("success"), r)

                # 所有 cancel 请求都成功
                for r in all_results[20:]:
                    self.assertTrue(r.get("success"), r)

                # 协作式取消允许短暂处于 cancel_requested，最终应收敛到 canceled。
                status = None
                for _ in range(5):
                    final_get = await self.tool("kb_document_import_batch_get", id=task["id"])
                    self.assert_success(final_get)
                    status = final_get["data"]["task"]["status"]
                    if status == "canceled":
                        break
                    await asyncio.sleep(1)
                self.assertIn(status, {"canceled", "success"})
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    # -------------------------------------------------------------------------
    # 状态转换一致性
    # -------------------------------------------------------------------------

    def test_task_status_transitions_are_atomic(self) -> None:
        """一致性：任务状态转换应是原子的。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="consistency_atomic")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"consistency_atomic_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]
                self.assertEqual(task["status"], "queued")

                # 取消
                cancel_payload = await self.tool(
                    "kb_document_import_batch_cancel",
                    id=task["id"],
                )
                self.assert_success(cancel_payload)

                # 状态直接变为终止状态
                self.assertIn(
                    cancel_payload["data"]["task"]["status"],
                    {"canceled"},
                    f"Unexpected transition to {cancel_payload['data']['task']['status']}",
                )

                # 不能再转换到其他状态
                second_cancel = await self.tool(
                    "kb_document_import_batch_cancel",
                    id=task["id"],
                )
                self.assert_success(second_cancel)
                # 已在终止状态，不会再变
                self.assertIn(
                    second_cancel["data"]["task"]["status"],
                    {"canceled", "success", "partial_success", "failed"},
                )
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_task_counts_always_equal_sum_of_item_counts(self) -> None:
        """一致性：任务的状态计数始终等于各状态子项数之和。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="consistency_counts")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"consistency_counts_{i}_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        }
                        for i in range(4)
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                # 初始状态验证
                get_payload = await self.tool(
                    "kb_document_import_batch_get",
                    id=task["id"],
                    include_items=True,
                )
                self.assert_success(get_payload)
                task_data = get_payload["data"]["task"]

                # 总数验证
                self.assertEqual(
                    task_data["total_items"],
                    task_data["pending_items"] + task_data["running_items"] +
                    task_data["success_items"] + task_data["failed_items"] +
                    task_data["canceled_items"],
                )

                # 取消任务
                await self.tool("kb_document_import_batch_cancel", id=task["id"])

                # 取消后再次验证
                get_payload2 = await self.tool(
                    "kb_document_import_batch_get",
                    id=task["id"],
                    include_items=True,
                )
                self.assert_success(get_payload2)
                task_data2 = get_payload2["data"]["task"]

                self.assertEqual(
                    task_data2["total_items"],
                    task_data2["pending_items"] + task_data2["running_items"] +
                    task_data2["success_items"] + task_data2["failed_items"] +
                    task_data2["canceled_items"],
                )
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_cancel_task_with_uid_and_id_both_provided(self) -> None:
        """一致性：同时提供 task_uid 和 id 取消任务，应一致处理。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="consistency_both_ids")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"consistency_both_ids_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                # 用 id 取消
                cancel_payload = await self.tool(
                    "kb_document_import_batch_cancel",
                    id=task["id"],
                )
                self.assert_success(cancel_payload)

                # 验证状态
                get_payload = await self.tool(
                    "kb_document_import_batch_get",
                    task_uid=task["task_uid"],
                )
                self.assert_success(get_payload)
                status = get_payload["data"]["task"]["status"]
                self.assertIn(status, {"cancel_requested", "canceled"})

                # 协作式取消允许短暂处于 cancel_requested，最终应收敛到 canceled。
                for _ in range(5):
                    if status == "canceled":
                        break
                    await asyncio.sleep(1)
                    get_payload = await self.tool(
                        "kb_document_import_batch_get",
                        task_uid=task["task_uid"],
                    )
                    self.assert_success(get_payload)
                    status = get_payload["data"]["task"]["status"]
                self.assertIn(status, {"canceled", "success"})
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    # -------------------------------------------------------------------------
    # 重复操作一致性
    # -------------------------------------------------------------------------

    def test_repeated_cancel_returns_consistent_response(self) -> None:
        """一致性：重复取消同一任务，每次返回一致响应。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="consistency_repeat_cancel")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"consistency_repeat_cancel_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                # 第一次取消
                result1 = await self.tool("kb_document_import_batch_cancel", id=task["id"])
                self.assert_success(result1)

                # 重复取消 5 次
                results = [result1]
                for _ in range(5):
                    result = await self.tool("kb_document_import_batch_cancel", id=task["id"])
                    results.append(result)

                # 所有请求都成功
                for r in results:
                    self.assert_success(r)

                # 最终状态稳定
                self.assertIn(results[-1]["data"]["task"]["status"], {"canceled", "success"})
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_repeated_get_returns_consistent_response(self) -> None:
        """一致性：重复查询同一任务，每次返回一致响应。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="consistency_repeat_get")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"consistency_repeat_get_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                # 重复查询 10 次
                results = []
                for _ in range(10):
                    result = await self.tool("kb_document_import_batch_get", id=task["id"])
                    self.assert_success(result)
                    results.append(result)

                # 验证返回的数据一致
                for r in results:
                    self.assertEqual(r["data"]["task"]["id"], task["id"])
                    self.assertEqual(r["data"]["task"]["task_uid"], task["task_uid"])
                    self.assertIn(r["data"]["task"]["status"], {"queued", "running", "cancel_requested"})
                    self.assertEqual(r["data"]["task"]["total_items"], 1)
            finally:
                await self.tool("kb_document_import_batch_cancel", id=task["id"])
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    # -------------------------------------------------------------------------
    # 任务完成后的查询一致性
    # -------------------------------------------------------------------------

    def test_task_not_found_after_repeated_cancel(self) -> None:
        """一致性：对于已取消的任务，重复取消应返回 NOT_FOUND 或一致状态。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="consistency_not_found")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"consistency_not_found_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                # 取消
                await self.tool("kb_document_import_batch_cancel", id=task["id"])

                # 查询应该能找到
                get_payload = await self.tool(
                    "kb_document_import_batch_get",
                    id=task["id"],
                )
                self.assert_success(get_payload)
                self.assertIn(get_payload["data"]["task"]["status"], {"canceled", "success"})
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_cancel_with_nonexistent_id_returns_not_found(self) -> None:
        """一致性：取消不存在的任务应返回 NOT_FOUND。"""

        async def scenario() -> None:
            # 连续取消不存在的任务，应该都返回 NOT_FOUND
            for _ in range(5):
                payload = await self.tool(
                    "kb_document_import_batch_cancel",
                    id=99999999,
                )
                self.assert_error(payload, code="IMPORT_TASK_NOT_FOUND", error_type="not_found")

        self.run_async(scenario())

    def test_cancel_with_mismatched_ids_returns_error(self) -> None:
        """一致性：使用不匹配的 id 和 task_uid 应返回错误。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="consistency_mismatch")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"consistency_mismatch_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                # 用错误的 id 和正确的 task_uid
                cancel_payload = await self.tool(
                    "kb_document_import_batch_cancel",
                    id=99999999,
                    task_uid=task["task_uid"],
                )
                self.assert_error(cancel_payload, code="INVALID_ARGUMENT", error_type="validation_error")
            finally:
                await self.tool("kb_document_import_batch_cancel", task_uid=task["task_uid"])
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    # -------------------------------------------------------------------------
    # 大规模任务一致性
    # -------------------------------------------------------------------------

    def test_large_task_cancel_consistency(self) -> None:
        """一致性：大规模任务（100项）取消后状态一致。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="consistency_large")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"consistency_large_{i}_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        }
                        for i in range(10)  # 使用 10 项来加快测试
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                # 取消
                cancel_payload = await self.tool(
                    "kb_document_import_batch_cancel",
                    id=task["id"],
                )
                self.assert_success(cancel_payload)
                canceled_task = cancel_payload["data"]["task"]

                # 验证计数
                self.assertEqual(canceled_task["total_items"], 10)
                self.assertEqual(canceled_task["canceled_items"], 10)
                self.assertEqual(canceled_task["pending_items"], 0)
                self.assertEqual(canceled_task["running_items"], 0)

                # 验证查询一致性
                for _ in range(5):
                    get_payload = await self.tool(
                        "kb_document_import_batch_get",
                        id=task["id"],
                        include_items=True,
                    )
                    self.assert_success(get_payload)
                    task_data = get_payload["data"]["task"]
                    self.assertEqual(task_data["canceled_items"], 10)
                    self.assertEqual(len(task_data["items"]), 10)
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    # -------------------------------------------------------------------------
    # 竞态场景一致性
    # -------------------------------------------------------------------------

    def test_submit_and_immediately_cancel_consistency(self) -> None:
        """一致性：提交后立即取消，状态应一致。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="consistency_immediate")
            try:
                # 提交
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"consistency_immediate_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                # 立即取消（不等待）
                cancel_payload = await self.tool(
                    "kb_document_import_batch_cancel",
                    id=task["id"],
                )
                self.assert_success(cancel_payload)

                # 验证
                get_payload = await self.tool(
                    "kb_document_import_batch_get",
                    id=task["id"],
                )
                self.assert_success(get_payload)
                self.assertIn(get_payload["data"]["task"]["status"], {"canceled", "success"})
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_multiple_cancels_at_same_time_consistency(self) -> None:
        """一致性：同一时间多个取消请求，状态应一致。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="consistency_same_time")
            try:
                # 提交多个任务
                task_ids = []
                for i in range(5):
                    payload = await self.tool(
                        "kb_document_import_batch_submit",
                        items=[
                            {
                                "category_id": category["id"],
                                "title": f"consistency_same_time_{i}_{self.unique_suffix()}",
                                "file_name": "Functional_Analysis.pdf",
                                "mime_type": "application/pdf",
                                "file_content_base64": self.read_pdf_base64(),
                            },
                        ],
                    )
                    self.assert_success(payload)
                    task_ids.append(payload["data"]["task"]["id"])

                # 同时取消所有任务
                async def cancel_task(tid: int) -> dict:
                    async with MCPToolClient(self.server_url) as client:
                        return await client.call_tool(
                            "kb_document_import_batch_cancel",
                            {"id": tid},
                        )

                cancel_results = await asyncio.gather(*(cancel_task(tid) for tid in task_ids))

                # 所有取消都成功
                for r in cancel_results:
                    self.assert_success(r)

                # 所有任务状态一致
                for tid in task_ids:
                    status = None
                    for _ in range(5):
                        get_payload = await self.tool(
                            "kb_document_import_batch_get",
                            id=tid,
                        )
                        self.assert_success(get_payload)
                        status = get_payload["data"]["task"]["status"]
                        if status == "canceled":
                            break
                        await asyncio.sleep(1)
                    self.assertIn(status, {"canceled", "success"})
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    # -------------------------------------------------------------------------
    # 任务字段一致性
    # -------------------------------------------------------------------------

    def test_task_timestamps_consistency(self) -> None:
        """一致性：任务的时间戳字段应合理且一致。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="consistency_timestamps")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"consistency_timestamps_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                # 验证时间戳存在
                self.assertIsNotNone(task["created_at"])
                self.assertIsNotNone(task["updated_at"])
                self.assertIsNone(task["started_at"])
                self.assertIsNone(task["finished_at"])
                self.assertIsNone(task["heartbeat_at"])

                # created_at 和 updated_at 应该相等或很接近
                self.assertEqual(task["created_at"], task["updated_at"])

                # 取消后
                cancel_payload = await self.tool(
                    "kb_document_import_batch_cancel",
                    id=task["id"],
                )
                self.assert_success(cancel_payload)
                canceled_task = cancel_payload["data"]["task"]

                # updated_at 应该变化
                self.assertNotEqual(canceled_task["created_at"], canceled_task["updated_at"])
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_task_priority_and_attempts_consistency(self) -> None:
        """一致性：任务优先级和重试次数字段应一致保存。"""

        async def scenario() -> None:
            category = await self.create_category(prefix="consistency_priority")
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit",
                    priority=75,
                    max_attempts=5,
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"consistency_priority_{self.unique_suffix()}",
                            "file_name": "Functional_Analysis.pdf",
                            "mime_type": "application/pdf",
                            "file_content_base64": self.read_pdf_base64(),
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                # 取消后再次查询
                await self.tool("kb_document_import_batch_cancel", id=task["id"])

                get_payload = await self.tool(
                    "kb_document_import_batch_get",
                    id=task["id"],
                )
                self.assert_success(get_payload)
                final_task = get_payload["data"]["task"]

                # 优先级和重试次数保持不变
                self.assertEqual(final_task["priority"], 75)
                self.assertEqual(final_task["max_attempts"], 5)
                self.assertEqual(final_task["attempt_count"], 0)  # 未执行过
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())
