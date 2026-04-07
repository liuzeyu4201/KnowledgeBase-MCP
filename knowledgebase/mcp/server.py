from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from knowledgebase.app.config import get_settings
from knowledgebase.db.bootstrap import init_schema
from knowledgebase.mcp.tools.category_tools import register_category_tools
from knowledgebase.mcp.tools.document_tools import register_document_tools
from knowledgebase.mcp.tools.search_tools import register_search_tools

settings = get_settings()
mcp = FastMCP(
    settings.app_name,
    host=settings.mcp_host,
    port=settings.mcp_port,
    streamable_http_path=settings.mcp_path,
)

register_category_tools(mcp)
register_document_tools(mcp)
register_search_tools(mcp)


def run() -> None:
    """启动 MCP Server，并在需要时初始化数据库表结构。"""

    if settings.auto_init_schema:
        # 第一阶段采用自动建表，便于本地开发快速启动。
        init_schema()

    # 容器化部署优先使用 HTTP 传输，本地命令行调试仍可继续使用 stdio。
    if settings.mcp_transport == "stdio":
        mcp.run()
        return

    mcp.run(transport=settings.mcp_transport)
