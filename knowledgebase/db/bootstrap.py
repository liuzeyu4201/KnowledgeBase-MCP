from __future__ import annotations

from knowledgebase.db.base import Base
from knowledgebase.db.session import engine
from knowledgebase.models import chunk, document, category  # noqa: F401


def init_schema() -> None:
    """初始化数据库表结构。"""

    # 导入模型模块以确保所有表都已注册到 SQLAlchemy 元数据中。
    Base.metadata.create_all(bind=engine)
