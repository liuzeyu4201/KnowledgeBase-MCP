from __future__ import annotations

import asyncio
from contextlib import contextmanager
import importlib
import socket
import threading
import time
import unittest
from unittest import mock

import httpx
import uvicorn

from test.mcp_test_client import MCPToolClient


@contextmanager
def run_test_server():
    """在后台线程启动临时 HTTP 服务，供并发回归测试复用。"""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    from knowledgebase.mcp import server as server_module

    app = importlib.reload(server_module).create_http_app()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.monotonic() + 5.0
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.05)

    if not server.started:
        server.should_exit = True
        thread.join(timeout=5)
        raise RuntimeError("test server failed to start")

    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=5)


class NonBlockingIOContractTestCase(unittest.TestCase):
    """验证慢速 MCP/HTTP 写入不再阻塞主服务事件循环。"""

    def test_slow_document_import_does_not_block_healthz(self) -> None:
        async def scenario() -> None:
            slow_started = threading.Event()

            def slow_execute_write(payload: dict, action: str = "import") -> dict:
                slow_started.set()
                time.sleep(1.0)
                return {
                    "success": True,
                    "code": "OK",
                    "message": "ok",
                    "data": {
                        "document": {
                            "id": 1,
                        }
                    },
                }

            with mock.patch(
                "knowledgebase.mcp.tools.document_tools._execute_write",
                side_effect=slow_execute_write,
            ):
                with run_test_server() as base_url:
                    async with MCPToolClient(f"{base_url}/mcp") as mcp_client:
                        async with httpx.AsyncClient(timeout=5.0) as client:
                            import_task = asyncio.create_task(
                                mcp_client.call_tool(
                                    "kb_document_import_from_staged",
                                    {
                                        "category_id": 1,
                                        "title": "slow import",
                                        "staged_file_id": 1,
                                    },
                                )
                            )
                            started = await asyncio.to_thread(slow_started.wait, 2.0)
                            self.assertTrue(started, "slow import did not start in time")

                            started_at = time.perf_counter()
                            response = await client.get(f"{base_url}/healthz")
                            duration = time.perf_counter() - started_at

                            payload = await import_task
                            self.assertTrue(payload["success"], payload)
                            self.assertEqual(response.status_code, 200)
                            self.assertLess(duration, 0.5, f"healthz blocked for {duration:.3f}s")

        asyncio.run(scenario())

    def test_slow_staged_upload_does_not_block_healthz(self) -> None:
        async def scenario() -> None:
            slow_started = threading.Event()

            def slow_create_response(**_: object) -> dict:
                slow_started.set()
                time.sleep(1.0)
                return {
                    "success": True,
                    "code": "OK",
                    "message": "ok",
                    "data": {
                        "staged_file": {
                            "id": 1,
                            "staged_file_uid": "test-staged-file-uid",
                            "status": "uploaded",
                            "storage_backend": "minio",
                            "storage_uri": "s3://bucket/object",
                            "file_name": "slow.md",
                            "mime_type": "text/markdown",
                            "source_type": "markdown",
                            "file_size": 8,
                            "file_sha256": "a" * 64,
                            "upload_completed_at": None,
                            "expires_at": None,
                            "consumed_at": None,
                            "last_error": None,
                            "linked_document_id": None,
                            "linked_task_id": None,
                            "created_at": "2026-04-12T00:00:00",
                            "updated_at": "2026-04-12T00:00:00",
                            "deleted_at": None,
                        }
                    },
                }

            with mock.patch(
                "knowledgebase.http.staged_file_routes._create_staged_file_response",
                side_effect=slow_create_response,
            ):
                with run_test_server() as base_url:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        upload_task = asyncio.create_task(
                            client.post(
                                f"{base_url}/api/staged-files",
                                files={"file": ("slow.md", b"# slow", "text/markdown")},
                            )
                        )
                        started = await asyncio.to_thread(slow_started.wait, 2.0)
                        self.assertTrue(started, "slow upload did not start in time")

                        started_at = time.perf_counter()
                        response = await client.get(f"{base_url}/healthz")
                        duration = time.perf_counter() - started_at

                        upload_response = await upload_task
                        self.assertEqual(upload_response.status_code, 200, upload_response.text)
                        self.assertEqual(response.status_code, 200)
                        self.assertLess(duration, 0.5, f"healthz blocked for {duration:.3f}s")

        asyncio.run(scenario())
