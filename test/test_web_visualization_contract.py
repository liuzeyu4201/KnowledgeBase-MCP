from __future__ import annotations

from unittest import mock

from fastapi.testclient import TestClient

from knowledgebase.mcp.server import create_http_app
from test.base import MCPIntegrationTestCase


class WebVisualizationContractTestCase(MCPIntegrationTestCase):
    """验证知识库可视化网页模块对 MCP 数据的聚合与展示。"""

    def test_home_page_and_categories_api(self) -> None:
        async def scenario() -> tuple[int, str, dict]:
            category = await self.create_category(prefix="visual_home")
            await self.import_document(
                category_id=category["id"],
                title_prefix="visual_home_doc",
                file_name="visual-home.md",
                mime_type="text/markdown",
                file_content_base64=self.read_markdown_base64(title="Visual Home"),
            )
            payload = self.http_json("GET", "/api/visualization/categories", params={"page": 1, "page_size": 50})
            status_code, html = self.http_text("GET", "/ui")
            return status_code, html, payload

        status_code, html, payload = self.run_async(scenario())
        self.assertEqual(status_code, 200)
        self.assertIn("知识库分类总览", html)
        self.assert_success(payload)

        items = payload["data"]["items"]
        matched = [item for item in items if item["category_code"].startswith("visual_home_")]
        self.assertTrue(matched, payload)
        self.assertGreaterEqual(matched[0]["document_count"], 1, payload)

    def test_categories_api_supports_keyword_filter(self) -> None:
        async def scenario() -> dict:
            category = await self.create_category(prefix="visual_filter")
            return self.http_json(
                "GET",
                "/api/visualization/categories",
                params={"name": category["name"], "page": 1, "page_size": 20},
            )

        payload = self.run_async(scenario())
        self.assert_success(payload)
        self.assertEqual(payload["data"]["pagination"]["total"], 1, payload)

    def test_categories_api_supports_keyword_for_name_and_code(self) -> None:
        async def scenario() -> tuple[dict, dict]:
            category_payload = await self.tool("kb_category_get", category_code="math")
            self.assert_success(category_payload)
            by_name = self.http_json(
                "GET",
                "/api/visualization/categories",
                params={"keyword": "数学", "page": 1, "page_size": 20},
            )
            by_code = self.http_json(
                "GET",
                "/api/visualization/categories",
                params={"keyword": "math", "page": 1, "page_size": 20},
            )
            return by_name, by_code

        by_name, by_code = self.run_async(scenario())
        self.assert_success(by_name)
        self.assertTrue(by_name["data"]["items"], by_name)
        self.assertIn(
            "math",
            {item["category_code"] for item in by_name["data"]["items"]},
            by_name,
        )
        self.assert_success(by_code)
        self.assertTrue(by_code["data"]["items"], by_code)
        self.assertIn(
            "math",
            {item["category_code"] for item in by_code["data"]["items"]},
            by_code,
        )

    def test_category_documents_page_and_api(self) -> None:
        async def scenario() -> tuple[int, str, dict, dict]:
            category = await self.create_category(prefix="visual_docs")
            document = await self.import_document(
                category_id=category["id"],
                title_prefix="visual_docs_doc",
                file_name="visual-docs.docx",
                mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                file_content_base64=self.read_docx_base64(title="Visual Docs"),
            )
            payload = self.http_json(
                "GET",
                f"/api/visualization/categories/{category['id']}/documents",
                params={"page": 1, "page_size": 50},
            )
            status_code, html = self.http_text("GET", f"/ui/categories/{category['id']}")
            return status_code, html, payload, document

        status_code, html, payload, document = self.run_async(scenario())
        self.assertEqual(status_code, 200)
        self.assertIn("分类文档列表", html)
        self.assert_success(payload)
        self.assertEqual(payload["data"]["pagination"]["total"], 1, payload)
        self.assertEqual(payload["data"]["items"][0]["id"], document["id"], payload)

    def test_document_content_page_and_api(self) -> None:
        async def scenario() -> tuple[int, str, dict, dict]:
            category = await self.create_category(prefix="visual_doc_content")
            document = await self.import_document(
                category_id=category["id"],
                title_prefix="visual_doc_content_doc",
                file_name="visual-doc-content.md",
                mime_type="text/markdown",
                file_content_base64=self.read_markdown_base64(title="Visual Content"),
            )
            payload = self.http_json(
                "GET",
                f"/api/visualization/documents/{document['id']}/content",
                params={"source_page": 1, "source_page_size": 1, "chunk_page": 1, "chunk_page_size": 1},
            )
            status_code, html = self.http_text("GET", f"/ui/documents/{document['id']}")
            return status_code, html, payload, document

        status_code, html, payload, document = self.run_async(scenario())
        self.assertEqual(status_code, 200)
        self.assertIn("文档原文详情", html)
        self.assert_success(payload)
        self.assertEqual(payload["data"]["document"]["id"], document["id"], payload)
        self.assertGreaterEqual(len(payload["data"]["source_pages"]), 1, payload)
        self.assertEqual(payload["data"]["source_pagination"]["page_size"], 1, payload)

    def test_document_chunk_page_and_api(self) -> None:
        async def scenario() -> tuple[int, str, dict, dict]:
            category = await self.create_category(prefix="visual_doc_chunks")
            document = await self.import_document(
                category_id=category["id"],
                title_prefix="visual_doc_chunks_doc",
                file_name="visual-doc-chunks.md",
                mime_type="text/markdown",
                file_content_base64=self.read_markdown_base64(title="Visual Chunks"),
            )
            payload = self.http_json(
                "GET",
                f"/api/visualization/documents/{document['id']}/chunks",
                params={"chunk_page": 1, "chunk_page_size": 1},
            )
            status_code, html = self.http_text("GET", f"/ui/documents/{document['id']}/chunks")
            return status_code, html, payload, document

        status_code, html, payload, document = self.run_async(scenario())
        self.assertEqual(status_code, 200)
        self.assertIn("文档 Chunk 原文", html)
        self.assert_success(payload)
        self.assertEqual(payload["data"]["document"]["id"], document["id"], payload)
        self.assertEqual(len(payload["data"]["chunks"]), 1, payload)
        self.assertEqual(payload["data"]["chunk_pagination"]["page_size"], 1, payload)

    def test_visual_document_delete_api(self) -> None:
        async def scenario() -> tuple[dict, dict]:
            category = await self.create_category(prefix="visual_delete_doc")
            document = await self.import_document(
                category_id=category["id"],
                title_prefix="visual_delete_doc",
                file_name="visual-delete-doc.md",
                mime_type="text/markdown",
                file_content_base64=self.read_markdown_base64(title="Delete Doc"),
            )
            payload = self.http_json("DELETE", f"/api/visualization/documents/{document['id']}")
            list_payload = self.http_json(
                "GET",
                f"/api/visualization/categories/{category['id']}/documents",
                params={"page": 1, "page_size": 20},
            )
            return payload, list_payload

        payload, list_payload = self.run_async(scenario())
        self.assert_success(payload)
        self.assertTrue(payload["data"]["deleted"], payload)
        self.assert_success(list_payload)
        self.assertEqual(list_payload["data"]["pagination"]["total"], 0, list_payload)

    def test_visual_category_delete_api_requires_empty_documents(self) -> None:
        async def scenario() -> tuple[dict, dict]:
            category = await self.create_category(prefix="visual_delete_category")
            document = await self.import_document(
                category_id=category["id"],
                title_prefix="visual_delete_category_doc",
                file_name="visual-delete-category.md",
                mime_type="text/markdown",
                file_content_base64=self.read_markdown_base64(title="Delete Category"),
            )
            blocked_payload = self.http_json("DELETE", f"/api/visualization/categories/{category['id']}")
            deleted_document_payload = self.http_json("DELETE", f"/api/visualization/documents/{document['id']}")
            delete_payload = self.http_json("DELETE", f"/api/visualization/categories/{category['id']}")
            return blocked_payload, deleted_document_payload, delete_payload

        blocked_payload, deleted_document_payload, delete_payload = self.run_async(scenario())
        self.assert_error(blocked_payload, code="CATEGORY_HAS_DOCUMENTS", error_type="business_error")
        self.assert_success(deleted_document_payload)
        self.assert_success(delete_payload)

    def test_category_documents_api_supports_title_filter(self) -> None:
        async def scenario() -> tuple[dict, dict]:
            category = await self.create_category(prefix="visual_docs_filter")
            document = await self.import_document(
                category_id=category["id"],
                title_prefix="visual_docs_filter_doc",
                file_name="visual-docs-filter.md",
                mime_type="text/markdown",
                file_content_base64=self.read_markdown_base64(title="Visual Filter"),
            )
            payload = self.http_json(
                "GET",
                f"/api/visualization/categories/{category['id']}/documents",
                params={"title": document["title"], "page": 1, "page_size": 20},
            )
            return payload, document

        payload, document = self.run_async(scenario())
        self.assert_success(payload)
        self.assertEqual(payload["data"]["pagination"]["total"], 1, payload)
        self.assertEqual(payload["data"]["items"][0]["id"], document["id"], payload)

    def test_import_task_visualization_api(self) -> None:
        async def scenario() -> dict:
            category = await self.create_category(prefix="visual_task")
            task_payload = await self.submit_batch_import_task(
                items=[
                    {
                        "category_id": category["id"],
                        "title": "visual_task_doc",
                        "file_name": "visual-task.md",
                        "mime_type": "text/markdown",
                        "file_content_base64": self.read_markdown_base64(title="Visual Task"),
                    }
                ]
            )
            self.assert_success(task_payload)
            task_id = task_payload["data"]["task"]["id"]
            return self.http_json("GET", f"/api/visualization/import-tasks/{task_id}")

        payload = self.run_async(scenario())
        self.assert_success(payload)
        self.assertIn("task", payload["data"], payload)
        self.assertIn("items", payload["data"], payload)


class WebVisualizationWebSocketTestCase(MCPIntegrationTestCase):
    """验证任务状态 WebSocket 推送逻辑。"""

    def test_task_websocket_pushes_terminal_state(self) -> None:
        class FakeGateway:
            def __init__(self, *args, **kwargs) -> None:
                self.calls = 0

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def get_import_task(self, payload):
                self.calls += 1
                status = "running" if self.calls == 1 else "success"
                return {
                    "success": True,
                    "data": {
                        "task": {
                            "id": payload["id"],
                            "status": status,
                            "success_items": 1 if status == "success" else 0,
                            "failed_items": 0,
                            "canceled_items": 0,
                        },
                        "items": [],
                    },
                }

        with mock.patch("knowledgebase.web.routes.MCPGateway", FakeGateway):
            app = create_http_app()
            with TestClient(app) as client:
                with client.websocket_connect("/ws/import-tasks/99") as websocket:
                    first = websocket.receive_json()
                    second = websocket.receive_json()

        self.assertEqual(first["data"]["task"]["status"], "running")
        self.assertEqual(second["data"]["task"]["status"], "success")
