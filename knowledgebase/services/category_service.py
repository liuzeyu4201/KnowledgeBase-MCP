from __future__ import annotations

from pydantic import ValidationError

from knowledgebase.domain.exceptions import AppError
from knowledgebase.repositories.category_repository import CategoryRepository
from knowledgebase.schemas.category import (
    CategoryCreateInput,
    CategoryDeleteInput,
    CategoryGetInput,
    CategoryListInput,
    CategoryOutput,
    CategoryUpdateInput,
)


class CategoryService:
    """分类领域服务。"""

    def __init__(self, repository: CategoryRepository) -> None:
        self.repository = repository

    def create_category(self, payload: dict) -> CategoryOutput:
        """创建分类，并在落库前执行参数校验与唯一性校验。"""

        try:
            data = CategoryCreateInput.model_validate(payload)
        except ValidationError as exc:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="分类创建参数不合法",
                error_type="validation_error",
                details={"errors": exc.errors()},
            ) from exc

        # 先校验分类编码唯一性，避免写入阶段触发数据库唯一约束错误。
        if self.repository.get_by_code(data.category_code):
            raise AppError(
                code="CATEGORY_CODE_CONFLICT",
                message="category code already exists",
                error_type="business_error",
                details={"field": "category_code", "value": data.category_code},
            )

        # 分类名称作为业务标识之一，需要在服务层显式校验唯一性。
        if self.repository.get_by_name(data.name):
            raise AppError(
                code="CATEGORY_NAME_CONFLICT",
                message="category name already exists",
                error_type="business_error",
                details={"field": "name", "value": data.name},
            )

        category = self.repository.create(
            category_code=data.category_code,
            name=data.name,
            description=data.description,
            status=data.status,
        )
        return CategoryOutput.from_model(category)

    def get_category(self, payload: dict) -> CategoryOutput:
        """按主键或分类编码查询单个分类。"""

        try:
            data = CategoryGetInput.model_validate(payload)
        except ValidationError as exc:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="分类查询参数不合法",
                error_type="validation_error",
                details={"errors": exc.errors()},
            ) from exc

        if data.id is None and data.category_code is None:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="id or category_code is required",
                error_type="validation_error",
            )

        category = None
        if data.id is not None:
            category = self.repository.get_by_id(data.id)
        if data.category_code is not None:
            category_by_code = self.repository.get_by_code(data.category_code)
            if data.id is not None and category and category_by_code and category.id != category_by_code.id:
                raise AppError(
                    code="INVALID_ARGUMENT",
                    message="id and category_code do not match",
                    error_type="validation_error",
                )
            category = category_by_code or category

        if category is None:
            raise AppError(
                code="CATEGORY_NOT_FOUND",
                message="category not found",
                error_type="not_found",
                details={"id": data.id, "category_code": data.category_code},
            )

        return CategoryOutput.from_model(category)

    def list_categories(self, payload: dict) -> tuple[list[CategoryOutput], dict]:
        """按过滤条件分页查询分类列表。"""

        try:
            data = CategoryListInput.model_validate(payload)
        except ValidationError as exc:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="分类列表查询参数不合法",
                error_type="validation_error",
                details={"errors": exc.errors()},
            ) from exc

        items, total = self.repository.list(
            category_code=data.category_code,
            name=data.name,
            status=data.status,
            page=data.page,
            page_size=data.page_size,
        )
        outputs = [CategoryOutput.from_model(item) for item in items]
        pagination = {
            "page": data.page,
            "page_size": data.page_size,
            "total": total,
            "has_next": data.page * data.page_size < total,
        }
        return outputs, pagination

    def update_category(self, payload: dict) -> CategoryOutput:
        """更新分类，并校验目标存在性与唯一性约束。"""

        try:
            data = CategoryUpdateInput.model_validate(payload)
        except ValidationError as exc:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="分类更新参数不合法",
                error_type="validation_error",
                details={"errors": exc.errors()},
            ) from exc

        category = self._resolve_category(id=data.id, category_code=data.category_code)
        self._ensure_update_fields_present(data)

        if data.new_category_code and data.new_category_code != category.category_code:
            existing = self.repository.get_by_code(data.new_category_code)
            if existing and existing.id != category.id:
                raise AppError(
                    code="CATEGORY_CODE_CONFLICT",
                    message="category code already exists",
                    error_type="business_error",
                    details={"field": "new_category_code", "value": data.new_category_code},
                )

        if data.name and data.name != category.name:
            existing = self.repository.get_by_name(data.name)
            if existing and existing.id != category.id:
                raise AppError(
                    code="CATEGORY_NAME_CONFLICT",
                    message="category name already exists",
                    error_type="business_error",
                    details={"field": "name", "value": data.name},
                )

        # 更新操作集中在服务层进行字段决策，保证 repository 只负责持久化。
        updated = self.repository.update(
            category,
            category_code=data.new_category_code,
            name=data.name,
            description=data.description,
            status=data.status,
        )
        return CategoryOutput.from_model(updated)

    def delete_category(self, payload: dict) -> dict:
        """删除分类，当前采用软删除并校验是否仍有关联文档。"""

        try:
            data = CategoryDeleteInput.model_validate(payload)
        except ValidationError as exc:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="分类删除参数不合法",
                error_type="validation_error",
                details={"errors": exc.errors()},
            ) from exc

        category = self._resolve_category(id=data.id, category_code=data.category_code)

        # 删除前先校验文档归属，避免把仍在使用的分类直接软删除。
        active_document_count = self.repository.count_active_documents(category.id)
        if active_document_count > 0:
            raise AppError(
                code="CATEGORY_HAS_DOCUMENTS",
                message="category has active documents",
                error_type="business_error",
                details={"category_id": category.id, "document_count": active_document_count},
            )

        deleted = self.repository.soft_delete(category)
        return {
            "deleted": True,
            "category_id": deleted.id,
            "category_code": deleted.category_code,
            "deleted_at": deleted.deleted_at.isoformat() if deleted.deleted_at else None,
        }

    def _resolve_category(self, *, id: int | None, category_code: str | None):
        """按主键或分类编码解析目标分类。"""

        if id is None and category_code is None:
            raise AppError(
                code="INVALID_ARGUMENT",
                message="id or category_code is required",
                error_type="validation_error",
            )

        category = None
        if id is not None:
            category = self.repository.get_by_id(id)
        if category_code is not None:
            category_by_code = self.repository.get_by_code(category_code)
            if id is not None and category and category_by_code and category.id != category_by_code.id:
                raise AppError(
                    code="INVALID_ARGUMENT",
                    message="id and category_code do not match",
                    error_type="validation_error",
                )
            category = category_by_code or category

        if category is None:
            raise AppError(
                code="CATEGORY_NOT_FOUND",
                message="category not found",
                error_type="not_found",
                details={"id": id, "category_code": category_code},
            )

        return category

    def _ensure_update_fields_present(self, data: CategoryUpdateInput) -> None:
        """确保更新接口至少收到一个实际变更字段。"""

        if (
            data.new_category_code is None
            and data.name is None
            and data.description is None
            and data.status is None
        ):
            raise AppError(
                code="INVALID_ARGUMENT",
                message="at least one update field is required",
                error_type="validation_error",
            )
