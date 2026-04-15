from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from starlette.staticfiles import StaticFiles
from starlette.applications import Starlette

from knowledgebase.app.config import get_settings
from knowledgebase.db.bootstrap import init_schema
from knowledgebase.integrations.embedding.validator import validate_embedding_startup
from knowledgebase.http.staged_file_routes import router as staged_file_router
from knowledgebase.mcp.tools.category_tools import register_category_tools
from knowledgebase.mcp.tools.document_tools import register_document_tools
from knowledgebase.mcp.tools.import_task_tools import register_import_task_tools
from knowledgebase.mcp.tools.search_tools import register_search_tools
from knowledgebase.mcp.tools.staged_file_tools import register_staged_file_tools
from knowledgebase.web.middleware import RequestContextMiddleware
from knowledgebase.web.routes import STATIC_DIR, api_router, page_router, ws_router

settings = get_settings()


def create_mcp_server() -> FastMCP:
    """创建一份新的 FastMCP 实例，避免测试场景复用同一个 lifespan 对象。"""

    mcp = FastMCP(
        settings.app_name,
        host=settings.mcp_host,
        port=settings.mcp_port,
        streamable_http_path=settings.mcp_path,
    )
    register_category_tools(mcp)
    register_document_tools(mcp)
    register_import_task_tools(mcp)
    register_search_tools(mcp)
    register_staged_file_tools(mcp)
    return mcp


def create_http_app(*, mcp_server: FastMCP | None = None) -> Starlette:
    """创建统一 HTTP 应用，复用 FastMCP 内置 lifespan 后再挂接上传子应用。"""

    mcp_app = (mcp_server or create_mcp_server()).streamable_http_app()
    upload_app = FastAPI(title=f"{settings.app_name} Upload API")
    upload_app.add_middleware(RequestContextMiddleware)

    @upload_app.get("/healthz")
    def healthz() -> dict[str, str]:
        """提供容器级健康检查端点，仅在应用启动完成后返回成功。"""

        return {"status": "ok"}

    upload_app.include_router(staged_file_router)
    upload_app.include_router(page_router)
    upload_app.include_router(api_router)
    upload_app.include_router(ws_router)
    upload_app.mount("/assets", StaticFiles(directory=str(STATIC_DIR)), name="visual-assets")
    mcp_app.mount("/", upload_app)
    return mcp_app


def run() -> None:
    """启动 MCP Server，并在需要时初始化数据库表结构。"""

    if settings.auto_init_schema:
        # 第一阶段采用自动建表，便于本地开发快速启动。
        init_schema()

    validate_embedding_startup()

    mcp_server = create_mcp_server()

    # 容器化部署优先使用 HTTP 传输，本地命令行调试仍可继续使用 stdio。
    if settings.mcp_transport == "stdio":
        mcp_server.run()
        return

    http_app = create_http_app(mcp_server=mcp_server)
    uvicorn.run(
        http_app,
        host=settings.mcp_host,
        port=settings.mcp_port,
        log_level="info",
    )


if __name__ == "__main__":
    run()
