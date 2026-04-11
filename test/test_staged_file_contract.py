from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import knowledgebase.db.bootstrap  # noqa: F401

from knowledgebase.db.session import SessionFactory
from knowledgebase.repositories.staged_file_repository import StagedFileRepository
from knowledgebase.services.staged_file_service import StagedFileService

from test.base import MCPIntegrationTestCase


class StagedFileContractTestCase(MCPIntegrationTestCase):
    """覆盖暂存文件上传接口和 from_staged MCP 主链路。"""

    def test_staged_file_http_upload_and_mcp_manage_smoke(self) -> None:
        async def scenario() -> None:
            staged_file = self.upload_staged_file(
                file_name="staged-smoke.md",
                file_bytes=self.read_markdown_bytes(title="Staged Smoke"),
                mime_type="text/markdown",
            )
            self.assertEqual(staged_file["status"], "uploaded")
            self.assertEqual(staged_file["source_type"], "md")
            self.assertEqual(staged_file["storage_backend"], "minio")
            self.assertTrue(staged_file["storage_uri"].startswith("s3://"))
            self.assert_storage_uri_exists(staged_file["storage_uri"])

            get_payload = await self.tool("kb_staged_file_get", id=staged_file["id"])
            self.assert_success(get_payload)
            self.assertEqual(get_payload["data"]["staged_file"]["id"], staged_file["id"])

            list_payload = await self.tool(
                "kb_staged_file_list",
                status="uploaded",
                page=1,
                page_size=20,
            )
            self.assert_success(list_payload)
            ids = [item["id"] for item in list_payload["data"]["items"]]
            self.assertIn(staged_file["id"], ids)

            delete_payload = await self.tool("kb_staged_file_delete", id=staged_file["id"])
            self.assert_success(delete_payload)
            self.assertEqual(delete_payload["data"]["staged_file"]["status"], "deleted")
            self.wait_for_storage_uri_deleted(staged_file["storage_uri"])

        self.run_async(scenario())

    def test_staged_file_upload_rejects_invalid_mime(self) -> None:
        payload = self.http_json(
            "POST",
            "/api/staged-files",
            files={
                "file": ("invalid.txt", b"plain text", "text/plain"),
            },
        )
        self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")

    def test_document_import_from_staged_smoke(self) -> None:
        async def scenario() -> None:
            category = await self.create_category(prefix="staged_import")
            staged_file = self.upload_staged_file(
                file_name="Functional_Analysis.pdf",
                file_bytes=self.read_pdf_bytes(),
                mime_type="application/pdf",
            )
            self.assert_storage_uri_exists(staged_file["storage_uri"])
            document = None
            try:
                payload = await self.tool(
                    "kb_document_import_from_staged",
                    category_id=category["id"],
                    title=f"staged_import_{self.unique_suffix()}",
                    staged_file_id=staged_file["id"],
                )
                self.assert_success(payload)
                document = payload["data"]["document"]
                self.assertGreaterEqual(document["chunk_count"], 1)

                staged_get_payload = await self.tool("kb_staged_file_get", id=staged_file["id"])
                self.assert_success(staged_get_payload)
                self.assertEqual(staged_get_payload["data"]["staged_file"]["status"], "consumed")
                self.assertEqual(
                    staged_get_payload["data"]["staged_file"]["linked_document_id"],
                    document["id"],
                )
                self.assert_storage_uri_exists(document["storage_uri"])
                self.wait_for_storage_uri_deleted(staged_file["storage_uri"])
            finally:
                if document is not None:
                    await self.delete_document_best_effort(document)
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_document_update_from_staged_rebuilds_document(self) -> None:
        async def scenario() -> None:
            category = await self.create_category(prefix="staged_update")
            document = await self.import_document(
                category_id=category["id"],
                title_prefix="staged_update_before",
                file_name="before.md",
                mime_type="text/markdown",
                file_content_base64=self.read_markdown_base64(title="Before Staged Update"),
            )
            old_storage_uri = document["storage_uri"]
            staged_file = self.upload_staged_file(
                file_name="after.docx",
                file_bytes=self.read_docx_bytes(title="After Staged Update"),
                mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            try:
                payload = await self.tool(
                    "kb_document_update_from_staged",
                    id=document["id"],
                    title="staged_update_after",
                    staged_file_id=staged_file["id"],
                )
                self.assert_success(payload)
                updated = payload["data"]["document"]
                self.assertEqual(updated["title"], "staged_update_after")
                self.assertEqual(
                    updated["mime_type"],
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
                self.assertEqual(updated["source_type"], "docx")
                self.assertEqual(updated["version"], 2)
                self.assert_storage_uri_exists(updated["storage_uri"])
                self.wait_for_storage_uri_deleted(old_storage_uri)
                self.wait_for_storage_uri_deleted(staged_file["storage_uri"])
            finally:
                await self.delete_document_best_effort(document)
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_staged_file_delete_rejects_consumed_file(self) -> None:
        async def scenario() -> None:
            category = await self.create_category(prefix="staged_consumed_guard")
            staged_file = self.upload_staged_file(
                file_name="notes.md",
                file_bytes=self.read_markdown_bytes(title="Consumed Guard"),
                mime_type="text/markdown",
            )
            document = None
            try:
                payload = await self.tool(
                    "kb_document_import_from_staged",
                    category_id=category["id"],
                    title=f"consumed_guard_{self.unique_suffix()}",
                    staged_file_id=staged_file["id"],
                )
                self.assert_success(payload)
                document = payload["data"]["document"]

                delete_payload = await self.tool("kb_staged_file_delete", id=staged_file["id"])
                self.assert_error(
                    delete_payload,
                    code="STAGED_FILE_STATUS_INVALID",
                    error_type="business_error",
                )
            finally:
                if document is not None:
                    await self.delete_document_best_effort(document)
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_batch_submit_from_staged_smoke(self) -> None:
        async def scenario() -> None:
            category = await self.create_category(prefix="batch_staged")
            staged_pdf = self.upload_staged_file(
                file_name="Functional_Analysis.pdf",
                file_bytes=self.read_pdf_bytes(),
                mime_type="application/pdf",
            )
            staged_md = self.upload_staged_file(
                file_name="batch-staged.md",
                file_bytes=self.read_markdown_bytes(title="Batch Staged Markdown"),
                mime_type="text/markdown",
            )
            try:
                payload = await self.tool(
                    "kb_document_import_batch_submit_from_staged",
                    items=[
                        {
                            "category_id": category["id"],
                            "title": f"batch_staged_pdf_{self.unique_suffix()}",
                            "staged_file_id": staged_pdf["id"],
                        },
                        {
                            "category_id": category["id"],
                            "title": f"batch_staged_md_{self.unique_suffix()}",
                            "staged_file_id": staged_md["id"],
                        },
                    ],
                )
                self.assert_success(payload)
                task = payload["data"]["task"]

                final_status = task["status"]
                for _ in range(40):
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
                self.assertEqual(len(items), 2)
                self.assertTrue(all(item["status"] == "success" for item in items))
                self.assertTrue(all(item["staged_file_id"] for item in items))
            finally:
                await self.delete_documents_by_category_best_effort(category_id=category["id"])
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_expired_uploaded_staged_file_is_cleaned(self) -> None:
        staged_file = self.upload_staged_file(
            file_name="expired-cleanup.md",
            file_bytes=self.read_markdown_bytes(title="Expired Cleanup"),
            mime_type="text/markdown",
        )
        self.assert_storage_uri_exists(staged_file["storage_uri"])

        session = SessionFactory()
        try:
            repository = StagedFileRepository(session)
            model = repository.get_by_id(staged_file["id"])
            self.assertIsNotNone(model)
            assert model is not None
            model.expires_at = datetime.utcnow() - timedelta(minutes=10)
            session.add(model)
            session.commit()
        finally:
            session.close()

        session = SessionFactory()
        try:
            repository = StagedFileRepository(session)
            claimed = repository.claim_next_expired_for_cleanup(staged_file_id=staged_file["id"])
            self.assertIsNotNone(claimed)
            assert claimed is not None
            self.assertEqual(claimed.status, "expired")

            service = StagedFileService(repository)
            service.delete_staged_file_by_id(staged_file["id"])
            session.commit()
        finally:
            session.close()

        self.wait_for_storage_uri_deleted(staged_file["storage_uri"])
        session = SessionFactory()
        try:
            repository = StagedFileRepository(session)
            deleted = repository.get_by_id(staged_file["id"], include_deleted=True)
            self.assertIsNotNone(deleted)
            assert deleted is not None
            self.assertEqual(deleted.status, "deleted")
            self.assertIsNotNone(deleted.deleted_at)
        finally:
            session.close()

    def test_consuming_staged_file_is_not_cleaned_by_expired_sweep(self) -> None:
        staged_file = self.upload_staged_file(
            file_name="consuming-guard.md",
            file_bytes=self.read_markdown_bytes(title="Consuming Guard"),
            mime_type="text/markdown",
        )
        self.assert_storage_uri_exists(staged_file["storage_uri"])

        session = SessionFactory()
        try:
            repository = StagedFileRepository(session)
            model = repository.get_by_id(staged_file["id"])
            self.assertIsNotNone(model)
            assert model is not None
            repository.mark_consuming(model)
            model.expires_at = datetime.utcnow() - timedelta(minutes=10)
            session.add(model)
            session.commit()
        finally:
            session.close()

        session = SessionFactory()
        try:
            repository = StagedFileRepository(session)
            claimed = repository.claim_next_expired_for_cleanup(staged_file_id=staged_file["id"])
            self.assertIsNone(claimed)
        finally:
            session.close()

        self.assert_storage_uri_exists(staged_file["storage_uri"])

        session = SessionFactory()
        try:
            repository = StagedFileRepository(session)
            model = repository.get_by_id(staged_file["id"])
            self.assertIsNotNone(model)
            assert model is not None
            repository.mark_expired(model)
            service = StagedFileService(repository)
            service.delete_staged_file_by_id(staged_file["id"])
            session.commit()
        finally:
            session.close()

        self.wait_for_storage_uri_deleted(staged_file["storage_uri"])
