# 测试文档

- 生成时间: 2026-04-08T09:24:03.250735
- Python: 3.13.12
- 平台: Linux-6.12.76-linuxkit-aarch64-with-glibc2.41
- 执行用例总数: 114
- 通过: 107
- 失败: 6
- 错误: 1
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
test_cancel_queued_task_cleans_staged_files (test_import_task_consistency.ImportTaskConsistencyTestCase.test_cancel_queued_task_cleans_staged_files)
一致性：取消 queued 任务后，暂存文件应被清理。 ... ok
test_cancel_running_task_does_not_corrupt_other_items (test_import_task_consistency.ImportTaskConsistencyTestCase.test_cancel_running_task_does_not_corrupt_other_items)
一致性：取消正在运行的任务时，不应影响同一任务中的其他子项记录。 ... ok
test_cancel_task_preserves_task_record_integrity (test_import_task_consistency.ImportTaskConsistencyTestCase.test_cancel_task_preserves_task_record_integrity)
一致性：取消任务后，任务记录应保持完整且状态一致。 ... ok
test_cancel_task_with_uid_and_id_both_provided (test_import_task_consistency.ImportTaskConsistencyTestCase.test_cancel_task_with_uid_and_id_both_provided)
一致性：同时提供 task_uid 和 id 取消任务，应一致处理。 ... ok
test_cancel_then_get_returns_consistent_state (test_import_task_consistency.ImportTaskConsistencyTestCase.test_cancel_then_get_returns_consistent_state)
一致性：取消后多次查询应返回一致的状态。 ... ok
test_cancel_with_mismatched_ids_returns_error (test_import_task_consistency.ImportTaskConsistencyTestCase.test_cancel_with_mismatched_ids_returns_error)
一致性：使用不匹配的 id 和 task_uid 应返回错误。 ... FAIL
test_cancel_with_nonexistent_id_returns_not_found (test_import_task_consistency.ImportTaskConsistencyTestCase.test_cancel_with_nonexistent_id_returns_not_found)
一致性：取消不存在的任务应返回 NOT_FOUND。 ... ok
test_concurrent_cancel_all_return_same_final_state (test_import_task_consistency.ImportTaskConsistencyTestCase.test_concurrent_cancel_all_return_same_final_state)
一致性：并发取消同一任务，所有请求应返回相同最终状态。 ... ok
test_concurrent_cancel_and_get_never_shows_inconsistent_state (test_import_task_consistency.ImportTaskConsistencyTestCase.test_concurrent_cancel_and_get_never_shows_inconsistent_state)
一致性：并发取消和查询操作不应显示不一致的状态。 ... ok
test_large_task_cancel_consistency (test_import_task_consistency.ImportTaskConsistencyTestCase.test_large_task_cancel_consistency)
一致性：大规模任务（100项）取消后状态一致。 ... ok
test_multiple_cancels_at_same_time_consistency (test_import_task_consistency.ImportTaskConsistencyTestCase.test_multiple_cancels_at_same_time_consistency)
一致性：同一时间多个取消请求，状态应一致。 ... ok
test_repeated_cancel_returns_consistent_response (test_import_task_consistency.ImportTaskConsistencyTestCase.test_repeated_cancel_returns_consistent_response)
一致性：重复取消同一任务，每次返回一致响应。 ... ok
test_repeated_get_returns_consistent_response (test_import_task_consistency.ImportTaskConsistencyTestCase.test_repeated_get_returns_consistent_response)
一致性：重复查询同一任务，每次返回一致响应。 ... ok
test_submit_and_immediately_cancel_consistency (test_import_task_consistency.ImportTaskConsistencyTestCase.test_submit_and_immediately_cancel_consistency)
一致性：提交后立即取消，状态应一致。 ... ok
test_task_counts_always_equal_sum_of_item_counts (test_import_task_consistency.ImportTaskConsistencyTestCase.test_task_counts_always_equal_sum_of_item_counts)
一致性：任务的状态计数始终等于各状态子项数之和。 ... ok
test_task_not_found_after_repeated_cancel (test_import_task_consistency.ImportTaskConsistencyTestCase.test_task_not_found_after_repeated_cancel)
一致性：对于已取消的任务，重复取消应返回 NOT_FOUND 或一致状态。 ... ok
test_task_priority_and_attempts_consistency (test_import_task_consistency.ImportTaskConsistencyTestCase.test_task_priority_and_attempts_consistency)
一致性：任务优先级和重试次数字段应一致保存。 ... ok
test_task_status_transitions_are_atomic (test_import_task_consistency.ImportTaskConsistencyTestCase.test_task_status_transitions_are_atomic)
一致性：任务状态转换应是原子的。 ... ok
test_task_timestamps_consistency (test_import_task_consistency.ImportTaskConsistencyTestCase.test_task_timestamps_consistency)
一致性：任务的时间戳字段应合理且一致。 ... FAIL
test_batch_cancel_already_finished_task_returns_conflict (test_import_task_contract.ImportTaskContractTestCase.test_batch_cancel_already_finished_task_returns_conflict)
取消已完成的任務应直接返回（不做二次取消）。 ... ok
test_batch_cancel_not_found_task (test_import_task_contract.ImportTaskContractTestCase.test_batch_cancel_not_found_task)
取消不存在的任务应返回 NOT_FOUND。 ... ok
test_batch_cancel_queued_task (test_import_task_contract.ImportTaskContractTestCase.test_batch_cancel_queued_task)
取消处于 queued 状态的任务。 ... ok
test_batch_cancel_rejects_neither_id_nor_task_uid (test_import_task_contract.ImportTaskContractTestCase.test_batch_cancel_rejects_neither_id_nor_task_uid)
取消时既没有 id 也没有 task_uid 应被拒绝。 ... ok
test_batch_get_include_items_false (test_import_task_contract.ImportTaskContractTestCase.test_batch_get_include_items_false)
查询时 include_items=False 不返回子项详情。 ... ok
test_batch_get_not_found_task (test_import_task_contract.ImportTaskContractTestCase.test_batch_get_not_found_task)
查询不存在的任务应返回 NOT_FOUND。 ... ok
test_batch_get_rejects_mismatch_id_and_task_uid (test_import_task_contract.ImportTaskContractTestCase.test_batch_get_rejects_mismatch_id_and_task_uid)
id 和 task_uid 同时提供但不匹配时应被拒绝。 ... FAIL
test_batch_get_rejects_neither_id_nor_task_uid (test_import_task_contract.ImportTaskContractTestCase.test_batch_get_rejects_neither_id_nor_task_uid)
查询时既没有 id 也没有 task_uid 应被拒绝。 ... ok
test_batch_submit_and_get_by_uid (test_import_task_contract.ImportTaskContractTestCase.test_batch_submit_and_get_by_uid)
通过 task_uid 查询任务。 ... ok
test_batch_submit_and_get_smoke (test_import_task_contract.ImportTaskContractTestCase.test_batch_submit_and_get_smoke)
提交批量任务并查询状态。 ... ok
test_batch_submit_large_pdf (test_import_task_contract.ImportTaskContractTestCase.test_batch_submit_large_pdf)
提交大文件 PDF（ Functional Analysis Notes.pdf）。 ... ok
test_batch_submit_rejects_empty_items (test_import_task_contract.ImportTaskContractTestCase.test_batch_submit_rejects_empty_items)
items 为空列表时应被拒绝。 ... ok
test_batch_submit_rejects_empty_title (test_import_task_contract.ImportTaskContractTestCase.test_batch_submit_rejects_empty_title)
item 中 title 为空时应被拒绝。 ... ok
test_batch_submit_rejects_invalid_base64 (test_import_task_contract.ImportTaskContractTestCase.test_batch_submit_rejects_invalid_base64)
item 中 file_content_base64 为非法格式时应被拒绝。 ... ok
test_batch_submit_rejects_invalid_category (test_import_task_contract.ImportTaskContractTestCase.test_batch_submit_rejects_invalid_category)
item 中包含不存在的 category_id 应被拒绝。 ... FAIL
test_batch_submit_rejects_invalid_mime_type (test_import_task_contract.ImportTaskContractTestCase.test_batch_submit_rejects_invalid_mime_type)
item 中 mime_type 不是 application/pdf 时应被拒绝。 ... ok
test_batch_submit_rejects_item_priority_out_of_range (test_import_task_contract.ImportTaskContractTestCase.test_batch_submit_rejects_item_priority_out_of_range)
item 中 priority 超出 0-1000 范围时应被拒绝。 ... ok
test_batch_submit_rejects_items_over_limit (test_import_task_contract.ImportTaskContractTestCase.test_batch_submit_rejects_items_over_limit)
items 数量超过 100 时应被拒绝。 ... ok
test_batch_submit_rejects_max_attempts_out_of_range (test_import_task_contract.ImportTaskContractTestCase.test_batch_submit_rejects_max_attempts_out_of_range)
max_attempts 超出 1-10 范围时应被拒绝。 ... ok
test_batch_submit_rejects_priority_out_of_range (test_import_task_contract.ImportTaskContractTestCase.test_batch_submit_rejects_priority_out_of_range)
priority 超出 0-1000 范围时应被拒绝。 ... ok
test_batch_submit_with_idempotency_key_returns_same_task (test_import_task_contract.ImportTaskContractTestCase.test_batch_submit_with_idempotency_key_returns_same_task)
相同 idempotency_key 应返回同一任务。 ... ok
test_batch_task_full_lifecycle_pending_to_canceled (test_import_task_contract.ImportTaskContractTestCase.test_batch_task_full_lifecycle_pending_to_canceled)
完整生命周期：queued -> canceled。 ... ok
test_batch_task_item_statuses_consistent (test_import_task_contract.ImportTaskContractTestCase.test_batch_task_item_statuses_consistent)
任务子项状态一致性：子项状态之和与任务状态一致。 ... ok
test_batch_task_metadata_fields_preserved (test_import_task_contract.ImportTaskContractTestCase.test_batch_task_metadata_fields_preserved)
任务元数据字段（request_id, operator, trace_id）正确保存。 ... ok
test_batch_task_priority_ordering (test_import_task_contract.ImportTaskContractTestCase.test_batch_task_priority_ordering)
高优先级任务排在前面（通过 worker 处理顺序验证）。 ... ok
test_batch_task_progress_after_submit (test_import_task_contract.ImportTaskContractTestCase.test_batch_task_progress_after_submit)
提交后任务状态和进度正确。 ... ok
test_concurrent_batch_cancel_same_task (test_import_task_contract.ImportTaskContractTestCase.test_concurrent_batch_cancel_same_task)
并发取消同一任务，所有取消请求都成功返回。 ... ok
test_concurrent_batch_submit_different_tasks (test_import_task_contract.ImportTaskContractTestCase.test_concurrent_batch_submit_different_tasks)
并发提交多个不同的批量任务，所有任务都成功创建。 ... ok
test_concurrent_batch_submit_same_idempotency_key (test_import_task_contract.ImportTaskContractTestCase.test_concurrent_batch_submit_same_idempotency_key)
并发提交相同 idempotency_key 的任务，只有一个成功。 ... FAIL
test_batch_cancel_preserves_task_history (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_cancel_preserves_task_history)
一致性：取消后任务的历史记录（canceled_items）正确。 ... ok
test_batch_cancel_rejects_negative_id (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_cancel_rejects_negative_id)
异常：取消时 id 为负数。 ... ok
test_batch_cancel_running_task_sets_cancel_requested (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_cancel_running_task_sets_cancel_requested)
状态机：running 状态的任务取消应设置 cancel_requested。 ... ok
test_batch_cancel_with_only_id (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_cancel_with_only_id)
空值：仅通过 id 取消。 ... ok
test_batch_cancel_with_only_task_uid (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_cancel_with_only_task_uid)
空值：仅通过 task_uid 取消。 ... ok
test_batch_get_after_cancel_returns_canceled_status (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_get_after_cancel_returns_canceled_status)
状态机：取消后查询应返回 canceled 状态。 ... ok
test_batch_get_rejects_negative_id (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_get_rejects_negative_id)
异常：查询时 id 为负数。 ... ok
test_batch_get_with_only_id (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_get_with_only_id)
空值：仅通过 id 查询。 ... ok
test_batch_get_with_only_task_uid (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_get_with_only_task_uid)
空值：仅通过 task_uid 查询。 ... ok
test_batch_submit_extremely_large_items_count (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_extremely_large_items_count)
边界：items 数量为 1（最小有效值）。 ... ok
test_batch_submit_file_name_at_max_length (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_file_name_at_max_length)
边界：file_name 长度为 256 字符（最大有效值）。 ... FAIL
test_batch_submit_file_name_with_special_characters (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_file_name_with_special_characters)
特殊字符：file_name 包含空格和特殊字符。 ... ok
test_batch_submit_idempotency_key_at_max_length (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_idempotency_key_at_max_length)
边界：idempotency_key 长度为 128 字符（最大有效值）。 ... ok
test_batch_submit_items_at_size_limit (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_items_at_size_limit)
边界：items 数量为 100（最大有效值）。 ... ok
test_batch_submit_max_attempts_at_boundaries (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_max_attempts_at_boundaries)
边界：max_attempts 为 1 和 10（有效范围边界）。 ... ok
test_batch_submit_multiple_small_tasks_rapidly (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_multiple_small_tasks_rapidly)
压力：快速连续提交多个小任务。 ... ok
test_batch_submit_priority_at_boundaries (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_priority_at_boundaries)
边界：priority 为 0 和 1000（有效范围边界）。 ... ok
test_batch_submit_rejects_empty_base64 (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_rejects_empty_base64)
异常：file_content_base64 为空。 ... ok
test_batch_submit_rejects_empty_file_name (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_rejects_empty_file_name)
异常：file_name 为空。 ... ok
test_batch_submit_rejects_empty_mime_type (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_rejects_empty_mime_type)
异常：mime_type 为空。 ... ok
test_batch_submit_rejects_file_name_too_long (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_rejects_file_name_too_long)
异常：file_name 超过 256 字符。 ... ok
test_batch_submit_rejects_idempotency_key_too_long (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_rejects_idempotency_key_too_long)
异常：idempotency_key 超过 128 字符。 ... ok
test_batch_submit_rejects_negative_category_id (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_rejects_negative_category_id)
异常：category_id 为负数。 ... ok
test_batch_submit_rejects_negative_item_priority (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_rejects_negative_item_priority)
异常：item priority 为负数。 ... ok
test_batch_submit_rejects_negative_priority (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_rejects_negative_priority)
异常：priority 为负数。 ... ok
test_batch_submit_rejects_title_too_long (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_rejects_title_too_long)
异常：title 超过 256 字符。 ... ok
test_batch_submit_rejects_unsupported_mime_type (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_rejects_unsupported_mime_type)
异常：mime_type 为不支持的类型。 ... ok
test_batch_submit_rejects_whitespace_only_title (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_rejects_whitespace_only_title)
异常：title 仅包含空白字符。 ... ok
test_batch_submit_rejects_zero_category_id (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_rejects_zero_category_id)
异常：category_id 为 0。 ... ok
test_batch_submit_rejects_zero_max_attempts (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_rejects_zero_max_attempts)
异常：max_attempts 为 0。 ... ok
test_batch_submit_title_at_max_length (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_title_at_max_length)
边界：title 长度为 256 字符（最大有效值）。 ... ok
test_batch_submit_title_with_special_characters (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_title_with_special_characters)
特殊字符：title 包含中英文混合和特殊符号。 ... ok
test_batch_submit_with_all_optional_fields_null (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_with_all_optional_fields_null)
空值：所有可选字段为 null。 ... ok
test_batch_submit_with_empty_idempotency_key (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_with_empty_idempotency_key)
空值：idempotency_key 为空字符串（应被转为 None）。 ... ok
test_batch_task_item_priority_inherited_from_task (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_task_item_priority_inherited_from_task)
一致性：子项未指定 priority 时继承任务 priority。 ... ok
test_batch_task_item_priority_overrides_task (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_task_item_priority_overrides_task)
一致性：子项指定 priority 时覆盖任务 priority。 ... ok
test_batch_task_items_order_preserved (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_task_items_order_preserved)
一致性：任务子项的 item_no 按提交顺序递增。 ... ok
test_batch_task_progress_percent_calculation (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_task_progress_percent_calculation)
进度：progress_percent 计算正确。 ... ok
test_batch_task_status_counts_after_cancel (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_task_status_counts_after_cancel)
进度：取消后各状态计数正确。 ... ok
test_high_concurrent_batch_cancel_same_task_20_times (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_high_concurrent_batch_cancel_same_task_20_times)
压力：同一任务并发取消 20 次。 ... ok
test_high_concurrent_batch_get_same_task_30_times (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_high_concurrent_batch_get_same_task_30_times)
压力：同一任务并发查询 30 次。 ... ok
test_high_concurrent_batch_submit_10_tasks (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_high_concurrent_batch_submit_10_tasks)
压力：10 个不同任务并发提交。 ... ok
test_mixed_operations_concurrent_stress (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_mixed_operations_concurrent_stress)
压力：混合 submit/get/cancel 操作并发执行。 ... ERROR
test_race_condition_idempotency_key_concurrent_submit (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_race_condition_idempotency_key_concurrent_submit)
竞态：并发提交相同 idempotency_key 存在竞态条件（预期失败）。 ... ok
test_rapid_repeated_cancel_same_task (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_rapid_repeated_cancel_same_task)
快速连续：同一任务重复取消多次。 ... ok
test_rapid_repeated_get_same_task (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_rapid_repeated_get_same_task)
快速连续：同一任务重复查询多次。 ... ok
test_rapid_submit_cancel_submit_sequence (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_rapid_submit_cancel_submit_sequence)
快速连续：submit -> cancel -> submit 序列。 ... ok
test_bm25_exact_theorem_query_hits_expected_chunk (test_search_contract.SearchContractTestCase.test_bm25_exact_theorem_query_hits_expected_chunk) ... ok
test_bm25_natural_question_should_return_hilbert_definition_in_top3 (test_search_contract.SearchContractTestCase.test_bm25_natural_question_should_return_hilbert_definition_in_top3) ... ok
test_hybrid_search_chinese_query_should_hit_hilbert_section_in_top3 (test_search_contract.SearchContractTestCase.test_hybrid_search_chinese_query_should_hit_hilbert_section_in_top3) ... ok
test_search_rejects_empty_query (test_search_contract.SearchContractTestCase.test_search_rejects_empty_query) ... ok
test_search_rejects_invalid_alpha (test_search_contract.SearchContractTestCase.test_search_rejects_invalid_alpha) ... ok

