from __future__ import annotations

from sqlalchemy import text

from knowledgebase.db.base import Base
from knowledgebase.db.session import engine
from knowledgebase.models import category, chunk, document, import_task, staged_file, storage_gc_task  # noqa: F401

_CATEGORY_INDEX_LOCK_KEY = 2026041201
_CATEGORY_INDEX_DEFINITIONS = {
    "ix_kb_category_category_code": (
        "CREATE UNIQUE INDEX ix_kb_category_category_code "
        "ON kb_category USING btree (category_code) WHERE deleted_at IS NULL"
    ),
    "ix_kb_category_name": (
        "CREATE UNIQUE INDEX ix_kb_category_name "
        "ON kb_category USING btree (name) WHERE deleted_at IS NULL"
    ),
}


def init_schema() -> None:
    """初始化数据库表结构。"""

    # 导入模型模块以确保所有表都已注册到 SQLAlchemy 元数据中。
    Base.metadata.create_all(bind=engine)
    _reconcile_postgresql_category_indexes()


def _reconcile_postgresql_category_indexes() -> None:
    """把分类唯一索引收敛为仅对未删除记录生效，兼容历史库结构。"""

    if engine.dialect.name != "postgresql":
        return

    with engine.begin() as connection:
        connection.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": _CATEGORY_INDEX_LOCK_KEY},
        )
        existing_index_defs = {
            row.indexname: row.indexdef
            for row in connection.execute(
                text(
                    """
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE schemaname = current_schema()
                      AND tablename = 'kb_category'
                    """
                )
            )
        }

        for index_name, create_sql in _CATEGORY_INDEX_DEFINITIONS.items():
            current_definition = existing_index_defs.get(index_name)
            if _is_expected_partial_unique_index(current_definition, index_name=index_name):
                continue
            connection.execute(text(f'DROP INDEX IF EXISTS "{index_name}"'))
            connection.execute(text(create_sql))


def _is_expected_partial_unique_index(index_definition: str | None, *, index_name: str) -> bool:
    """判断分类唯一索引是否已经是目标的软删除友好结构。"""

    if not index_definition:
        return False

    normalized = " ".join(index_definition.lower().split())
    return (
        f"create unique index {index_name.lower()}" in normalized
        and "where" in normalized
        and "deleted_at is null" in normalized
    )
