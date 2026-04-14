from __future__ import annotations

from test.base import MCPIntegrationTestCase


class CategoryContractTestCase(MCPIntegrationTestCase):
    """覆盖分类接口的正常流程、边界输入与业务冲突场景。"""

    def test_category_crud_smoke(self) -> None:
        async def scenario() -> None:
            category = await self.create_category(prefix="category_smoke")

            get_payload = await self.tool("kb_category_get", id=category["id"])
            self.assert_success(get_payload)
            self.assertEqual(
                get_payload["data"]["category"]["category_code"],
                category["category_code"],
            )

            list_payload = await self.tool(
                "kb_category_list",
                category_code=category["category_code"],
                page=1,
                page_size=20,
            )
            self.assert_success(list_payload)
            self.assertEqual(list_payload["data"]["pagination"]["total"], 1)

            update_payload = await self.tool(
                "kb_category_update",
                id=category["id"],
                name=f"{category['name']}_updated",
                status=0,
            )
            self.assert_success(update_payload)
            self.assertEqual(update_payload["data"]["category"]["status"], 0)

            delete_payload = await self.tool("kb_category_delete", id=category["id"])
            self.assert_success(delete_payload)
            self.assertTrue(delete_payload["data"]["deleted"])

            not_found_payload = await self.tool("kb_category_get", id=category["id"])
            self.assert_error(not_found_payload, code="CATEGORY_NOT_FOUND", error_type="not_found")

        self.run_async(scenario())

    def test_category_create_rejects_invalid_code(self) -> None:
        async def scenario() -> None:
            payload = await self.tool(
                "kb_category_create",
                category_code="数学-分类",
                name="invalid_code_case",
                description="非法分类编码",
            )
            self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")

        self.run_async(scenario())

    def test_category_create_rejects_duplicate_code(self) -> None:
        async def scenario() -> None:
            category = await self.create_category(prefix="category_dup")
            try:
                payload = await self.tool(
                    "kb_category_create",
                    category_code=category["category_code"],
                    name=f"{category['name']}_dup",
                    description="重复编码测试",
                )
                self.assert_error(payload, code="CATEGORY_CODE_CONFLICT", error_type="business_error")
            finally:
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_category_can_recreate_same_code_and_name_after_soft_delete(self) -> None:
        async def scenario() -> None:
            category = await self.create_category(prefix="category_recreate")

            delete_payload = await self.tool("kb_category_delete", id=category["id"])
            self.assert_success(delete_payload)

            recreate_payload = await self.tool(
                "kb_category_create",
                category_code=category["category_code"],
                name=category["name"],
                description="软删除后重建分类",
            )
            self.assert_success(recreate_payload)

            recreated = recreate_payload["data"]["category"]
            self.assertNotEqual(recreated["id"], category["id"])

            try:
                get_payload = await self.tool("kb_category_get", id=recreated["id"])
                self.assert_success(get_payload)
                self.assertEqual(
                    get_payload["data"]["category"]["category_code"],
                    category["category_code"],
                )
                self.assertEqual(get_payload["data"]["category"]["name"], category["name"])
            finally:
                await self.delete_category_best_effort(recreated)

        self.run_async(scenario())

    def test_category_get_requires_identifier(self) -> None:
        async def scenario() -> None:
            payload = await self.tool("kb_category_get")
            self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")

        self.run_async(scenario())

    def test_category_list_rejects_page_size_over_limit(self) -> None:
        async def scenario() -> None:
            payload = await self.tool("kb_category_list", page=1, page_size=101)
            self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")

        self.run_async(scenario())
