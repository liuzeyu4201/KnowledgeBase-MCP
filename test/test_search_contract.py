from __future__ import annotations

from test.base import MCPIntegrationTestCase


class SearchContractTestCase(MCPIntegrationTestCase):
    """覆盖检索接口的契约、边界和召回质量基线。"""

    def test_bm25_exact_theorem_query_hits_expected_chunk(self) -> None:
        async def scenario() -> None:
            category = await self.create_category(prefix="search_exact")
            document = await self.import_document(
                category_id=category["id"],
                title_prefix="search_exact",
                large=True,
            )
            try:
                payload = await self.tool(
                    "kb_search_retrieve",
                    query="Open Mapping Theorem",
                    alpha=1.0,
                    limit=5,
                    document_id=document["id"],
                )
                self.assert_success(payload)
                previews = [item["content"] for item in payload["data"]["items"]]
                self.assertTrue(
                    any("Open Mapping Theorem" in preview for preview in previews),
                    payload,
                )
            finally:
                await self.delete_document_best_effort(document)
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_search_rejects_empty_query(self) -> None:
        async def scenario() -> None:
            payload = await self.tool("kb_search_retrieve", query="   ", alpha=1.0, limit=5)
            self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")

        self.run_async(scenario())

    def test_search_rejects_invalid_alpha(self) -> None:
        async def scenario() -> None:
            payload = await self.tool("kb_search_retrieve", query="Hilbert space", alpha=1.1, limit=5)
            self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")

        self.run_async(scenario())

    def test_bm25_natural_question_should_return_hilbert_definition_in_top3(self) -> None:
        async def scenario() -> None:
            category = await self.create_category(prefix="search_hilbert_question")
            document = await self.import_document(
                category_id=category["id"],
                title_prefix="search_hilbert_question",
                large=True,
            )
            try:
                payload = await self.tool(
                    "kb_search_retrieve",
                    query="what is Hilbert space?",
                    alpha=1.0,
                    limit=3,
                    document_id=document["id"],
                )
                self.assert_success(payload)
                previews = [item["content"] for item in payload["data"]["items"]]
                self.assertTrue(
                    any("then we say that X is a Hilbert space" in preview for preview in previews),
                    payload,
                )
            finally:
                await self.delete_document_best_effort(document)
                await self.delete_category_best_effort(category)

        self.run_async(scenario())

    def test_hybrid_search_chinese_query_should_hit_hilbert_section_in_top3(self) -> None:
        async def scenario() -> None:
            category = await self.create_category(prefix="search_hilbert_cn")
            document = await self.import_document(
                category_id=category["id"],
                title_prefix="search_hilbert_cn",
                large=True,
            )
            try:
                payload = await self.tool(
                    "kb_search_retrieve",
                    query="什么是希尔伯特空间",
                    alpha=0.5,
                    limit=3,
                    document_id=document["id"],
                )
                self.assert_success(payload)
                previews = [item["content"] for item in payload["data"]["items"]]
                self.assertTrue(
                    any("Hilbert space" in preview for preview in previews),
                    payload,
                )
            finally:
                await self.delete_document_best_effort(document)
                await self.delete_category_best_effort(category)

        self.run_async(scenario())
