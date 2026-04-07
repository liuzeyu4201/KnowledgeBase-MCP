# 测试文档

- 生成时间: 2026-04-07T11:19:35.548147
- Python: 3.13.12
- 平台: Linux-6.12.76-linuxkit-aarch64-with-glibc2.41
- 执行用例总数: 19
- 通过: 19
- 失败: 0
- 错误: 0
- 跳过: 0

## 执行摘要

```text
test_category_create_rejects_duplicate_code (test_category_contract.CategoryContractTestCase.test_category_create_rejects_duplicate_code) ... ok
test_category_create_rejects_invalid_code (test_category_contract.CategoryContractTestCase.test_category_create_rejects_invalid_code) ... ok
test_category_crud_smoke (test_category_contract.CategoryContractTestCase.test_category_crud_smoke) ... ok
test_category_get_requires_identifier (test_category_contract.CategoryContractTestCase.test_category_get_requires_identifier) ... ok
test_category_list_rejects_page_size_over_limit (test_category_contract.CategoryContractTestCase.test_category_list_rejects_page_size_over_limit) ... ok
test_concurrent_duplicate_category_create_should_only_return_business_conflict (test_concurrency_pressure.ConcurrencyAndPressureTestCase.test_concurrent_duplicate_category_create_should_only_return_business_conflict) ... ok
test_high_concurrency_search_requests_all_succeed (test_concurrency_pressure.ConcurrencyAndPressureTestCase.test_high_concurrency_search_requests_all_succeed) ... ok
test_sequential_search_pressure_burst (test_concurrency_pressure.ConcurrencyAndPressureTestCase.test_sequential_search_pressure_burst) ... ok
test_category_delete_rejects_active_documents (test_document_contract.DocumentContractTestCase.test_category_delete_rejects_active_documents) ... ok
test_document_import_get_list_delete_smoke (test_document_contract.DocumentContractTestCase.test_document_import_get_list_delete_smoke) ... ok
test_document_import_rejects_invalid_base64 (test_document_contract.DocumentContractTestCase.test_document_import_rejects_invalid_base64) ... ok
test_document_import_rejects_invalid_category (test_document_contract.DocumentContractTestCase.test_document_import_rejects_invalid_category) ... ok
test_document_import_rejects_invalid_mime_type (test_document_contract.DocumentContractTestCase.test_document_import_rejects_invalid_mime_type) ... ok
test_document_update_metadata_only (test_document_contract.DocumentContractTestCase.test_document_update_metadata_only) ... ok
test_bm25_exact_theorem_query_hits_expected_chunk (test_search_contract.SearchContractTestCase.test_bm25_exact_theorem_query_hits_expected_chunk) ... ok
test_bm25_natural_question_should_return_hilbert_definition_in_top3 (test_search_contract.SearchContractTestCase.test_bm25_natural_question_should_return_hilbert_definition_in_top3) ... ok
test_hybrid_search_chinese_query_should_hit_hilbert_section_in_top3 (test_search_contract.SearchContractTestCase.test_hybrid_search_chinese_query_should_hit_hilbert_section_in_top3) ... ok
test_search_rejects_empty_query (test_search_contract.SearchContractTestCase.test_search_rejects_empty_query) ... ok
test_search_rejects_invalid_alpha (test_search_contract.SearchContractTestCase.test_search_rejects_invalid_alpha) ... ok

----------------------------------------------------------------------
Ran 19 tests in 166.946s

OK
```

## 错误记录

本轮未发现失败或执行错误。
