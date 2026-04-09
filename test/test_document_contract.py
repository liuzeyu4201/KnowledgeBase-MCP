from __future__ import annotations

from test.base import MCPIntegrationTestCase


class DocumentContractTestCase(MCPIntegrationTestCase):
    """覆盖文档导入、查询、删除、更新与失败路径。"""

    def test_document_import_get_list_delete_smoke(self) -> None:
        async def scenario() -> None:
            category = await self.create_category(prefix="document_smoke")
            document = await self.import_document(
                category_id=category["id"],
                title_prefix="document_smoke",
            )
            try:
                get_payload = await self.tool("kb_document_get", id=document["id"])
                self.assert_success(get_payload)
                self.assertEqual(
                    get_payload["data"]["document"]["document_uid"],
                    document["document_uid"],
                )

                list_payload = await self.tool(
                    "kb_document_list",
                    category_id=category["id"],
                    page=1,
                    page_size=20,
                )
                self.assert_success(list_payload)
                self.assertGreaterEqual(list_payload["data"]["pagination"]["total"], 1)

                delete_payload = await self.tool("kb_document_delete", id=document["id"])
                self.assert_success(delete_payload)
                self.assertTrue(delete_payload["data"]["deleted"])

                not_found_payload = await self.tool("kb_document_get", id=document["id"])
                self.assert_error(not_found_payload, code="DOCUMENT_NOT_FOUND", error_type="not_found")
            finally:
                await self.delete_document_best_effort(document)
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_document_import_markdown_smoke(self) -> None:
        async def scenario() -> None:
            category = await self.create_category(prefix="document_markdown")
            document = await self.import_document(
                category_id=category["id"],
                title_prefix="document_markdown",
                file_name="notes.md",
                mime_type="text/markdown",
                file_content_base64=self.read_markdown_base64(title="Markdown Import"),
            )
            try:
                self.assertEqual(document["mime_type"], "text/markdown")
                self.assertEqual(document["source_type"], "md")
                self.assertGreaterEqual(document["chunk_count"], 1)

                get_payload = await self.tool("kb_document_get", id=document["id"])
                self.assert_success(get_payload)
                self.assertEqual(get_payload["data"]["document"]["source_type"], "md")
            finally:
                await self.delete_document_best_effort(document)
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_document_import_docx_smoke(self) -> None:
        async def scenario() -> None:
            category = await self.create_category(prefix="document_docx")
            document = await self.import_document(
                category_id=category["id"],
                title_prefix="document_docx",
                file_name="notes.docx",
                mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                file_content_base64=self.read_docx_base64(title="Docx Import"),
            )
            try:
                self.assertEqual(
                    document["mime_type"],
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
                self.assertEqual(document["source_type"], "docx")
                self.assertGreaterEqual(document["chunk_count"], 1)

                get_payload = await self.tool("kb_document_get", id=document["id"])
                self.assert_success(get_payload)
                self.assertEqual(get_payload["data"]["document"]["source_type"], "docx")
            finally:
                await self.delete_document_best_effort(document)
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_document_import_rejects_invalid_category(self) -> None:
        async def scenario() -> None:
            staged_file = self.upload_staged_file(
                file_name="Functional_Analysis.pdf",
                file_bytes=self.read_pdf_bytes(),
                mime_type="application/pdf",
            )
            payload = await self.tool(
                "kb_document_import_from_staged",
                category_id=99999999,
                title="document_invalid_category",
                staged_file_id=staged_file["id"],
            )
            self.assert_error(payload, code="CATEGORY_NOT_FOUND", error_type="not_found")

        self.run_async(scenario())

    def test_document_import_from_staged_rejects_missing_staged_file(self) -> None:
        async def scenario() -> None:
            category = await self.create_category(prefix="document_missing_staged")
            try:
                payload = await self.tool(
                    "kb_document_import_from_staged",
                    category_id=category["id"],
                    title="missing_staged_case",
                    staged_file_id=99999999,
                )
                self.assert_error(payload, code="STAGED_FILE_NOT_FOUND", error_type="not_found")
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_document_upload_rejects_invalid_mime_type(self) -> None:
        async def scenario() -> None:
            payload = self.http_json(
                "POST",
                "/api/staged-files",
                files={
                    "file": ("Functional_Analysis.txt", self.read_pdf_bytes(), "text/plain"),
                },
            )
            self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")

        self.run_async(scenario())

    def test_category_delete_rejects_active_documents(self) -> None:
        async def scenario() -> None:
            category = await self.create_category(prefix="category_delete_guard")
            document = await self.import_document(category_id=category["id"], title_prefix="guard_doc")
            try:
                payload = await self.tool("kb_category_delete", id=category["id"])
                self.assert_error(payload, code="CATEGORY_HAS_DOCUMENTS", error_type="business_error")
            finally:
                await self.delete_document_best_effort(document)
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_document_update_metadata_only(self) -> None:
        async def scenario() -> None:
            source_category = await self.create_category(prefix="document_update_src")
            target_category = await self.create_category(prefix="document_update_dst")
            document = await self.import_document(
                category_id=source_category["id"],
                title_prefix="update_meta",
            )
            try:
                payload = await self.tool(
                    "kb_document_update_from_staged",
                    id=document["id"],
                    category_id=target_category["id"],
                    title="updated_document_title",
                )
                self.assert_success(payload)
                updated = payload["data"]["document"]
                self.assertEqual(updated["category_id"], target_category["id"])
                self.assertEqual(updated["title"], "updated_document_title")
            finally:
                await self.delete_document_best_effort(document)
                await self.delete_category_best_effort(source_category)
                await self.delete_category_best_effort(target_category)

        self.run_async(scenario())

    def test_document_update_replace_markdown_with_docx(self) -> None:
        async def scenario() -> None:
            category = await self.create_category(prefix="document_update_replace")
            document = await self.import_document(
                category_id=category["id"],
                title_prefix="update_replace",
                file_name="replace.md",
                mime_type="text/markdown",
                file_content_base64=self.read_markdown_base64(title="Before Replace"),
            )
            try:
                payload = await self.update_document(
                    document_id=document["id"],
                    file_name="replace.docx",
                    mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    file_content_base64=self.read_docx_base64(title="After Replace"),
                )
                self.assert_success(payload)
                updated = payload["data"]["document"]
                self.assertEqual(updated["mime_type"], "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                self.assertEqual(updated["source_type"], "docx")
                self.assertEqual(updated["version"], 2)
            finally:
                await self.delete_document_best_effort(document)
                await self.delete_category_best_effort(category)

        self.run_async(scenario())
