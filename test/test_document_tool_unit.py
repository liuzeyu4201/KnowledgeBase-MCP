from __future__ import annotations

import unittest
from unittest import mock

from knowledgebase.mcp.tools import document_tools


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.closed = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True


class DocumentToolUnitTestCase(unittest.TestCase):
    """覆盖单文档导入工具的同步语义。"""

    def test_import_from_staged_executes_synchronously(self) -> None:
        session = _FakeSession()
        service = mock.Mock()
        service.import_document_from_staged.return_value = {
            "document": {
                "id": 1,
                "document_uid": "doc-1",
            }
        }

        with (
            mock.patch.object(document_tools, "SessionFactory", return_value=session),
            mock.patch.object(document_tools, "DocumentService", return_value=service),
            mock.patch.object(
                document_tools,
                "_execute_async_document_task",
                side_effect=AssertionError("import_from_staged should not submit async task"),
            ),
        ):
            payload = document_tools._execute_write(
                {
                    "category_id": 1,
                    "title": "sync import",
                    "staged_file_id": 1,
                },
                action="import_from_staged",
            )

        self.assertTrue(payload["success"], payload)
        self.assertIn("document", payload["data"])
        self.assertNotIn("task", payload["data"])
        service.import_document_from_staged.assert_called_once()
        self.assertTrue(session.committed)
        self.assertTrue(session.closed)

    def test_import_from_staged_rejects_async_execution_mode(self) -> None:
        payload = document_tools._execute_write(
            {
                "category_id": 1,
                "title": "invalid async import",
                "staged_file_id": 1,
                "execution_mode": "async",
            },
            action="import_from_staged",
        )

        self.assertFalse(payload["success"], payload)
        self.assertEqual(payload["code"], "INVALID_ARGUMENT", payload)
        self.assertEqual(payload["error"]["type"], "validation_error", payload)


if __name__ == "__main__":
    unittest.main()