======================================================================
ERROR: test_mixed_operations_concurrent_stress (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_mixed_operations_concurrent_stress)
压力：混合 submit/get/cancel 操作并发执行。
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/test/test_import_task_production_edge_cases.py", line 381, in test_mixed_operations_concurrent_stress
    self.run_async(scenario())
    ~~~~~~~~~~~~~~^^^^^^^^^^^^
  File "/app/test/base.py", line 28, in run_async
    return asyncio.run(coroutine)
           ~~~~~~~~~~~^^^^^^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 195, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/base_events.py", line 725, in run_until_complete
    return future.result()
           ~~~~~~~~~~~~~^^
  File "/app/test/test_import_task_production_edge_cases.py", line 375, in scenario
    self.assertTrue(r.get("success"), r)
                    ^^^^^
AttributeError: 'str' object has no attribute 'get'

======================================================================
FAIL: test_cancel_with_mismatched_ids_returns_error (test_import_task_consistency.ImportTaskConsistencyTestCase.test_cancel_with_mismatched_ids_returns_error)
一致性：使用不匹配的 id 和 task_uid 应返回错误。
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/test/test_import_task_consistency.py", line 661, in test_cancel_with_mismatched_ids_returns_error
    self.run_async(scenario())
    ~~~~~~~~~~~~~~^^^^^^^^^^^^
  File "/app/test/base.py", line 28, in run_async
    return asyncio.run(coroutine)
           ~~~~~~~~~~~^^^^^^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 195, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/base_events.py", line 725, in run_until_complete
    return future.result()
           ~~~~~~~~~~~~~^^
  File "/app/test/test_import_task_consistency.py", line 656, in scenario
    self.assert_error(cancel_payload, code="INVALID_ARGUMENT", error_type="validation_error")
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/test/base.py", line 62, in assert_error
    self.assertFalse(payload.get("success"), payload)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: True is not false : {'success': True, 'code': 'OK', 'message': 'success', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-08T09:22:45.363518+00:00', 'data': {'task': {'id': 107, 'task_uid': '1e27e6d0-d81e-48d3-940b-d7cc9d8d2539', 'task_type': 'document_import_batch', 'status': 'canceled', 'priority': 50, 'cancel_requested': True, 'idempotency_key': None, 'request_id': None, 'operator': None, 'trace_id': None, 'total_items': 1, 'pending_items': 0, 'running_items': 0, 'success_items': 0, 'failed_items': 0, 'canceled_items': 1, 'progress_percent': 100.0, 'attempt_count': 0, 'max_attempts': 3, 'started_at': None, 'finished_at': '2026-04-08T09:22:45.361050', 'heartbeat_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:45.343752', 'updated_at': '2026-04-08T09:22:45.361192', 'items': [{'id': 234, 'item_no': 1, 'status': 'canceled', 'priority': 50, 'category_id': 236, 'title': 'consistency_mismatch_1775640165333_281473577148944', 'file_name': 'Functional_Analysis.pdf', 'mime_type': 'application/pdf', 'file_sha256': 'e27cc09ecbeb8ac295697bec3fe07bc24c671b8c69cfdffe3b7c05fc3f2a8060', 'document_id': None, 'document_uid': None, 'attempt_count': 0, 'started_at': None, 'finished_at': '2026-04-08T09:22:45.361050', 'last_error': 'task canceled before execution', 'created_at': '2026-04-08T09:22:45.345840', 'updated_at': '2026-04-08T09:22:45.361961'}]}}}

======================================================================
FAIL: test_task_timestamps_consistency (test_import_task_consistency.ImportTaskConsistencyTestCase.test_task_timestamps_consistency)
一致性：任务的时间戳字段应合理且一致。
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/test/test_import_task_consistency.py", line 863, in test_task_timestamps_consistency
    self.run_async(scenario())
    ~~~~~~~~~~~~~~^^^^^^^^^^^^
  File "/app/test/base.py", line 28, in run_async
    return asyncio.run(coroutine)
           ~~~~~~~~~~~^^^^^^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 195, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/base_events.py", line 725, in run_until_complete
    return future.result()
           ~~~~~~~~~~~~~^^
  File "/app/test/test_import_task_consistency.py", line 848, in scenario
    self.assertEqual(task["created_at"], task["updated_at"])
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: '2026-04-08T09:22:47.581640' != '2026-04-08T09:22:47.581643'
- 2026-04-08T09:22:47.581640
?                          ^
+ 2026-04-08T09:22:47.581643
?                          ^


======================================================================
FAIL: test_batch_get_rejects_mismatch_id_and_task_uid (test_import_task_contract.ImportTaskContractTestCase.test_batch_get_rejects_mismatch_id_and_task_uid)
id 和 task_uid 同时提供但不匹配时应被拒绝。
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/test/test_import_task_contract.py", line 411, in test_batch_get_rejects_mismatch_id_and_task_uid
    self.run_async(scenario())
    ~~~~~~~~~~~~~~^^^^^^^^^^^^
  File "/app/test/base.py", line 28, in run_async
    return asyncio.run(coroutine)
           ~~~~~~~~~~~^^^^^^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 195, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/base_events.py", line 725, in run_until_complete
    return future.result()
           ~~~~~~~~~~~~~^^
  File "/app/test/test_import_task_contract.py", line 406, in scenario
    self.assert_error(get_payload, code="INVALID_ARGUMENT", error_type="validation_error")
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/test/base.py", line 62, in assert_error
    self.assertFalse(payload.get("success"), payload)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: True is not false : {'success': True, 'code': 'OK', 'message': 'success', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-08T09:22:52.145938+00:00', 'data': {'task': {'id': 127, 'task_uid': 'cc6de5b4-9618-4548-a218-f2974ca75fd4', 'task_type': 'document_import_batch', 'status': 'queued', 'priority': 50, 'cancel_requested': False, 'idempotency_key': None, 'request_id': None, 'operator': None, 'trace_id': None, 'total_items': 1, 'pending_items': 1, 'running_items': 0, 'success_items': 0, 'failed_items': 0, 'canceled_items': 0, 'progress_percent': 0.0, 'attempt_count': 0, 'max_attempts': 3, 'started_at': None, 'finished_at': None, 'heartbeat_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:52.125511', 'updated_at': '2026-04-08T09:22:52.125514', 'items': [{'id': 266, 'item_no': 1, 'status': 'pending', 'priority': 50, 'category_id': 252, 'title': 'batch_mismatch_1775640172114_281473577342624', 'file_name': 'Functional_Analysis.pdf', 'mime_type': 'application/pdf', 'file_sha256': 'e27cc09ecbeb8ac295697bec3fe07bc24c671b8c69cfdffe3b7c05fc3f2a8060', 'document_id': None, 'document_uid': None, 'attempt_count': 0, 'started_at': None, 'finished_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:52.127713', 'updated_at': '2026-04-08T09:22:52.127715'}]}}}

======================================================================
FAIL: test_batch_submit_rejects_invalid_category (test_import_task_contract.ImportTaskContractTestCase.test_batch_submit_rejects_invalid_category)
item 中包含不存在的 category_id 应被拒绝。
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/test/test_import_task_contract.py", line 245, in test_batch_submit_rejects_invalid_category
    self.run_async(scenario())
    ~~~~~~~~~~~~~~^^^^^^^^^^^^
  File "/app/test/base.py", line 28, in run_async
    return asyncio.run(coroutine)
           ~~~~~~~~~~~^^^^^^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 195, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/base_events.py", line 725, in run_until_complete
    return future.result()
           ~~~~~~~~~~~~~^^
  File "/app/test/test_import_task_contract.py", line 243, in scenario
    self.assert_error(payload, code="CATEGORY_NOT_FOUND", error_type="not_found")
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/test/base.py", line 62, in assert_error
    self.assertFalse(payload.get("success"), payload)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: True is not false : {'success': True, 'code': 'OK', 'message': 'success', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-08T09:22:52.608816+00:00', 'data': {'task': {'id': 132, 'task_uid': 'a0f6b0cf-f05d-4420-bfb4-85dca024233c', 'task_type': 'document_import_batch', 'status': 'queued', 'priority': 50, 'cancel_requested': False, 'idempotency_key': None, 'request_id': None, 'operator': None, 'trace_id': None, 'total_items': 1, 'pending_items': 1, 'running_items': 0, 'success_items': 0, 'failed_items': 0, 'canceled_items': 0, 'progress_percent': 0.0, 'attempt_count': 0, 'max_attempts': 3, 'started_at': None, 'finished_at': None, 'heartbeat_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:52.605456', 'updated_at': '2026-04-08T09:22:52.605459', 'items': [{'id': 271, 'item_no': 1, 'status': 'pending', 'priority': 50, 'category_id': 99999999, 'title': 'batch_invalid_cat_1775640172594_281473578329520', 'file_name': 'Functional_Analysis.pdf', 'mime_type': 'application/pdf', 'file_sha256': 'e27cc09ecbeb8ac295697bec3fe07bc24c671b8c69cfdffe3b7c05fc3f2a8060', 'document_id': None, 'document_uid': None, 'attempt_count': 0, 'started_at': None, 'finished_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:52.607586', 'updated_at': '2026-04-08T09:22:52.607588'}]}}}

======================================================================
FAIL: test_concurrent_batch_submit_same_idempotency_key (test_import_task_contract.ImportTaskContractTestCase.test_concurrent_batch_submit_same_idempotency_key)
并发提交相同 idempotency_key 的任务，只有一个成功。
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/test/test_import_task_contract.py", line 623, in test_concurrent_batch_submit_same_idempotency_key
    self.run_async(scenario())
    ~~~~~~~~~~~~~~^^^^^^^^^^^^
  File "/app/test/base.py", line 28, in run_async
    return asyncio.run(coroutine)
           ~~~~~~~~~~~^^^^^^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 195, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/base_events.py", line 725, in run_until_complete
    return future.result()
           ~~~~~~~~~~~~~^^
  File "/app/test/test_import_task_contract.py", line 616, in scenario
    self.assertEqual(len(success_results), 1, results)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 5 != 1 : [{'success': True, 'code': 'OK', 'message': 'success', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-08T09:22:57.881957+00:00', 'data': {'task': {'id': 146, 'task_uid': '1dba7a9f-8822-4a9b-8f95-460530f7f550', 'task_type': 'document_import_batch', 'status': 'queued', 'priority': 50, 'cancel_requested': False, 'idempotency_key': 'concurrent_idem_1775640177810_281473576986960', 'request_id': None, 'operator': None, 'trace_id': None, 'total_items': 1, 'pending_items': 1, 'running_items': 0, 'success_items': 0, 'failed_items': 0, 'canceled_items': 0, 'progress_percent': 0.0, 'attempt_count': 0, 'max_attempts': 3, 'started_at': None, 'finished_at': None, 'heartbeat_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:57.878723', 'updated_at': '2026-04-08T09:22:57.878726', 'items': [{'id': 289, 'item_no': 1, 'status': 'pending', 'priority': 50, 'category_id': 271, 'title': 'concurrent_idem_item_0_1775640177837_281473576986960', 'file_name': 'Functional_Analysis.pdf', 'mime_type': 'application/pdf', 'file_sha256': 'e27cc09ecbeb8ac295697bec3fe07bc24c671b8c69cfdffe3b7c05fc3f2a8060', 'document_id': None, 'document_uid': None, 'attempt_count': 0, 'started_at': None, 'finished_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:57.880724', 'updated_at': '2026-04-08T09:22:57.880726'}]}}}, {'success': True, 'code': 'OK', 'message': 'success', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-08T09:22:57.883552+00:00', 'data': {'task': {'id': 146, 'task_uid': '1dba7a9f-8822-4a9b-8f95-460530f7f550', 'task_type': 'document_import_batch', 'status': 'queued', 'priority': 50, 'cancel_requested': False, 'idempotency_key': 'concurrent_idem_1775640177810_281473576986960', 'request_id': None, 'operator': None, 'trace_id': None, 'total_items': 1, 'pending_items': 1, 'running_items': 0, 'success_items': 0, 'failed_items': 0, 'canceled_items': 0, 'progress_percent': 0.0, 'attempt_count': 0, 'max_attempts': 3, 'started_at': None, 'finished_at': None, 'heartbeat_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:57.878723', 'updated_at': '2026-04-08T09:22:57.878726', 'items': [{'id': 289, 'item_no': 1, 'status': 'pending', 'priority': 50, 'category_id': 271, 'title': 'concurrent_idem_item_0_1775640177837_281473576986960', 'file_name': 'Functional_Analysis.pdf', 'mime_type': 'application/pdf', 'file_sha256': 'e27cc09ecbeb8ac295697bec3fe07bc24c671b8c69cfdffe3b7c05fc3f2a8060', 'document_id': None, 'document_uid': None, 'attempt_count': 0, 'started_at': None, 'finished_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:57.880724', 'updated_at': '2026-04-08T09:22:57.880726'}]}}}, {'success': True, 'code': 'OK', 'message': 'success', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-08T09:22:57.884794+00:00', 'data': {'task': {'id': 146, 'task_uid': '1dba7a9f-8822-4a9b-8f95-460530f7f550', 'task_type': 'document_import_batch', 'status': 'queued', 'priority': 50, 'cancel_requested': False, 'idempotency_key': 'concurrent_idem_1775640177810_281473576986960', 'request_id': None, 'operator': None, 'trace_id': None, 'total_items': 1, 'pending_items': 1, 'running_items': 0, 'success_items': 0, 'failed_items': 0, 'canceled_items': 0, 'progress_percent': 0.0, 'attempt_count': 0, 'max_attempts': 3, 'started_at': None, 'finished_at': None, 'heartbeat_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:57.878723', 'updated_at': '2026-04-08T09:22:57.878726', 'items': [{'id': 289, 'item_no': 1, 'status': 'pending', 'priority': 50, 'category_id': 271, 'title': 'concurrent_idem_item_0_1775640177837_281473576986960', 'file_name': 'Functional_Analysis.pdf', 'mime_type': 'application/pdf', 'file_sha256': 'e27cc09ecbeb8ac295697bec3fe07bc24c671b8c69cfdffe3b7c05fc3f2a8060', 'document_id': None, 'document_uid': None, 'attempt_count': 0, 'started_at': None, 'finished_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:57.880724', 'updated_at': '2026-04-08T09:22:57.880726'}]}}}, {'success': True, 'code': 'OK', 'message': 'success', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-08T09:22:57.887993+00:00', 'data': {'task': {'id': 146, 'task_uid': '1dba7a9f-8822-4a9b-8f95-460530f7f550', 'task_type': 'document_import_batch', 'status': 'queued', 'priority': 50, 'cancel_requested': False, 'idempotency_key': 'concurrent_idem_1775640177810_281473576986960', 'request_id': None, 'operator': None, 'trace_id': None, 'total_items': 1, 'pending_items': 1, 'running_items': 0, 'success_items': 0, 'failed_items': 0, 'canceled_items': 0, 'progress_percent': 0.0, 'attempt_count': 0, 'max_attempts': 3, 'started_at': None, 'finished_at': None, 'heartbeat_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:57.878723', 'updated_at': '2026-04-08T09:22:57.878726', 'items': [{'id': 289, 'item_no': 1, 'status': 'pending', 'priority': 50, 'category_id': 271, 'title': 'concurrent_idem_item_0_1775640177837_281473576986960', 'file_name': 'Functional_Analysis.pdf', 'mime_type': 'application/pdf', 'file_sha256': 'e27cc09ecbeb8ac295697bec3fe07bc24c671b8c69cfdffe3b7c05fc3f2a8060', 'document_id': None, 'document_uid': None, 'attempt_count': 0, 'started_at': None, 'finished_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:57.880724', 'updated_at': '2026-04-08T09:22:57.880726'}]}}}, {'success': True, 'code': 'OK', 'message': 'success', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-08T09:22:57.889396+00:00', 'data': {'task': {'id': 146, 'task_uid': '1dba7a9f-8822-4a9b-8f95-460530f7f550', 'task_type': 'document_import_batch', 'status': 'queued', 'priority': 50, 'cancel_requested': False, 'idempotency_key': 'concurrent_idem_1775640177810_281473576986960', 'request_id': None, 'operator': None, 'trace_id': None, 'total_items': 1, 'pending_items': 1, 'running_items': 0, 'success_items': 0, 'failed_items': 0, 'canceled_items': 0, 'progress_percent': 0.0, 'attempt_count': 0, 'max_attempts': 3, 'started_at': None, 'finished_at': None, 'heartbeat_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:57.878723', 'updated_at': '2026-04-08T09:22:57.878726', 'items': [{'id': 289, 'item_no': 1, 'status': 'pending', 'priority': 50, 'category_id': 271, 'title': 'concurrent_idem_item_0_1775640177837_281473576986960', 'file_name': 'Functional_Analysis.pdf', 'mime_type': 'application/pdf', 'file_sha256': 'e27cc09ecbeb8ac295697bec3fe07bc24c671b8c69cfdffe3b7c05fc3f2a8060', 'document_id': None, 'document_uid': None, 'attempt_count': 0, 'started_at': None, 'finished_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:57.880724', 'updated_at': '2026-04-08T09:22:57.880726'}]}}}]

======================================================================
FAIL: test_batch_submit_file_name_at_max_length (test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_file_name_at_max_length)
边界：file_name 长度为 256 字符（最大有效值）。
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/test/test_import_task_production_edge_cases.py", line 188, in test_batch_submit_file_name_at_max_length
    self.run_async(scenario())
    ~~~~~~~~~~~~~~^^^^^^^^^^^^
  File "/app/test/base.py", line 28, in run_async
    return asyncio.run(coroutine)
           ~~~~~~~~~~~^^^^^^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 195, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/base_events.py", line 725, in run_until_complete
    return future.result()
           ~~~~~~~~~~~~~^^
  File "/app/test/test_import_task_production_edge_cases.py", line 184, in scenario
    self.assert_success(payload)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^^
  File "/app/test/base.py", line 50, in assert_success
    self.assertTrue(payload.get("success"), payload)
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : {'success': False, 'code': 'INTERNAL_ERROR', 'message': 'internal server error', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-08T09:22:58.753662+00:00', 'error': {'type': 'system_error', 'details': {'error': "[Errno 36] File name too long: '/app/data/storage/_tasks/8680d30a-a85f-44af-8c99-043ba8e0fa6d/000001_863e00575ca94c998065cfe921769533_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.pdf'"}}}

----------------------------------------------------------------------
Ran 114 tests in 184.006s

FAILED (failures=6, errors=1)
```

## 错误记录

### 失败: test_import_task_consistency.ImportTaskConsistencyTestCase.test_cancel_with_mismatched_ids_returns_error

```text
Traceback (most recent call last):
  File "/app/test/test_import_task_consistency.py", line 661, in test_cancel_with_mismatched_ids_returns_error
    self.run_async(scenario())
    ~~~~~~~~~~~~~~^^^^^^^^^^^^
  File "/app/test/base.py", line 28, in run_async
    return asyncio.run(coroutine)
           ~~~~~~~~~~~^^^^^^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 195, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/base_events.py", line 725, in run_until_complete
    return future.result()
           ~~~~~~~~~~~~~^^
  File "/app/test/test_import_task_consistency.py", line 656, in scenario
    self.assert_error(cancel_payload, code="INVALID_ARGUMENT", error_type="validation_error")
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/test/base.py", line 62, in assert_error
    self.assertFalse(payload.get("success"), payload)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: True is not false : {'success': True, 'code': 'OK', 'message': 'success', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-08T09:22:45.363518+00:00', 'data': {'task': {'id': 107, 'task_uid': '1e27e6d0-d81e-48d3-940b-d7cc9d8d2539', 'task_type': 'document_import_batch', 'status': 'canceled', 'priority': 50, 'cancel_requested': True, 'idempotency_key': None, 'request_id': None, 'operator': None, 'trace_id': None, 'total_items': 1, 'pending_items': 0, 'running_items': 0, 'success_items': 0, 'failed_items': 0, 'canceled_items': 1, 'progress_percent': 100.0, 'attempt_count': 0, 'max_attempts': 3, 'started_at': None, 'finished_at': '2026-04-08T09:22:45.361050', 'heartbeat_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:45.343752', 'updated_at': '2026-04-08T09:22:45.361192', 'items': [{'id': 234, 'item_no': 1, 'status': 'canceled', 'priority': 50, 'category_id': 236, 'title': 'consistency_mismatch_1775640165333_281473577148944', 'file_name': 'Functional_Analysis.pdf', 'mime_type': 'application/pdf', 'file_sha256': 'e27cc09ecbeb8ac295697bec3fe07bc24c671b8c69cfdffe3b7c05fc3f2a8060', 'document_id': None, 'document_uid': None, 'attempt_count': 0, 'started_at': None, 'finished_at': '2026-04-08T09:22:45.361050', 'last_error': 'task canceled before execution', 'created_at': '2026-04-08T09:22:45.345840', 'updated_at': '2026-04-08T09:22:45.361961'}]}}}
```

### 失败: test_import_task_consistency.ImportTaskConsistencyTestCase.test_task_timestamps_consistency

```text
Traceback (most recent call last):
  File "/app/test/test_import_task_consistency.py", line 863, in test_task_timestamps_consistency
    self.run_async(scenario())
    ~~~~~~~~~~~~~~^^^^^^^^^^^^
  File "/app/test/base.py", line 28, in run_async
    return asyncio.run(coroutine)
           ~~~~~~~~~~~^^^^^^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 195, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/base_events.py", line 725, in run_until_complete
    return future.result()
           ~~~~~~~~~~~~~^^
  File "/app/test/test_import_task_consistency.py", line 848, in scenario
    self.assertEqual(task["created_at"], task["updated_at"])
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: '2026-04-08T09:22:47.581640' != '2026-04-08T09:22:47.581643'
- 2026-04-08T09:22:47.581640
?                          ^
+ 2026-04-08T09:22:47.581643
?                          ^
```

### 失败: test_import_task_contract.ImportTaskContractTestCase.test_batch_get_rejects_mismatch_id_and_task_uid

```text
Traceback (most recent call last):
  File "/app/test/test_import_task_contract.py", line 411, in test_batch_get_rejects_mismatch_id_and_task_uid
    self.run_async(scenario())
    ~~~~~~~~~~~~~~^^^^^^^^^^^^
  File "/app/test/base.py", line 28, in run_async
    return asyncio.run(coroutine)
           ~~~~~~~~~~~^^^^^^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 195, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/base_events.py", line 725, in run_until_complete
    return future.result()
           ~~~~~~~~~~~~~^^
  File "/app/test/test_import_task_contract.py", line 406, in scenario
    self.assert_error(get_payload, code="INVALID_ARGUMENT", error_type="validation_error")
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/test/base.py", line 62, in assert_error
    self.assertFalse(payload.get("success"), payload)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: True is not false : {'success': True, 'code': 'OK', 'message': 'success', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-08T09:22:52.145938+00:00', 'data': {'task': {'id': 127, 'task_uid': 'cc6de5b4-9618-4548-a218-f2974ca75fd4', 'task_type': 'document_import_batch', 'status': 'queued', 'priority': 50, 'cancel_requested': False, 'idempotency_key': None, 'request_id': None, 'operator': None, 'trace_id': None, 'total_items': 1, 'pending_items': 1, 'running_items': 0, 'success_items': 0, 'failed_items': 0, 'canceled_items': 0, 'progress_percent': 0.0, 'attempt_count': 0, 'max_attempts': 3, 'started_at': None, 'finished_at': None, 'heartbeat_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:52.125511', 'updated_at': '2026-04-08T09:22:52.125514', 'items': [{'id': 266, 'item_no': 1, 'status': 'pending', 'priority': 50, 'category_id': 252, 'title': 'batch_mismatch_1775640172114_281473577342624', 'file_name': 'Functional_Analysis.pdf', 'mime_type': 'application/pdf', 'file_sha256': 'e27cc09ecbeb8ac295697bec3fe07bc24c671b8c69cfdffe3b7c05fc3f2a8060', 'document_id': None, 'document_uid': None, 'attempt_count': 0, 'started_at': None, 'finished_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:52.127713', 'updated_at': '2026-04-08T09:22:52.127715'}]}}}
```

### 失败: test_import_task_contract.ImportTaskContractTestCase.test_batch_submit_rejects_invalid_category

```text
Traceback (most recent call last):
  File "/app/test/test_import_task_contract.py", line 245, in test_batch_submit_rejects_invalid_category
    self.run_async(scenario())
    ~~~~~~~~~~~~~~^^^^^^^^^^^^
  File "/app/test/base.py", line 28, in run_async
    return asyncio.run(coroutine)
           ~~~~~~~~~~~^^^^^^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 195, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/base_events.py", line 725, in run_until_complete
    return future.result()
           ~~~~~~~~~~~~~^^
  File "/app/test/test_import_task_contract.py", line 243, in scenario
    self.assert_error(payload, code="CATEGORY_NOT_FOUND", error_type="not_found")
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/test/base.py", line 62, in assert_error
    self.assertFalse(payload.get("success"), payload)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: True is not false : {'success': True, 'code': 'OK', 'message': 'success', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-08T09:22:52.608816+00:00', 'data': {'task': {'id': 132, 'task_uid': 'a0f6b0cf-f05d-4420-bfb4-85dca024233c', 'task_type': 'document_import_batch', 'status': 'queued', 'priority': 50, 'cancel_requested': False, 'idempotency_key': None, 'request_id': None, 'operator': None, 'trace_id': None, 'total_items': 1, 'pending_items': 1, 'running_items': 0, 'success_items': 0, 'failed_items': 0, 'canceled_items': 0, 'progress_percent': 0.0, 'attempt_count': 0, 'max_attempts': 3, 'started_at': None, 'finished_at': None, 'heartbeat_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:52.605456', 'updated_at': '2026-04-08T09:22:52.605459', 'items': [{'id': 271, 'item_no': 1, 'status': 'pending', 'priority': 50, 'category_id': 99999999, 'title': 'batch_invalid_cat_1775640172594_281473578329520', 'file_name': 'Functional_Analysis.pdf', 'mime_type': 'application/pdf', 'file_sha256': 'e27cc09ecbeb8ac295697bec3fe07bc24c671b8c69cfdffe3b7c05fc3f2a8060', 'document_id': None, 'document_uid': None, 'attempt_count': 0, 'started_at': None, 'finished_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:52.607586', 'updated_at': '2026-04-08T09:22:52.607588'}]}}}
```

### 失败: test_import_task_contract.ImportTaskContractTestCase.test_concurrent_batch_submit_same_idempotency_key

```text
Traceback (most recent call last):
  File "/app/test/test_import_task_contract.py", line 623, in test_concurrent_batch_submit_same_idempotency_key
    self.run_async(scenario())
    ~~~~~~~~~~~~~~^^^^^^^^^^^^
  File "/app/test/base.py", line 28, in run_async
    return asyncio.run(coroutine)
           ~~~~~~~~~~~^^^^^^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 195, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/base_events.py", line 725, in run_until_complete
    return future.result()
           ~~~~~~~~~~~~~^^
  File "/app/test/test_import_task_contract.py", line 616, in scenario
    self.assertEqual(len(success_results), 1, results)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 5 != 1 : [{'success': True, 'code': 'OK', 'message': 'success', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-08T09:22:57.881957+00:00', 'data': {'task': {'id': 146, 'task_uid': '1dba7a9f-8822-4a9b-8f95-460530f7f550', 'task_type': 'document_import_batch', 'status': 'queued', 'priority': 50, 'cancel_requested': False, 'idempotency_key': 'concurrent_idem_1775640177810_281473576986960', 'request_id': None, 'operator': None, 'trace_id': None, 'total_items': 1, 'pending_items': 1, 'running_items': 0, 'success_items': 0, 'failed_items': 0, 'canceled_items': 0, 'progress_percent': 0.0, 'attempt_count': 0, 'max_attempts': 3, 'started_at': None, 'finished_at': None, 'heartbeat_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:57.878723', 'updated_at': '2026-04-08T09:22:57.878726', 'items': [{'id': 289, 'item_no': 1, 'status': 'pending', 'priority': 50, 'category_id': 271, 'title': 'concurrent_idem_item_0_1775640177837_281473576986960', 'file_name': 'Functional_Analysis.pdf', 'mime_type': 'application/pdf', 'file_sha256': 'e27cc09ecbeb8ac295697bec3fe07bc24c671b8c69cfdffe3b7c05fc3f2a8060', 'document_id': None, 'document_uid': None, 'attempt_count': 0, 'started_at': None, 'finished_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:57.880724', 'updated_at': '2026-04-08T09:22:57.880726'}]}}}, {'success': True, 'code': 'OK', 'message': 'success', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-08T09:22:57.883552+00:00', 'data': {'task': {'id': 146, 'task_uid': '1dba7a9f-8822-4a9b-8f95-460530f7f550', 'task_type': 'document_import_batch', 'status': 'queued', 'priority': 50, 'cancel_requested': False, 'idempotency_key': 'concurrent_idem_1775640177810_281473576986960', 'request_id': None, 'operator': None, 'trace_id': None, 'total_items': 1, 'pending_items': 1, 'running_items': 0, 'success_items': 0, 'failed_items': 0, 'canceled_items': 0, 'progress_percent': 0.0, 'attempt_count': 0, 'max_attempts': 3, 'started_at': None, 'finished_at': None, 'heartbeat_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:57.878723', 'updated_at': '2026-04-08T09:22:57.878726', 'items': [{'id': 289, 'item_no': 1, 'status': 'pending', 'priority': 50, 'category_id': 271, 'title': 'concurrent_idem_item_0_1775640177837_281473576986960', 'file_name': 'Functional_Analysis.pdf', 'mime_type': 'application/pdf', 'file_sha256': 'e27cc09ecbeb8ac295697bec3fe07bc24c671b8c69cfdffe3b7c05fc3f2a8060', 'document_id': None, 'document_uid': None, 'attempt_count': 0, 'started_at': None, 'finished_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:57.880724', 'updated_at': '2026-04-08T09:22:57.880726'}]}}}, {'success': True, 'code': 'OK', 'message': 'success', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-08T09:22:57.884794+00:00', 'data': {'task': {'id': 146, 'task_uid': '1dba7a9f-8822-4a9b-8f95-460530f7f550', 'task_type': 'document_import_batch', 'status': 'queued', 'priority': 50, 'cancel_requested': False, 'idempotency_key': 'concurrent_idem_1775640177810_281473576986960', 'request_id': None, 'operator': None, 'trace_id': None, 'total_items': 1, 'pending_items': 1, 'running_items': 0, 'success_items': 0, 'failed_items': 0, 'canceled_items': 0, 'progress_percent': 0.0, 'attempt_count': 0, 'max_attempts': 3, 'started_at': None, 'finished_at': None, 'heartbeat_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:57.878723', 'updated_at': '2026-04-08T09:22:57.878726', 'items': [{'id': 289, 'item_no': 1, 'status': 'pending', 'priority': 50, 'category_id': 271, 'title': 'concurrent_idem_item_0_1775640177837_281473576986960', 'file_name': 'Functional_Analysis.pdf', 'mime_type': 'application/pdf', 'file_sha256': 'e27cc09ecbeb8ac295697bec3fe07bc24c671b8c69cfdffe3b7c05fc3f2a8060', 'document_id': None, 'document_uid': None, 'attempt_count': 0, 'started_at': None, 'finished_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:57.880724', 'updated_at': '2026-04-08T09:22:57.880726'}]}}}, {'success': True, 'code': 'OK', 'message': 'success', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-08T09:22:57.887993+00:00', 'data': {'task': {'id': 146, 'task_uid': '1dba7a9f-8822-4a9b-8f95-460530f7f550', 'task_type': 'document_import_batch', 'status': 'queued', 'priority': 50, 'cancel_requested': False, 'idempotency_key': 'concurrent_idem_1775640177810_281473576986960', 'request_id': None, 'operator': None, 'trace_id': None, 'total_items': 1, 'pending_items': 1, 'running_items': 0, 'success_items': 0, 'failed_items': 0, 'canceled_items': 0, 'progress_percent': 0.0, 'attempt_count': 0, 'max_attempts': 3, 'started_at': None, 'finished_at': None, 'heartbeat_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:57.878723', 'updated_at': '2026-04-08T09:22:57.878726', 'items': [{'id': 289, 'item_no': 1, 'status': 'pending', 'priority': 50, 'category_id': 271, 'title': 'concurrent_idem_item_0_1775640177837_281473576986960', 'file_name': 'Functional_Analysis.pdf', 'mime_type': 'application/pdf', 'file_sha256': 'e27cc09ecbeb8ac295697bec3fe07bc24c671b8c69cfdffe3b7c05fc3f2a8060', 'document_id': None, 'document_uid': None, 'attempt_count': 0, 'started_at': None, 'finished_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:57.880724', 'updated_at': '2026-04-08T09:22:57.880726'}]}}}, {'success': True, 'code': 'OK', 'message': 'success', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-08T09:22:57.889396+00:00', 'data': {'task': {'id': 146, 'task_uid': '1dba7a9f-8822-4a9b-8f95-460530f7f550', 'task_type': 'document_import_batch', 'status': 'queued', 'priority': 50, 'cancel_requested': False, 'idempotency_key': 'concurrent_idem_1775640177810_281473576986960', 'request_id': None, 'operator': None, 'trace_id': None, 'total_items': 1, 'pending_items': 1, 'running_items': 0, 'success_items': 0, 'failed_items': 0, 'canceled_items': 0, 'progress_percent': 0.0, 'attempt_count': 0, 'max_attempts': 3, 'started_at': None, 'finished_at': None, 'heartbeat_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:57.878723', 'updated_at': '2026-04-08T09:22:57.878726', 'items': [{'id': 289, 'item_no': 1, 'status': 'pending', 'priority': 50, 'category_id': 271, 'title': 'concurrent_idem_item_0_1775640177837_281473576986960', 'file_name': 'Functional_Analysis.pdf', 'mime_type': 'application/pdf', 'file_sha256': 'e27cc09ecbeb8ac295697bec3fe07bc24c671b8c69cfdffe3b7c05fc3f2a8060', 'document_id': None, 'document_uid': None, 'attempt_count': 0, 'started_at': None, 'finished_at': None, 'last_error': None, 'created_at': '2026-04-08T09:22:57.880724', 'updated_at': '2026-04-08T09:22:57.880726'}]}}}]
```

### 失败: test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_batch_submit_file_name_at_max_length

```text
Traceback (most recent call last):
  File "/app/test/test_import_task_production_edge_cases.py", line 188, in test_batch_submit_file_name_at_max_length
    self.run_async(scenario())
    ~~~~~~~~~~~~~~^^^^^^^^^^^^
  File "/app/test/base.py", line 28, in run_async
    return asyncio.run(coroutine)
           ~~~~~~~~~~~^^^^^^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 195, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/base_events.py", line 725, in run_until_complete
    return future.result()
           ~~~~~~~~~~~~~^^
  File "/app/test/test_import_task_production_edge_cases.py", line 184, in scenario
    self.assert_success(payload)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^^
  File "/app/test/base.py", line 50, in assert_success
    self.assertTrue(payload.get("success"), payload)
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : {'success': False, 'code': 'INTERNAL_ERROR', 'message': 'internal server error', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-08T09:22:58.753662+00:00', 'error': {'type': 'system_error', 'details': {'error': "[Errno 36] File name too long: '/app/data/storage/_tasks/8680d30a-a85f-44af-8c99-043ba8e0fa6d/000001_863e00575ca94c998065cfe921769533_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.pdf'"}}}
```

### 错误: test_import_task_production_edge_cases.ProductionEdgeCaseTestCase.test_mixed_operations_concurrent_stress

```text
Traceback (most recent call last):
  File "/app/test/test_import_task_production_edge_cases.py", line 381, in test_mixed_operations_concurrent_stress
    self.run_async(scenario())
    ~~~~~~~~~~~~~~^^^^^^^^^^^^
  File "/app/test/base.py", line 28, in run_async
    return asyncio.run(coroutine)
           ~~~~~~~~~~~^^^^^^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 195, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/asyncio/base_events.py", line 725, in run_until_complete
    return future.result()
           ~~~~~~~~~~~~~^^
  File "/app/test/test_import_task_production_edge_cases.py", line 375, in scenario
    self.assertTrue(r.get("success"), r)
                    ^^^^^
AttributeError: 'str' object has no attribute 'get'
```
