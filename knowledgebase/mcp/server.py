from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette

from knowledgebase.app.config import get_settings
from knowledgebase.db.bootstrap import init_schema
from knowledgebase.http.staged_file_routes import router as staged_file_router
from knowledgebase.mcp.tools.category_tools import register_category_tools
from knowledgebase.mcp.tools.document_tools import register_document_tools
from knowledgebase.mcp.tools.import_task_tools import register_import_task_tools
from knowledgebase.mcp.tools.search_tools import register_search_tools
from knowledgebase.mcp.tools.staged_file_tools import register_staged_file_tools

settings = get_settings()
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


def create_http_app() -> Starlette:
    """创建统一 HTTP 应用，复用 FastMCP 内置 lifespan 后再挂接上传子应用。"""

    mcp_app = mcp.streamable_http_app()
    upload_app = FastAPI(title=f"{settings.app_name} Upload API")
    upload_app.include_router(staged_file_router)
    mcp_app.mount("/", upload_app)
    return mcp_app


def run() -> None:
    """启动 MCP Server，并在需要时初始化数据库表结构。"""

    if settings.auto_init_schema:
        # 第一阶段采用自动建表，便于本地开发快速启动。
        init_schema()

    # 容器化部署优先使用 HTTP 传输，本地命令行调试仍可继续使用 stdio。
    if settings.mcp_transport == "stdio":
        mcp.run()
        return

    http_app = create_http_app()
    uvicorn.run(
        http_app,
        host=settings.mcp_host,
        port=settings.mcp_port,
        log_level="info",
    )
