from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from knowledgebase.models.category import CategoryModel
from knowledgebase.models.document import DocumentModel


class CategoryRepository:
    """分类数据访问层。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        category_code: str,
        name: str,
        description: str | None,
        status: int,
    ) -> CategoryModel:
        category = CategoryModel(
            category_code=category_code,
            name=name,
            description=description,
            status=status,
        )
        self.session.add(category)
        self.session.flush()
        self.session.refresh(category)
        return category

    def get_by_id(self, category_id: int) -> CategoryModel | None:
        stmt = select(CategoryModel).where(
            CategoryModel.id == category_id,
            CategoryModel.deleted_at.is_(None),
        )
        return self.session.scalar(stmt)

    def get_by_code(self, category_code: str) -> CategoryModel | None:
        stmt = select(CategoryModel).where(
            CategoryModel.category_code == category_code,
            CategoryModel.deleted_at.is_(None),
        )
        return self.session.scalar(stmt)

    def get_by_name(self, name: str) -> CategoryModel | None:
        stmt = select(CategoryModel).where(
            CategoryModel.name == name,
            CategoryModel.deleted_at.is_(None),
        )
        return self.session.scalar(stmt)

    def list(
        self,
        *,
        category_code: str | None,
        name: str | None,
        status: int | None,
        page: int,
        page_size: int,
    ) -> tuple[list[CategoryModel], int]:
        conditions = [CategoryModel.deleted_at.is_(None)]

        if category_code:
            conditions.append(CategoryModel.category_code.ilike(f"%{category_code}%"))
        if name:
            conditions.append(CategoryModel.name.ilike(f"%{name}%"))
        if status is not None:
            conditions.append(CategoryModel.status == status)

        data_stmt = (
            select(CategoryModel)
            .where(*conditions)
            .order_by(CategoryModel.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        count_stmt = select(func.count(CategoryModel.id)).where(*conditions)

        items = list(self.session.scalars(data_stmt).all())
        total = self.session.scalar(count_stmt) or 0
        return items, total

    def update(
        self,
        category: CategoryModel,
        *,
        category_code: str | None = None,
        name: str | None = None,
        description: str | None = None,
        status: int | None = None,
    ) -> CategoryModel:
        """更新分类实体，并返回最新状态。"""

        if category_code is not None:
            category.category_code = category_code
        if name is not None:
            category.name = name
        if description is not None:
            category.description = description
        if status is not None:
            category.status = status

        self.session.add(category)
        self.session.flush()
        self.session.refresh(category)
        return category

    def count_active_documents(self, category_id: int) -> int:
        """统计分类下未删除文档数量，用于删除前约束校验。"""

        stmt = select(func.count(DocumentModel.id)).where(
            DocumentModel.category_id == category_id,
            DocumentModel.deleted_at.is_(None),
        )
        return self.session.scalar(stmt) or 0

    def soft_delete(self, category: CategoryModel) -> CategoryModel:
        """对分类执行软删除。"""

        category.deleted_at = datetime.utcnow()
        self.session.add(category)
        self.session.flush()
        self.session.refresh(category)
        return category
