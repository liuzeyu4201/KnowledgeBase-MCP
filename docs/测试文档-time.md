# 测试文档

- 生成时间: 2026-04-07T10:43:33.469369
- Python: 3.13.12
- 平台: Linux-6.12.76-linuxkit-aarch64-with-glibc2.41
- 执行用例总数: 19
- 通过: 11
- 失败: 8
- 错误: 0
- 跳过: 0

## 关键问题摘要

- 参数校验类请求在部分接口上没有按统一 JSON 错误协议返回，而是被 MCP 包装成 `MCP_TOOL_EXECUTION_ERROR`。当前已复现于：
  - `kb_category_create` 非法 `category_code`
  - `kb_document_import` 非法 `mime_type`
  - `kb_search_retrieve` 空白 `query`
- 文档导入链路对 [Functional_Analysis.pdf](/Users/token/Projects/KnowledgeBase/KnowledgeBase/data/Functional_Analysis.pdf) 失败。根因是切片文本中包含 PostgreSQL 不接受的 `NUL (0x00)` 字节，导致 `kb_chunk.content` 插入失败，并进一步影响：
  - 文档导入基本流程
  - 依赖该样例 PDF 的分类删除保护测试
  - 文档元数据更新测试
- 检索质量方面，长文档英文 BM25 精确术语检索正常，但以下问答型场景未达到预期：
  - `what is Hilbert space?` 在 `alpha=1.0` 时，定义片段未进入 Top 3
  - `什么是希尔伯特空间` 在 `alpha=0.5` 时，Top 3 未召回 Hilbert space 相关片段

## 复现环境

- 分支：`test`
- 编排方式：`docker-compose.dev.yml`
- 测试入口：`docker exec knowledgebase-app-dev sh -lc 'cd /app && /opt/venv/bin/python -m test.run_suite'`

## 执行摘要

```text
test_category_create_rejects_duplicate_code (test_category_contract.CategoryContractTestCase.test_category_create_rejects_duplicate_code) ... ok
test_category_create_rejects_invalid_code (test_category_contract.CategoryContractTestCase.test_category_create_rejects_invalid_code) ... FAIL
test_category_crud_smoke (test_category_contract.CategoryContractTestCase.test_category_crud_smoke) ... ok
test_category_get_requires_identifier (test_category_contract.CategoryContractTestCase.test_category_get_requires_identifier) ... ok
test_category_list_rejects_page_size_over_limit (test_category_contract.CategoryContractTestCase.test_category_list_rejects_page_size_over_limit) ... ok
test_concurrent_duplicate_category_create_should_only_return_business_conflict (test_concurrency_pressure.ConcurrencyAndPressureTestCase.test_concurrent_duplicate_category_create_should_only_return_business_conflict) ... ok
test_high_concurrency_search_requests_all_succeed (test_concurrency_pressure.ConcurrencyAndPressureTestCase.test_high_concurrency_search_requests_all_succeed) ... ok
test_sequential_search_pressure_burst (test_concurrency_pressure.ConcurrencyAndPressureTestCase.test_sequential_search_pressure_burst) ... ok
test_category_delete_rejects_active_documents (test_document_contract.DocumentContractTestCase.test_category_delete_rejects_active_documents) ... FAIL
test_document_import_get_list_delete_smoke (test_document_contract.DocumentContractTestCase.test_document_import_get_list_delete_smoke) ... FAIL
test_document_import_rejects_invalid_base64 (test_document_contract.DocumentContractTestCase.test_document_import_rejects_invalid_base64) ... ok
test_document_import_rejects_invalid_category (test_document_contract.DocumentContractTestCase.test_document_import_rejects_invalid_category) ... ok
test_document_import_rejects_invalid_mime_type (test_document_contract.DocumentContractTestCase.test_document_import_rejects_invalid_mime_type) ... FAIL
test_document_update_metadata_only (test_document_contract.DocumentContractTestCase.test_document_update_metadata_only) ... FAIL
test_bm25_exact_theorem_query_hits_expected_chunk (test_search_contract.SearchContractTestCase.test_bm25_exact_theorem_query_hits_expected_chunk) ... ok
test_bm25_natural_question_should_return_hilbert_definition_in_top3 (test_search_contract.SearchContractTestCase.test_bm25_natural_question_should_return_hilbert_definition_in_top3) ... FAIL
test_hybrid_search_chinese_query_should_hit_hilbert_section_in_top3 (test_search_contract.SearchContractTestCase.test_hybrid_search_chinese_query_should_hit_hilbert_section_in_top3) ... FAIL
test_search_rejects_empty_query (test_search_contract.SearchContractTestCase.test_search_rejects_empty_query) ... FAIL
test_search_rejects_invalid_alpha (test_search_contract.SearchContractTestCase.test_search_rejects_invalid_alpha) ... ok

======================================================================
FAIL: test_category_create_rejects_invalid_code (test_category_contract.CategoryContractTestCase.test_category_create_rejects_invalid_code)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/test/test_category_contract.py", line 57, in test_category_create_rejects_invalid_code
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
  File "/app/test/test_category_contract.py", line 55, in scenario
    self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/test/base.py", line 64, in assert_error
    self.assertEqual(payload.get("code"), code, payload)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'MCP_TOOL_EXECUTION_ERROR' != 'INVALID_ARGUMENT'
- MCP_TOOL_EXECUTION_ERROR
+ INVALID_ARGUMENT
 : {'success': False, 'code': 'MCP_TOOL_EXECUTION_ERROR', 'message': "Error executing tool kb_category_create: Unable to serialize unknown type: <class 'ValueError'>", 'error': {'type': 'tool_execution_error', 'details': {}}}

======================================================================
FAIL: test_category_delete_rejects_active_documents (test_document_contract.DocumentContractTestCase.test_category_delete_rejects_active_documents)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/test/test_document_contract.py", line 106, in test_category_delete_rejects_active_documents
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
  File "/app/test/test_document_contract.py", line 98, in scenario
    document = await self.import_document(category_id=category["id"], title_prefix="guard_doc")
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/test/base.py", line 100, in import_document
    self.assert_success(payload)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^^
  File "/app/test/base.py", line 50, in assert_success
    self.assertTrue(payload.get("success"), payload)
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : {'success': False, 'code': 'DOCUMENT_IMPORT_FAILED', 'message': 'document import failed', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-07T10:42:27.853633+00:00', 'error': {'type': 'system_error', 'details': {'error': "(psycopg.DataError) PostgreSQL text fields cannot contain NUL (0x00) bytes\n[SQL: INSERT INTO kb_chunk (chunk_uid, document_id, chunk_no, page_no, char_start, char_end, token_count, content, content_hash, embedding_model, vector_version, vector_status, metadata_json, created_at, updated_at, deleted_at) SELECT p0::VARCHAR, p1::BIGI ... 34390 characters truncated ... 1, p12, p13, p14, p15, sen_counter) ORDER BY sen_counter RETURNING kb_chunk.id, kb_chunk.id AS id__1]\n[parameters: {'char_end__0': 23, 'page_no__0': 1, 'token_count__0': 11, 'updated_at__0': datetime.datetime(2026, 4, 7, 10, 42, 27, 850961), 'chunk_uid__0': 'fe09a718-9b1c-4cc0-8b6c-a93b8f9ba487', 'char_start__0': 0, 'metadata_json__0': Jsonb({'page_no': 1}), 'chunk_no__0': 0, 'document_id__0': 37, 'vector_version__0': 1, 'created_at__0': datetime.datetime(2026, 4, 7, 10, 42, 27, 850958), 'deleted_at__0': None, 'vector_status__0': 'ready', 'content_hash__0': 'f6ada8c06323952705736deb3dc1a87cbefab9120af166aaa34b7866323189f5', 'embedding_model__0': 'mock-embedding', 'content__0': '泛函分析\\n孙天阳\\n2023 年 6 月 8 日', 'char_end__1': 800, 'page_no__1': 2, 'token_count__1': 399, 'updated_at__1': datetime.datetime(2026, 4, 7, 10, 42, 27, 850965), 'chunk_uid__1': '841572cc-92b7-449c-99a0-9cdca4f7d5de', 'char_start__1': 0, 'metadata_json__1': Jsonb({'page_no': 2}), 'chunk_no__1': 1, 'document_id__1': 37, 'vector_version__1': 1, 'created_at__1': datetime.datetime(2026, 4, 7, 10, 42, 27, 850965), 'deleted_at__1': None, 'vector_status__1': 'ready', 'content_hash__1': '657d2ae6c721eeab710a87be1dab3bce2156ea47556abfb9f7e355c4dcdb26ec', 'embedding_model__1': 'mock-embedding', 'content__1': '目录\\n目录 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 2\\n1 拓扑线性空间 3\\n1 局部凸空间 . . . . . . . . . . . . ... (512 characters truncated) ...  . . . . . . . . . . . 7\\n4.2 有限维赋范线性空间的刻画 . . . . . . . . . . . . . . . . . . . . . . . . . . . . 8\\n4.3 商空间 . . . . . . . . . . . . . . . . . . . .', 'char_end__2': 1500, 'page_no__2': 2, 'token_count__2': 400, 'updated_at__2': datetime.datetime(2026, 4, 7, 10, 42, 27, 850969), 'chunk_uid__2': 'bd36b21e-e844-4179-afa2-f1971cb9079c', 'char_start__2': 700, 'metadata_json__2': Jsonb({'page_no': 2}), 'chunk_no__2': 2, 'document_id__2': 37, 'vector_version__2': 1, 'created_at__2': datetime.datetime(2026, 4, 7, 10, 42, 27, 850968), 'deleted_at__2': None, 'vector_status__2': 'ready', 'content_hash__2': '1a89193837bea0aace5da4f9bf338a590ad8d6736db479f98c380a3eb1740860', 'embedding_model__2': 'mock-embedding', 'content__2': '. . . . . . . . . . . . . . . . . . . . . . . . . 8\\n4.3 商空间 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 8\\n5 凸集与 ... (513 characters truncated) ...  . . . . . . . . . . . . 12\\n3 拓扑线性空间 13\\n4 线性算子 14\\n1 线性算子的概念 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 14\\n2 下有', 'char_end__3': 2200, 'page_no__3': 2 ... 924 parameters truncated ... 'embedding_model__60': 'mock-embedding', 'content__60': 'CHAPTER 7. BANACH 代数 43\\n2 谱\\n定义 2.1. 设 A 是 Banach 代数 U 中的元素， 定义了A 的谱值是什么， 即没有双边逆. 但是它似乎\\n没有区分什么连续谱什么剩余谱什么点谱之类.', 'char_end__61': 36, 'page_no__61': 45, 'token_count__61': 18, 'updated_at__61': datetime.datetime(2026, 4, 7, 10, 42, 27, 851116), 'chunk_uid__61': '560f0261-b92b-483a-a667-309421ae3efa', 'char_start__61': 0, 'metadata_json__61': Jsonb({'page_no': 45}), 'chunk_no__61': 61, 'document_id__61': 37, 'vector_version__61': 1, 'created_at__61': datetime.datetime(2026, 4, 7, 10, 42, 27, 851115), 'deleted_at__61': None, 'vector_status__61': 'ready', 'content_hash__61': '55da88492ebc0a89ae01461ec940117196d2b72abc1a031ebc412d199c4d92a9', 'embedding_model__61': 'mock-embedding', 'content__61': '附录 A\\n泛函分析中的反例\\n1 纲\\n• 第一纲集但不无处稠密：Q.\\n44', 'char_end__62': 148, 'page_no__62': 46, 'token_count__62': 74, 'updated_at__62': datetime.datetime(2026, 4, 7, 10, 42, 27, 851118), 'chunk_uid__62': '5d05faa8-65e0-4018-ab92-122950f8f16b', 'char_start__62': 0, 'metadata_json__62': Jsonb({'page_no': 46}), 'chunk_no__62': 62, 'document_id__62': 37, 'vector_version__62': 1, 'created_at__62': datetime.datetime(2026, 4, 7, 10, 42, 27, 851118), 'deleted_at__62': None, 'vector_status__62': 'ready', 'content_hash__62': 'c9811b7d76f2fe68f17d1933ea35b02b00f408072c5b7cb0174e0e28a885db35', 'embedding_model__62': 'mock-embedding', 'content__62': '附录 A. 泛函分析中的反例 45\\n2 映射\\n• 逆映射不连续\\n3\\n定理 3.1 (Riesz 表示定理).\\nLax-Milgram 定理可看作将内积改为满足强制条件 a(u; u) ⩾ \\x0ekuk2 的连续共轭双线性泛函\\na(u; v) 的推广.\\n定理 3.2 (Lax-Milgram 定理).', 'char_end__63': 390, 'page_no__63': 47, 'token_count__63': 195, 'updated_at__63': datetime.datetime(2026, 4, 7, 10, 42, 27, 851121), 'chunk_uid__63': '071847b2-5f4e-4ab3-b193-34cee25adf96', 'char_start__63': 0, 'metadata_json__63': Jsonb({'page_no': 47}), 'chunk_no__63': 63, 'document_id__63': 37, 'vector_version__63': 1, 'created_at__63': datetime.datetime(2026, 4, 7, 10, 42, 27, 851120), 'deleted_at__63': None, 'vector_status__63': 'ready', 'content_hash__63': 'cfb271fb79bfdeff7f25452a60a8a06777067bb6dab9bb82f45de5e180c5d0d7', 'embedding_model__63': 'mock-embedding', 'content__63': '附录 B\\n套路\\n1 有机会成为一组的东西\\n• 最佳逼近元\\n– 设 X 是赋范线性空间，M 是 X 的有限维子空间， 那么对于任意x 2 X，x 到 M 的距离\\n的最小值能取到.\\n– 如果 M 仅仅是闭子空间，那么虽然可以任意精度逼近，但可能取不到.\\n• 对象分解\\n– 设 X 是 B ... (109 characters truncated) ... 任意 g 2 Y ∗，g(T xn) ! g(y).\\n• T ∗g(xn) ! g(y).\\n• 也就是说，我知道了一部分 X ∗ 中的元素，作用在 fxng 上时，的收敛性.\\n比较，已知 xn 弱收敛到 x，\\n• 我就知道了所有 X ∗ 中的元素，作用在 fxng 上时，的收敛性.\\n46'}]\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"}}}

======================================================================
FAIL: test_document_import_get_list_delete_smoke (test_document_contract.DocumentContractTestCase.test_document_import_get_list_delete_smoke)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/test/test_document_contract.py", line 43, in test_document_import_get_list_delete_smoke
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
  File "/app/test/test_document_contract.py", line 12, in scenario
    document = await self.import_document(
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
    )
    ^
  File "/app/test/base.py", line 100, in import_document
    self.assert_success(payload)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^^
  File "/app/test/base.py", line 50, in assert_success
    self.assertTrue(payload.get("success"), payload)
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : {'success': False, 'code': 'DOCUMENT_IMPORT_FAILED', 'message': 'document import failed', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-07T10:42:28.143636+00:00', 'error': {'type': 'system_error', 'details': {'error': "(psycopg.DataError) PostgreSQL text fields cannot contain NUL (0x00) bytes\n[SQL: INSERT INTO kb_chunk (chunk_uid, document_id, chunk_no, page_no, char_start, char_end, token_count, content, content_hash, embedding_model, vector_version, vector_status, metadata_json, created_at, updated_at, deleted_at) SELECT p0::VARCHAR, p1::BIGI ... 34390 characters truncated ... 1, p12, p13, p14, p15, sen_counter) ORDER BY sen_counter RETURNING kb_chunk.id, kb_chunk.id AS id__1]\n[parameters: {'char_end__0': 23, 'page_no__0': 1, 'token_count__0': 11, 'updated_at__0': datetime.datetime(2026, 4, 7, 10, 42, 28, 141166), 'chunk_uid__0': '23805b09-ec09-4a37-92ed-fe0fbbe9b8d3', 'char_start__0': 0, 'metadata_json__0': Jsonb({'page_no': 1}), 'chunk_no__0': 0, 'document_id__0': 38, 'vector_version__0': 1, 'created_at__0': datetime.datetime(2026, 4, 7, 10, 42, 28, 141163), 'deleted_at__0': None, 'vector_status__0': 'ready', 'content_hash__0': 'f6ada8c06323952705736deb3dc1a87cbefab9120af166aaa34b7866323189f5', 'embedding_model__0': 'mock-embedding', 'content__0': '泛函分析\\n孙天阳\\n2023 年 6 月 8 日', 'char_end__1': 800, 'page_no__1': 2, 'token_count__1': 399, 'updated_at__1': datetime.datetime(2026, 4, 7, 10, 42, 28, 141170), 'chunk_uid__1': '172c3ea9-d433-4e70-99a4-8405605fc5e2', 'char_start__1': 0, 'metadata_json__1': Jsonb({'page_no': 2}), 'chunk_no__1': 1, 'document_id__1': 38, 'vector_version__1': 1, 'created_at__1': datetime.datetime(2026, 4, 7, 10, 42, 28, 141169), 'deleted_at__1': None, 'vector_status__1': 'ready', 'content_hash__1': '657d2ae6c721eeab710a87be1dab3bce2156ea47556abfb9f7e355c4dcdb26ec', 'embedding_model__1': 'mock-embedding', 'content__1': '目录\\n目录 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 2\\n1 拓扑线性空间 3\\n1 局部凸空间 . . . . . . . . . . . . ... (512 characters truncated) ...  . . . . . . . . . . . 7\\n4.2 有限维赋范线性空间的刻画 . . . . . . . . . . . . . . . . . . . . . . . . . . . . 8\\n4.3 商空间 . . . . . . . . . . . . . . . . . . . .', 'char_end__2': 1500, 'page_no__2': 2, 'token_count__2': 400, 'updated_at__2': datetime.datetime(2026, 4, 7, 10, 42, 28, 141173), 'chunk_uid__2': '61665c07-2ff5-4c4a-91d0-d239986ea3e8', 'char_start__2': 700, 'metadata_json__2': Jsonb({'page_no': 2}), 'chunk_no__2': 2, 'document_id__2': 38, 'vector_version__2': 1, 'created_at__2': datetime.datetime(2026, 4, 7, 10, 42, 28, 141172), 'deleted_at__2': None, 'vector_status__2': 'ready', 'content_hash__2': '1a89193837bea0aace5da4f9bf338a590ad8d6736db479f98c380a3eb1740860', 'embedding_model__2': 'mock-embedding', 'content__2': '. . . . . . . . . . . . . . . . . . . . . . . . . 8\\n4.3 商空间 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 8\\n5 凸集与 ... (513 characters truncated) ...  . . . . . . . . . . . . 12\\n3 拓扑线性空间 13\\n4 线性算子 14\\n1 线性算子的概念 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 14\\n2 下有', 'char_end__3': 2200, 'page_no__3': 2 ... 924 parameters truncated ... 'embedding_model__60': 'mock-embedding', 'content__60': 'CHAPTER 7. BANACH 代数 43\\n2 谱\\n定义 2.1. 设 A 是 Banach 代数 U 中的元素， 定义了A 的谱值是什么， 即没有双边逆. 但是它似乎\\n没有区分什么连续谱什么剩余谱什么点谱之类.', 'char_end__61': 36, 'page_no__61': 45, 'token_count__61': 18, 'updated_at__61': datetime.datetime(2026, 4, 7, 10, 42, 28, 141317), 'chunk_uid__61': 'ce47a8a6-4f05-400b-9a99-30e6b1d5ca2c', 'char_start__61': 0, 'metadata_json__61': Jsonb({'page_no': 45}), 'chunk_no__61': 61, 'document_id__61': 38, 'vector_version__61': 1, 'created_at__61': datetime.datetime(2026, 4, 7, 10, 42, 28, 141317), 'deleted_at__61': None, 'vector_status__61': 'ready', 'content_hash__61': '55da88492ebc0a89ae01461ec940117196d2b72abc1a031ebc412d199c4d92a9', 'embedding_model__61': 'mock-embedding', 'content__61': '附录 A\\n泛函分析中的反例\\n1 纲\\n• 第一纲集但不无处稠密：Q.\\n44', 'char_end__62': 148, 'page_no__62': 46, 'token_count__62': 74, 'updated_at__62': datetime.datetime(2026, 4, 7, 10, 42, 28, 141319), 'chunk_uid__62': 'bdd12081-6e0a-465f-8538-e5f7e4c29606', 'char_start__62': 0, 'metadata_json__62': Jsonb({'page_no': 46}), 'chunk_no__62': 62, 'document_id__62': 38, 'vector_version__62': 1, 'created_at__62': datetime.datetime(2026, 4, 7, 10, 42, 28, 141319), 'deleted_at__62': None, 'vector_status__62': 'ready', 'content_hash__62': 'c9811b7d76f2fe68f17d1933ea35b02b00f408072c5b7cb0174e0e28a885db35', 'embedding_model__62': 'mock-embedding', 'content__62': '附录 A. 泛函分析中的反例 45\\n2 映射\\n• 逆映射不连续\\n3\\n定理 3.1 (Riesz 表示定理).\\nLax-Milgram 定理可看作将内积改为满足强制条件 a(u; u) ⩾ \\x0ekuk2 的连续共轭双线性泛函\\na(u; v) 的推广.\\n定理 3.2 (Lax-Milgram 定理).', 'char_end__63': 390, 'page_no__63': 47, 'token_count__63': 195, 'updated_at__63': datetime.datetime(2026, 4, 7, 10, 42, 28, 141322), 'chunk_uid__63': 'ad641242-3007-41f6-add4-3dfcf2f3be09', 'char_start__63': 0, 'metadata_json__63': Jsonb({'page_no': 47}), 'chunk_no__63': 63, 'document_id__63': 38, 'vector_version__63': 1, 'created_at__63': datetime.datetime(2026, 4, 7, 10, 42, 28, 141321), 'deleted_at__63': None, 'vector_status__63': 'ready', 'content_hash__63': 'cfb271fb79bfdeff7f25452a60a8a06777067bb6dab9bb82f45de5e180c5d0d7', 'embedding_model__63': 'mock-embedding', 'content__63': '附录 B\\n套路\\n1 有机会成为一组的东西\\n• 最佳逼近元\\n– 设 X 是赋范线性空间，M 是 X 的有限维子空间， 那么对于任意x 2 X，x 到 M 的距离\\n的最小值能取到.\\n– 如果 M 仅仅是闭子空间，那么虽然可以任意精度逼近，但可能取不到.\\n• 对象分解\\n– 设 X 是 B ... (109 characters truncated) ... 任意 g 2 Y ∗，g(T xn) ! g(y).\\n• T ∗g(xn) ! g(y).\\n• 也就是说，我知道了一部分 X ∗ 中的元素，作用在 fxng 上时，的收敛性.\\n比较，已知 xn 弱收敛到 x，\\n• 我就知道了所有 X ∗ 中的元素，作用在 fxng 上时，的收敛性.\\n46'}]\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"}}}

======================================================================
FAIL: test_document_import_rejects_invalid_mime_type (test_document_contract.DocumentContractTestCase.test_document_import_rejects_invalid_mime_type)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/test/test_document_contract.py", line 75, in test_document_import_rejects_invalid_mime_type
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
  File "/app/test/test_document_contract.py", line 71, in scenario
    self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/test/base.py", line 64, in assert_error
    self.assertEqual(payload.get("code"), code, payload)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'MCP_TOOL_EXECUTION_ERROR' != 'INVALID_ARGUMENT'
- MCP_TOOL_EXECUTION_ERROR
+ INVALID_ARGUMENT
 : {'success': False, 'code': 'MCP_TOOL_EXECUTION_ERROR', 'message': "Error executing tool kb_document_import: Unable to serialize unknown type: <class 'ValueError'>", 'error': {'type': 'tool_execution_error', 'details': {}}}

======================================================================
FAIL: test_document_update_metadata_only (test_document_contract.DocumentContractTestCase.test_document_update_metadata_only)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/test/test_document_contract.py", line 132, in test_document_update_metadata_only
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
  File "/app/test/test_document_contract.py", line 112, in scenario
    document = await self.import_document(
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
    )
    ^
  File "/app/test/base.py", line 100, in import_document
    self.assert_success(payload)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^^
  File "/app/test/base.py", line 50, in assert_success
    self.assertTrue(payload.get("success"), payload)
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : {'success': False, 'code': 'DOCUMENT_IMPORT_FAILED', 'message': 'document import failed', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-07T10:42:28.634141+00:00', 'error': {'type': 'system_error', 'details': {'error': "(psycopg.DataError) PostgreSQL text fields cannot contain NUL (0x00) bytes\n[SQL: INSERT INTO kb_chunk (chunk_uid, document_id, chunk_no, page_no, char_start, char_end, token_count, content, content_hash, embedding_model, vector_version, vector_status, metadata_json, created_at, updated_at, deleted_at) SELECT p0::VARCHAR, p1::BIGI ... 34390 characters truncated ... 1, p12, p13, p14, p15, sen_counter) ORDER BY sen_counter RETURNING kb_chunk.id, kb_chunk.id AS id__1]\n[parameters: {'char_end__0': 23, 'page_no__0': 1, 'token_count__0': 11, 'updated_at__0': datetime.datetime(2026, 4, 7, 10, 42, 28, 631523), 'chunk_uid__0': 'f3b2616e-1004-4f93-96b9-0002feb4dbd6', 'char_start__0': 0, 'metadata_json__0': Jsonb({'page_no': 1}), 'chunk_no__0': 0, 'document_id__0': 39, 'vector_version__0': 1, 'created_at__0': datetime.datetime(2026, 4, 7, 10, 42, 28, 631520), 'deleted_at__0': None, 'vector_status__0': 'ready', 'content_hash__0': 'f6ada8c06323952705736deb3dc1a87cbefab9120af166aaa34b7866323189f5', 'embedding_model__0': 'mock-embedding', 'content__0': '泛函分析\\n孙天阳\\n2023 年 6 月 8 日', 'char_end__1': 800, 'page_no__1': 2, 'token_count__1': 399, 'updated_at__1': datetime.datetime(2026, 4, 7, 10, 42, 28, 631528), 'chunk_uid__1': 'e010ee92-0668-49be-91be-742ecbceb2c0', 'char_start__1': 0, 'metadata_json__1': Jsonb({'page_no': 2}), 'chunk_no__1': 1, 'document_id__1': 39, 'vector_version__1': 1, 'created_at__1': datetime.datetime(2026, 4, 7, 10, 42, 28, 631527), 'deleted_at__1': None, 'vector_status__1': 'ready', 'content_hash__1': '657d2ae6c721eeab710a87be1dab3bce2156ea47556abfb9f7e355c4dcdb26ec', 'embedding_model__1': 'mock-embedding', 'content__1': '目录\\n目录 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 2\\n1 拓扑线性空间 3\\n1 局部凸空间 . . . . . . . . . . . . ... (512 characters truncated) ...  . . . . . . . . . . . 7\\n4.2 有限维赋范线性空间的刻画 . . . . . . . . . . . . . . . . . . . . . . . . . . . . 8\\n4.3 商空间 . . . . . . . . . . . . . . . . . . . .', 'char_end__2': 1500, 'page_no__2': 2, 'token_count__2': 400, 'updated_at__2': datetime.datetime(2026, 4, 7, 10, 42, 28, 631531), 'chunk_uid__2': '8109dbb9-f4bc-4c90-824b-6d06dbe08675', 'char_start__2': 700, 'metadata_json__2': Jsonb({'page_no': 2}), 'chunk_no__2': 2, 'document_id__2': 39, 'vector_version__2': 1, 'created_at__2': datetime.datetime(2026, 4, 7, 10, 42, 28, 631530), 'deleted_at__2': None, 'vector_status__2': 'ready', 'content_hash__2': '1a89193837bea0aace5da4f9bf338a590ad8d6736db479f98c380a3eb1740860', 'embedding_model__2': 'mock-embedding', 'content__2': '. . . . . . . . . . . . . . . . . . . . . . . . . 8\\n4.3 商空间 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 8\\n5 凸集与 ... (513 characters truncated) ...  . . . . . . . . . . . . 12\\n3 拓扑线性空间 13\\n4 线性算子 14\\n1 线性算子的概念 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 14\\n2 下有', 'char_end__3': 2200, 'page_no__3': 2 ... 924 parameters truncated ... 'embedding_model__60': 'mock-embedding', 'content__60': 'CHAPTER 7. BANACH 代数 43\\n2 谱\\n定义 2.1. 设 A 是 Banach 代数 U 中的元素， 定义了A 的谱值是什么， 即没有双边逆. 但是它似乎\\n没有区分什么连续谱什么剩余谱什么点谱之类.', 'char_end__61': 36, 'page_no__61': 45, 'token_count__61': 18, 'updated_at__61': datetime.datetime(2026, 4, 7, 10, 42, 28, 631680), 'chunk_uid__61': '27189e35-9d50-4460-981b-0208b22234df', 'char_start__61': 0, 'metadata_json__61': Jsonb({'page_no': 45}), 'chunk_no__61': 61, 'document_id__61': 39, 'vector_version__61': 1, 'created_at__61': datetime.datetime(2026, 4, 7, 10, 42, 28, 631679), 'deleted_at__61': None, 'vector_status__61': 'ready', 'content_hash__61': '55da88492ebc0a89ae01461ec940117196d2b72abc1a031ebc412d199c4d92a9', 'embedding_model__61': 'mock-embedding', 'content__61': '附录 A\\n泛函分析中的反例\\n1 纲\\n• 第一纲集但不无处稠密：Q.\\n44', 'char_end__62': 148, 'page_no__62': 46, 'token_count__62': 74, 'updated_at__62': datetime.datetime(2026, 4, 7, 10, 42, 28, 631682), 'chunk_uid__62': '1ebff0cc-6f83-4456-b068-8e9255d79867', 'char_start__62': 0, 'metadata_json__62': Jsonb({'page_no': 46}), 'chunk_no__62': 62, 'document_id__62': 39, 'vector_version__62': 1, 'created_at__62': datetime.datetime(2026, 4, 7, 10, 42, 28, 631682), 'deleted_at__62': None, 'vector_status__62': 'ready', 'content_hash__62': 'c9811b7d76f2fe68f17d1933ea35b02b00f408072c5b7cb0174e0e28a885db35', 'embedding_model__62': 'mock-embedding', 'content__62': '附录 A. 泛函分析中的反例 45\\n2 映射\\n• 逆映射不连续\\n3\\n定理 3.1 (Riesz 表示定理).\\nLax-Milgram 定理可看作将内积改为满足强制条件 a(u; u) ⩾ \\x0ekuk2 的连续共轭双线性泛函\\na(u; v) 的推广.\\n定理 3.2 (Lax-Milgram 定理).', 'char_end__63': 390, 'page_no__63': 47, 'token_count__63': 195, 'updated_at__63': datetime.datetime(2026, 4, 7, 10, 42, 28, 631685), 'chunk_uid__63': '79f86245-5aea-4927-888c-cb942b30af6d', 'char_start__63': 0, 'metadata_json__63': Jsonb({'page_no': 47}), 'chunk_no__63': 63, 'document_id__63': 39, 'vector_version__63': 1, 'created_at__63': datetime.datetime(2026, 4, 7, 10, 42, 28, 631684), 'deleted_at__63': None, 'vector_status__63': 'ready', 'content_hash__63': 'cfb271fb79bfdeff7f25452a60a8a06777067bb6dab9bb82f45de5e180c5d0d7', 'embedding_model__63': 'mock-embedding', 'content__63': '附录 B\\n套路\\n1 有机会成为一组的东西\\n• 最佳逼近元\\n– 设 X 是赋范线性空间，M 是 X 的有限维子空间， 那么对于任意x 2 X，x 到 M 的距离\\n的最小值能取到.\\n– 如果 M 仅仅是闭子空间，那么虽然可以任意精度逼近，但可能取不到.\\n• 对象分解\\n– 设 X 是 B ... (109 characters truncated) ... 任意 g 2 Y ∗，g(T xn) ! g(y).\\n• T ∗g(xn) ! g(y).\\n• 也就是说，我知道了一部分 X ∗ 中的元素，作用在 fxng 上时，的收敛性.\\n比较，已知 xn 弱收敛到 x，\\n• 我就知道了所有 X ∗ 中的元素，作用在 fxng 上时，的收敛性.\\n46'}]\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"}}}

======================================================================
FAIL: test_bm25_natural_question_should_return_hilbert_definition_in_top3 (test_search_contract.SearchContractTestCase.test_bm25_natural_question_should_return_hilbert_definition_in_top3)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/test/test_search_contract.py", line 77, in test_bm25_natural_question_should_return_hilbert_definition_in_top3
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
  File "/app/test/test_search_contract.py", line 69, in scenario
    self.assertTrue(
    ~~~~~~~~~~~~~~~^
        any("then we say that X is a Hilbert space" in preview for preview in previews),
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        payload,
        ^^^^^^^^
    )
    ^
AssertionError: False is not true : {'success': True, 'code': 'OK', 'message': 'success', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-07T10:43:00.196864+00:00', 'data': {'query': 'what is Hilbert space?', 'alpha': 1.0, 'retrieval_mode': 'lexical_bm25', 'total': 3, 'items': [{'chunk_id': 5921, 'chunk_uid': '00fd82a6-b3d7-45ca-8191-0c4d4470a067', 'chunk_no': 38, 'page_no': 15, 'score': 6.665651798248291, 'content': '2011 F UNCTIONAL ANALYSIS ALP\n[8] Show that if fM/NAKg is a family of linear subspaces of a linear space X , then MD\\ /NAK M/NAK is a\nlinear subspace of X .\nIf M and N are linear subspaces of a linear space X , under what condition(s) is M[ N a\nlinear subspace of X ?\n12', 'document': {'id': 41, 'document_uid': 'fa3e023f-22f7-4c3a-a934-938445372c68', 'title': 'search_hilbert_question_1775558570247_281473503367952', 'file_name': 'Functional Analysis Notes.pdf', 'category_id': 67, 'version': 1}, 'category': {'id': 67, 'category_code': 'search_hilbert_question_1775558570232_281473503367952', 'name': 'search_hilbert_question_1775558570232_281473503367952'}}, {'chunk_id': 5986, 'chunk_uid': 'd50e6b27-c2d5-480e-a733-e4136be4d538', 'chunk_no': 103, 'page_no': 38, 'score': 5.25549840927124, 'content': 'r a long time until Per Enﬂo in 1973 ans wered it in the negative. He constructed a\nseparable reﬂexive Banach space with no basis.\n2.7.7 Exercise\n[1] Let X be a normed linear space over F. Show that X is ﬁnite-dimensional if and only if every\nbounded sequence in X has a convergent subsequence.\n[2] Complete the proof of Theorem 2.1.1.\n[3] Prove Lemma 2.3.2.\n[4] Prove the claims made in [1] and [2] of Example 2.3.7.\n[5] Prove Theorem 2.5.5.\n[6] Prove Corollary 2.5.8.\n[7] Prove Corollary 2.5.9.\n[8] Prove Corollary 2.5.10.\n[9] Prove Corollary 2.6.2.\n[10] Is .CŒa; b/c141;k/SOHk 1/ complete? What about .CŒa; b/c141;k/SOHk 1/? Fully justify both answers.\n35', 'document': {'id': 41, 'document_uid': 'fa3e023f-22f7-4c3a-a934-938445372c68', 'title': 'search_hilbert_question_1775558570247_281473503367952', 'file_name': 'Functional Analysis Notes.pdf', 'category_id': 67, 'version': 1}, 'category': {'id': 67, 'category_code': 'search_hilbert_question_1775558570232_281473503367952', 'name': 'search_hilbert_question_1775558570232_281473503367952'}}, {'chunk_id': 5886, 'chunk_uid': '985462b3-16df-4f07-9a90-673d8634d2b4', 'chunk_no': 3, 'page_no': 2, 'score': 4.725534915924072, 'content': '. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 36\n3.2 Completeness of Inner Product Spaces . . . . . . . . . . . . . . . . . . . . . . . . . . . . 42\n3.3 Orthogonality . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 42\n3.4 Best Approximation in Hilbert Spaces . . . . . . . . . . . . . . . . . . . . . . . . . . . . 45\n3.5 Orthonormal Sets and Orthonormal Bases . . . . . . . . . . . . . . . . . . . . . . . . . . 49\n4 Bounded Linear Operators and Functionals 62\n4.1 Introduction . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 62\n4.2 Examples of Dual Spaces . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 72\n4.3 The Dual Space of a Hilbert Space . . . . . . . . . . . .', 'document': {'id': 41, 'document_uid': 'fa3e023f-22f7-4c3a-a934-938445372c68', 'title': 'search_hilbert_question_1775558570247_281473503367952', 'file_name': 'Functional Analysis Notes.pdf', 'category_id': 67, 'version': 1}, 'category': {'id': 67, 'category_code': 'search_hilbert_question_1775558570232_281473503367952', 'name': 'search_hilbert_question_1775558570232_281473503367952'}}]}}

======================================================================
FAIL: test_hybrid_search_chinese_query_should_hit_hilbert_section_in_top3 (test_search_contract.SearchContractTestCase.test_hybrid_search_chinese_query_should_hit_hilbert_section_in_top3)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/test/test_search_contract.py", line 105, in test_hybrid_search_chinese_query_should_hit_hilbert_section_in_top3
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
  File "/app/test/test_search_contract.py", line 97, in scenario
    self.assertTrue(
    ~~~~~~~~~~~~~~~^
        any("Hilbert space" in preview for preview in previews),
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        payload,
        ^^^^^^^^
    )
    ^
AssertionError: False is not true : {'success': True, 'code': 'OK', 'message': 'success', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-07T10:43:21.798651+00:00', 'data': {'query': '什么是希尔伯特空间', 'alpha': 0.5, 'retrieval_mode': 'hybrid', 'total': 3, 'items': [{'chunk_id': 6380, 'chunk_uid': '6b974dcf-2139-4690-b31e-f4228d2c8ca3', 'chunk_no': 188, 'page_no': 71, 'score': 0.2699100375175476, 'content': '/SOHk 0 andk/SOHk on X are equivalent. Hence there are constants ˛\nandˇ such that\n˛kxk0/DC4kxk/DC4ˇkxk0 for all x2 X:\nHence,\nkT xk/DC4kxk0/DC41\n˛kxkD Kkxk;\nwhere KD 1\n˛ . Therefore T is bounded. ■\n4.1.9 Deﬁnition\nLet X and Y be normed linear spaces over a ﬁeld F.\n(1) A sequence .Tn/1\n1\nin B.X; Y/ is said to be uniformly operator convergent to T if\nlim\nn!1\nkTn/NUL TkD 0:\nThis is also referred to as convergence in the uniform topology or convergence in the operator\nnorm topology of B.X; Y/. In this case T is called the uniform operator limit of the sequence\n.Tn/1\n1\n.\n(2) A sequence .Tn/1\n1\nin B.X; Y/ is said to be strongly operator convergent to T if\nlim\nn!1\nkTnx/NUL T xkD 0 for each x2 X:\nIn this case T is called the strong operator limit of the sequence .Tn/1\n1\n.\nOf course, if T is the uni', 'document': {'id': 42, 'document_uid': '35632f61-d429-4a19-b699-45dc1cbecdcd', 'title': 'search_hilbert_cn_1775558591852_281473503368272', 'file_name': 'Functional Analysis Notes.pdf', 'category_id': 68, 'version': 1}, 'category': {'id': 68, 'category_code': 'search_hilbert_cn_1775558591838_281473503368272', 'name': 'search_hilbert_cn_1775558591838_281473503368272'}}, {'chunk_id': 6253, 'chunk_uid': 'e9add5e9-de16-4d33-b9b3-12bc0c551ce6', 'chunk_no': 61, 'page_no': 25, 'score': 0.269867479801178, 'content': '2011 F UNCTIONAL ANALYSIS ALP\nThat is, for each ﬁxed index i , .xn.i//1\n1 is a Cauchy sequence in F. Since F is complete,\nthere exists x.i/2 F such that\nxn.i/! x.i/ as n!1:\nDeﬁne xD.x.1/; x.2/;:::/ . We show that x2`p, and xn! x. T o that end, for each k2 N,\n kX\niD1\njxn.i//NUL xm.i/jp\n! 1\np\n/DC4kxn/NUL xmkpD\n 1X\niD1\njxn.i//NUL xm.i/jp\n! 1\np\n</SI:\nThat is,\nkX\niD1\njxn.i//NUL xm.i/jp </SI p; for all kD 1; 2; 3;::::\nKeep k and n/NAK N ﬁxed and let m!1 . Since we are dealing with a ﬁnite sum,\nkX\niD1\njxn.i//NUL x.i/jp/DC4/SI p:\nNow letting k!1 , then for all n/NAK N ,\n1X\niD1\njxn.i//NUL x.i/jp/DC4/SI p; . 2:3:7:1/\nwhich means that xn/NUL x2`p. Since xn2`p, we have that xD.x/NUL xn/C xn2`p. It also\nfollows from (2.3.7.1) that xn! x as n!1 . ■\n[4] The space `0 of all sequences .xi/1\n1 with only a ﬁ', 'document': {'id': 42, 'document_uid': '35632f61-d429-4a19-b699-45dc1cbecdcd', 'title': 'search_hilbert_cn_1775558591852_281473503368272', 'file_name': 'Functional Analysis Notes.pdf', 'category_id': 68, 'version': 1}, 'category': {'id': 68, 'category_code': 'search_hilbert_cn_1775558591838_281473503368272', 'name': 'search_hilbert_cn_1775558591838_281473503368272'}}, {'chunk_id': 6228, 'chunk_uid': '250edbf4-654e-4a11-b41a-380c05a581e4', 'chunk_no': 36, 'page_no': 14, 'score': 0.26853469014167786, 'content': '2011 F UNCTIONAL ANALYSIS ALP\nProof. Let qD p\np/NUL 1 . If\n1X\nkD1\njxkC ykjpD 0, then the inequality holds. We therefore assume that\n1X\nkD1\njxkC ykjp6D 0. Then\n1X\nkD1\njxkC ykjp D\n1X\nkD1\njxkC ykjp/NUL 1jxkC ykj\n/DC4\n1X\nkD1\njxkC ykjp/NUL 1jxkjC\n1X\nkD1\njxkC ykjp/NUL 1jykj\n/DC4\n 1X\nkD1\njxkC ykj.p/NUL 1/q\n! 1\nq\n2\n4\n 1X\nkD1\njxkjp\n! 1\np\nC\n 1X\nkD1\njykjp\n! 1\np\n3\n5\nD\n 1X\nkD1\njxkC ykjp\n! 1\nq\n2\n4\n 1X\nkD1\njxkjp\n! 1\np\nC\n 1X\nkD1\njykjp\n! 1\np\n3\n5:\nDividing both sides by\n 1X\nkD1\njxkC ykjp\n! 1\nq\n, we have\n 1X\nkD1\njxkC ykjp\n! 1\np\nD\n 1X\nkD1\njxkC ykjp\n!1/NUL 1\nq\n/DC4\n 1X\nkD1\njxkjp\n! 1\np\nC\n 1X\nkD1\njykjp\n! 1\np\n: ■\n1.6.5 Exercise\n[1] Show that the set of all n/STX m real matrices is a real linear space.\n[2] Show that a subset M of a linear space X is a linear subspace if and only if ˛xCˇy2 M\nfor all x; y2 M and all', 'document': {'id': 42, 'document_uid': '35632f61-d429-4a19-b699-45dc1cbecdcd', 'title': 'search_hilbert_cn_1775558591852_281473503368272', 'file_name': 'Functional Analysis Notes.pdf', 'category_id': 68, 'version': 1}, 'category': {'id': 68, 'category_code': 'search_hilbert_cn_1775558591838_281473503368272', 'name': 'search_hilbert_cn_1775558591838_281473503368272'}}]}}

======================================================================
FAIL: test_search_rejects_empty_query (test_search_contract.SearchContractTestCase.test_search_rejects_empty_query)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/test/test_search_contract.py", line 42, in test_search_rejects_empty_query
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
  File "/app/test/test_search_contract.py", line 40, in scenario
    self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/test/base.py", line 64, in assert_error
    self.assertEqual(payload.get("code"), code, payload)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'MCP_TOOL_EXECUTION_ERROR' != 'INVALID_ARGUMENT'
- MCP_TOOL_EXECUTION_ERROR
+ INVALID_ARGUMENT
 : {'success': False, 'code': 'MCP_TOOL_EXECUTION_ERROR', 'message': "Error executing tool kb_search_retrieve: Unable to serialize unknown type: <class 'ValueError'>", 'error': {'type': 'tool_execution_error', 'details': {}}}

----------------------------------------------------------------------
Ran 19 tests in 100.266s

FAILED (failures=8)
```

## 错误记录

### 失败: test_category_contract.CategoryContractTestCase.test_category_create_rejects_invalid_code

```text
Traceback (most recent call last):
  File "/app/test/test_category_contract.py", line 57, in test_category_create_rejects_invalid_code
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
  File "/app/test/test_category_contract.py", line 55, in scenario
    self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/test/base.py", line 64, in assert_error
    self.assertEqual(payload.get("code"), code, payload)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'MCP_TOOL_EXECUTION_ERROR' != 'INVALID_ARGUMENT'
- MCP_TOOL_EXECUTION_ERROR
+ INVALID_ARGUMENT
 : {'success': False, 'code': 'MCP_TOOL_EXECUTION_ERROR', 'message': "Error executing tool kb_category_create: Unable to serialize unknown type: <class 'ValueError'>", 'error': {'type': 'tool_execution_error', 'details': {}}}
```

### 失败: test_document_contract.DocumentContractTestCase.test_category_delete_rejects_active_documents

```text
Traceback (most recent call last):
  File "/app/test/test_document_contract.py", line 106, in test_category_delete_rejects_active_documents
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
  File "/app/test/test_document_contract.py", line 98, in scenario
    document = await self.import_document(category_id=category["id"], title_prefix="guard_doc")
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/test/base.py", line 100, in import_document
    self.assert_success(payload)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^^
  File "/app/test/base.py", line 50, in assert_success
    self.assertTrue(payload.get("success"), payload)
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : {'success': False, 'code': 'DOCUMENT_IMPORT_FAILED', 'message': 'document import failed', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-07T10:42:27.853633+00:00', 'error': {'type': 'system_error', 'details': {'error': "(psycopg.DataError) PostgreSQL text fields cannot contain NUL (0x00) bytes\n[SQL: INSERT INTO kb_chunk (chunk_uid, document_id, chunk_no, page_no, char_start, char_end, token_count, content, content_hash, embedding_model, vector_version, vector_status, metadata_json, created_at, updated_at, deleted_at) SELECT p0::VARCHAR, p1::BIGI ... 34390 characters truncated ... 1, p12, p13, p14, p15, sen_counter) ORDER BY sen_counter RETURNING kb_chunk.id, kb_chunk.id AS id__1]\n[parameters: {'char_end__0': 23, 'page_no__0': 1, 'token_count__0': 11, 'updated_at__0': datetime.datetime(2026, 4, 7, 10, 42, 27, 850961), 'chunk_uid__0': 'fe09a718-9b1c-4cc0-8b6c-a93b8f9ba487', 'char_start__0': 0, 'metadata_json__0': Jsonb({'page_no': 1}), 'chunk_no__0': 0, 'document_id__0': 37, 'vector_version__0': 1, 'created_at__0': datetime.datetime(2026, 4, 7, 10, 42, 27, 850958), 'deleted_at__0': None, 'vector_status__0': 'ready', 'content_hash__0': 'f6ada8c06323952705736deb3dc1a87cbefab9120af166aaa34b7866323189f5', 'embedding_model__0': 'mock-embedding', 'content__0': '泛函分析\\n孙天阳\\n2023 年 6 月 8 日', 'char_end__1': 800, 'page_no__1': 2, 'token_count__1': 399, 'updated_at__1': datetime.datetime(2026, 4, 7, 10, 42, 27, 850965), 'chunk_uid__1': '841572cc-92b7-449c-99a0-9cdca4f7d5de', 'char_start__1': 0, 'metadata_json__1': Jsonb({'page_no': 2}), 'chunk_no__1': 1, 'document_id__1': 37, 'vector_version__1': 1, 'created_at__1': datetime.datetime(2026, 4, 7, 10, 42, 27, 850965), 'deleted_at__1': None, 'vector_status__1': 'ready', 'content_hash__1': '657d2ae6c721eeab710a87be1dab3bce2156ea47556abfb9f7e355c4dcdb26ec', 'embedding_model__1': 'mock-embedding', 'content__1': '目录\\n目录 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 2\\n1 拓扑线性空间 3\\n1 局部凸空间 . . . . . . . . . . . . ... (512 characters truncated) ...  . . . . . . . . . . . 7\\n4.2 有限维赋范线性空间的刻画 . . . . . . . . . . . . . . . . . . . . . . . . . . . . 8\\n4.3 商空间 . . . . . . . . . . . . . . . . . . . .', 'char_end__2': 1500, 'page_no__2': 2, 'token_count__2': 400, 'updated_at__2': datetime.datetime(2026, 4, 7, 10, 42, 27, 850969), 'chunk_uid__2': 'bd36b21e-e844-4179-afa2-f1971cb9079c', 'char_start__2': 700, 'metadata_json__2': Jsonb({'page_no': 2}), 'chunk_no__2': 2, 'document_id__2': 37, 'vector_version__2': 1, 'created_at__2': datetime.datetime(2026, 4, 7, 10, 42, 27, 850968), 'deleted_at__2': None, 'vector_status__2': 'ready', 'content_hash__2': '1a89193837bea0aace5da4f9bf338a590ad8d6736db479f98c380a3eb1740860', 'embedding_model__2': 'mock-embedding', 'content__2': '. . . . . . . . . . . . . . . . . . . . . . . . . 8\\n4.3 商空间 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 8\\n5 凸集与 ... (513 characters truncated) ...  . . . . . . . . . . . . 12\\n3 拓扑线性空间 13\\n4 线性算子 14\\n1 线性算子的概念 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 14\\n2 下有', 'char_end__3': 2200, 'page_no__3': 2 ... 924 parameters truncated ... 'embedding_model__60': 'mock-embedding', 'content__60': 'CHAPTER 7. BANACH 代数 43\\n2 谱\\n定义 2.1. 设 A 是 Banach 代数 U 中的元素， 定义了A 的谱值是什么， 即没有双边逆. 但是它似乎\\n没有区分什么连续谱什么剩余谱什么点谱之类.', 'char_end__61': 36, 'page_no__61': 45, 'token_count__61': 18, 'updated_at__61': datetime.datetime(2026, 4, 7, 10, 42, 27, 851116), 'chunk_uid__61': '560f0261-b92b-483a-a667-309421ae3efa', 'char_start__61': 0, 'metadata_json__61': Jsonb({'page_no': 45}), 'chunk_no__61': 61, 'document_id__61': 37, 'vector_version__61': 1, 'created_at__61': datetime.datetime(2026, 4, 7, 10, 42, 27, 851115), 'deleted_at__61': None, 'vector_status__61': 'ready', 'content_hash__61': '55da88492ebc0a89ae01461ec940117196d2b72abc1a031ebc412d199c4d92a9', 'embedding_model__61': 'mock-embedding', 'content__61': '附录 A\\n泛函分析中的反例\\n1 纲\\n• 第一纲集但不无处稠密：Q.\\n44', 'char_end__62': 148, 'page_no__62': 46, 'token_count__62': 74, 'updated_at__62': datetime.datetime(2026, 4, 7, 10, 42, 27, 851118), 'chunk_uid__62': '5d05faa8-65e0-4018-ab92-122950f8f16b', 'char_start__62': 0, 'metadata_json__62': Jsonb({'page_no': 46}), 'chunk_no__62': 62, 'document_id__62': 37, 'vector_version__62': 1, 'created_at__62': datetime.datetime(2026, 4, 7, 10, 42, 27, 851118), 'deleted_at__62': None, 'vector_status__62': 'ready', 'content_hash__62': 'c9811b7d76f2fe68f17d1933ea35b02b00f408072c5b7cb0174e0e28a885db35', 'embedding_model__62': 'mock-embedding', 'content__62': '附录 A. 泛函分析中的反例 45\\n2 映射\\n• 逆映射不连续\\n3\\n定理 3.1 (Riesz 表示定理).\\nLax-Milgram 定理可看作将内积改为满足强制条件 a(u; u) ⩾ \\x0ekuk2 的连续共轭双线性泛函\\na(u; v) 的推广.\\n定理 3.2 (Lax-Milgram 定理).', 'char_end__63': 390, 'page_no__63': 47, 'token_count__63': 195, 'updated_at__63': datetime.datetime(2026, 4, 7, 10, 42, 27, 851121), 'chunk_uid__63': '071847b2-5f4e-4ab3-b193-34cee25adf96', 'char_start__63': 0, 'metadata_json__63': Jsonb({'page_no': 47}), 'chunk_no__63': 63, 'document_id__63': 37, 'vector_version__63': 1, 'created_at__63': datetime.datetime(2026, 4, 7, 10, 42, 27, 851120), 'deleted_at__63': None, 'vector_status__63': 'ready', 'content_hash__63': 'cfb271fb79bfdeff7f25452a60a8a06777067bb6dab9bb82f45de5e180c5d0d7', 'embedding_model__63': 'mock-embedding', 'content__63': '附录 B\\n套路\\n1 有机会成为一组的东西\\n• 最佳逼近元\\n– 设 X 是赋范线性空间，M 是 X 的有限维子空间， 那么对于任意x 2 X，x 到 M 的距离\\n的最小值能取到.\\n– 如果 M 仅仅是闭子空间，那么虽然可以任意精度逼近，但可能取不到.\\n• 对象分解\\n– 设 X 是 B ... (109 characters truncated) ... 任意 g 2 Y ∗，g(T xn) ! g(y).\\n• T ∗g(xn) ! g(y).\\n• 也就是说，我知道了一部分 X ∗ 中的元素，作用在 fxng 上时，的收敛性.\\n比较，已知 xn 弱收敛到 x，\\n• 我就知道了所有 X ∗ 中的元素，作用在 fxng 上时，的收敛性.\\n46'}]\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"}}}
```

### 失败: test_document_contract.DocumentContractTestCase.test_document_import_get_list_delete_smoke

```text
Traceback (most recent call last):
  File "/app/test/test_document_contract.py", line 43, in test_document_import_get_list_delete_smoke
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
  File "/app/test/test_document_contract.py", line 12, in scenario
    document = await self.import_document(
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
    )
    ^
  File "/app/test/base.py", line 100, in import_document
    self.assert_success(payload)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^^
  File "/app/test/base.py", line 50, in assert_success
    self.assertTrue(payload.get("success"), payload)
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : {'success': False, 'code': 'DOCUMENT_IMPORT_FAILED', 'message': 'document import failed', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-07T10:42:28.143636+00:00', 'error': {'type': 'system_error', 'details': {'error': "(psycopg.DataError) PostgreSQL text fields cannot contain NUL (0x00) bytes\n[SQL: INSERT INTO kb_chunk (chunk_uid, document_id, chunk_no, page_no, char_start, char_end, token_count, content, content_hash, embedding_model, vector_version, vector_status, metadata_json, created_at, updated_at, deleted_at) SELECT p0::VARCHAR, p1::BIGI ... 34390 characters truncated ... 1, p12, p13, p14, p15, sen_counter) ORDER BY sen_counter RETURNING kb_chunk.id, kb_chunk.id AS id__1]\n[parameters: {'char_end__0': 23, 'page_no__0': 1, 'token_count__0': 11, 'updated_at__0': datetime.datetime(2026, 4, 7, 10, 42, 28, 141166), 'chunk_uid__0': '23805b09-ec09-4a37-92ed-fe0fbbe9b8d3', 'char_start__0': 0, 'metadata_json__0': Jsonb({'page_no': 1}), 'chunk_no__0': 0, 'document_id__0': 38, 'vector_version__0': 1, 'created_at__0': datetime.datetime(2026, 4, 7, 10, 42, 28, 141163), 'deleted_at__0': None, 'vector_status__0': 'ready', 'content_hash__0': 'f6ada8c06323952705736deb3dc1a87cbefab9120af166aaa34b7866323189f5', 'embedding_model__0': 'mock-embedding', 'content__0': '泛函分析\\n孙天阳\\n2023 年 6 月 8 日', 'char_end__1': 800, 'page_no__1': 2, 'token_count__1': 399, 'updated_at__1': datetime.datetime(2026, 4, 7, 10, 42, 28, 141170), 'chunk_uid__1': '172c3ea9-d433-4e70-99a4-8405605fc5e2', 'char_start__1': 0, 'metadata_json__1': Jsonb({'page_no': 2}), 'chunk_no__1': 1, 'document_id__1': 38, 'vector_version__1': 1, 'created_at__1': datetime.datetime(2026, 4, 7, 10, 42, 28, 141169), 'deleted_at__1': None, 'vector_status__1': 'ready', 'content_hash__1': '657d2ae6c721eeab710a87be1dab3bce2156ea47556abfb9f7e355c4dcdb26ec', 'embedding_model__1': 'mock-embedding', 'content__1': '目录\\n目录 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 2\\n1 拓扑线性空间 3\\n1 局部凸空间 . . . . . . . . . . . . ... (512 characters truncated) ...  . . . . . . . . . . . 7\\n4.2 有限维赋范线性空间的刻画 . . . . . . . . . . . . . . . . . . . . . . . . . . . . 8\\n4.3 商空间 . . . . . . . . . . . . . . . . . . . .', 'char_end__2': 1500, 'page_no__2': 2, 'token_count__2': 400, 'updated_at__2': datetime.datetime(2026, 4, 7, 10, 42, 28, 141173), 'chunk_uid__2': '61665c07-2ff5-4c4a-91d0-d239986ea3e8', 'char_start__2': 700, 'metadata_json__2': Jsonb({'page_no': 2}), 'chunk_no__2': 2, 'document_id__2': 38, 'vector_version__2': 1, 'created_at__2': datetime.datetime(2026, 4, 7, 10, 42, 28, 141172), 'deleted_at__2': None, 'vector_status__2': 'ready', 'content_hash__2': '1a89193837bea0aace5da4f9bf338a590ad8d6736db479f98c380a3eb1740860', 'embedding_model__2': 'mock-embedding', 'content__2': '. . . . . . . . . . . . . . . . . . . . . . . . . 8\\n4.3 商空间 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 8\\n5 凸集与 ... (513 characters truncated) ...  . . . . . . . . . . . . 12\\n3 拓扑线性空间 13\\n4 线性算子 14\\n1 线性算子的概念 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 14\\n2 下有', 'char_end__3': 2200, 'page_no__3': 2 ... 924 parameters truncated ... 'embedding_model__60': 'mock-embedding', 'content__60': 'CHAPTER 7. BANACH 代数 43\\n2 谱\\n定义 2.1. 设 A 是 Banach 代数 U 中的元素， 定义了A 的谱值是什么， 即没有双边逆. 但是它似乎\\n没有区分什么连续谱什么剩余谱什么点谱之类.', 'char_end__61': 36, 'page_no__61': 45, 'token_count__61': 18, 'updated_at__61': datetime.datetime(2026, 4, 7, 10, 42, 28, 141317), 'chunk_uid__61': 'ce47a8a6-4f05-400b-9a99-30e6b1d5ca2c', 'char_start__61': 0, 'metadata_json__61': Jsonb({'page_no': 45}), 'chunk_no__61': 61, 'document_id__61': 38, 'vector_version__61': 1, 'created_at__61': datetime.datetime(2026, 4, 7, 10, 42, 28, 141317), 'deleted_at__61': None, 'vector_status__61': 'ready', 'content_hash__61': '55da88492ebc0a89ae01461ec940117196d2b72abc1a031ebc412d199c4d92a9', 'embedding_model__61': 'mock-embedding', 'content__61': '附录 A\\n泛函分析中的反例\\n1 纲\\n• 第一纲集但不无处稠密：Q.\\n44', 'char_end__62': 148, 'page_no__62': 46, 'token_count__62': 74, 'updated_at__62': datetime.datetime(2026, 4, 7, 10, 42, 28, 141319), 'chunk_uid__62': 'bdd12081-6e0a-465f-8538-e5f7e4c29606', 'char_start__62': 0, 'metadata_json__62': Jsonb({'page_no': 46}), 'chunk_no__62': 62, 'document_id__62': 38, 'vector_version__62': 1, 'created_at__62': datetime.datetime(2026, 4, 7, 10, 42, 28, 141319), 'deleted_at__62': None, 'vector_status__62': 'ready', 'content_hash__62': 'c9811b7d76f2fe68f17d1933ea35b02b00f408072c5b7cb0174e0e28a885db35', 'embedding_model__62': 'mock-embedding', 'content__62': '附录 A. 泛函分析中的反例 45\\n2 映射\\n• 逆映射不连续\\n3\\n定理 3.1 (Riesz 表示定理).\\nLax-Milgram 定理可看作将内积改为满足强制条件 a(u; u) ⩾ \\x0ekuk2 的连续共轭双线性泛函\\na(u; v) 的推广.\\n定理 3.2 (Lax-Milgram 定理).', 'char_end__63': 390, 'page_no__63': 47, 'token_count__63': 195, 'updated_at__63': datetime.datetime(2026, 4, 7, 10, 42, 28, 141322), 'chunk_uid__63': 'ad641242-3007-41f6-add4-3dfcf2f3be09', 'char_start__63': 0, 'metadata_json__63': Jsonb({'page_no': 47}), 'chunk_no__63': 63, 'document_id__63': 38, 'vector_version__63': 1, 'created_at__63': datetime.datetime(2026, 4, 7, 10, 42, 28, 141321), 'deleted_at__63': None, 'vector_status__63': 'ready', 'content_hash__63': 'cfb271fb79bfdeff7f25452a60a8a06777067bb6dab9bb82f45de5e180c5d0d7', 'embedding_model__63': 'mock-embedding', 'content__63': '附录 B\\n套路\\n1 有机会成为一组的东西\\n• 最佳逼近元\\n– 设 X 是赋范线性空间，M 是 X 的有限维子空间， 那么对于任意x 2 X，x 到 M 的距离\\n的最小值能取到.\\n– 如果 M 仅仅是闭子空间，那么虽然可以任意精度逼近，但可能取不到.\\n• 对象分解\\n– 设 X 是 B ... (109 characters truncated) ... 任意 g 2 Y ∗，g(T xn) ! g(y).\\n• T ∗g(xn) ! g(y).\\n• 也就是说，我知道了一部分 X ∗ 中的元素，作用在 fxng 上时，的收敛性.\\n比较，已知 xn 弱收敛到 x，\\n• 我就知道了所有 X ∗ 中的元素，作用在 fxng 上时，的收敛性.\\n46'}]\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"}}}
```

### 失败: test_document_contract.DocumentContractTestCase.test_document_import_rejects_invalid_mime_type

```text
Traceback (most recent call last):
  File "/app/test/test_document_contract.py", line 75, in test_document_import_rejects_invalid_mime_type
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
  File "/app/test/test_document_contract.py", line 71, in scenario
    self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/test/base.py", line 64, in assert_error
    self.assertEqual(payload.get("code"), code, payload)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'MCP_TOOL_EXECUTION_ERROR' != 'INVALID_ARGUMENT'
- MCP_TOOL_EXECUTION_ERROR
+ INVALID_ARGUMENT
 : {'success': False, 'code': 'MCP_TOOL_EXECUTION_ERROR', 'message': "Error executing tool kb_document_import: Unable to serialize unknown type: <class 'ValueError'>", 'error': {'type': 'tool_execution_error', 'details': {}}}
```

### 失败: test_document_contract.DocumentContractTestCase.test_document_update_metadata_only

```text
Traceback (most recent call last):
  File "/app/test/test_document_contract.py", line 132, in test_document_update_metadata_only
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
  File "/app/test/test_document_contract.py", line 112, in scenario
    document = await self.import_document(
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
    )
    ^
  File "/app/test/base.py", line 100, in import_document
    self.assert_success(payload)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^^
  File "/app/test/base.py", line 50, in assert_success
    self.assertTrue(payload.get("success"), payload)
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : {'success': False, 'code': 'DOCUMENT_IMPORT_FAILED', 'message': 'document import failed', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-07T10:42:28.634141+00:00', 'error': {'type': 'system_error', 'details': {'error': "(psycopg.DataError) PostgreSQL text fields cannot contain NUL (0x00) bytes\n[SQL: INSERT INTO kb_chunk (chunk_uid, document_id, chunk_no, page_no, char_start, char_end, token_count, content, content_hash, embedding_model, vector_version, vector_status, metadata_json, created_at, updated_at, deleted_at) SELECT p0::VARCHAR, p1::BIGI ... 34390 characters truncated ... 1, p12, p13, p14, p15, sen_counter) ORDER BY sen_counter RETURNING kb_chunk.id, kb_chunk.id AS id__1]\n[parameters: {'char_end__0': 23, 'page_no__0': 1, 'token_count__0': 11, 'updated_at__0': datetime.datetime(2026, 4, 7, 10, 42, 28, 631523), 'chunk_uid__0': 'f3b2616e-1004-4f93-96b9-0002feb4dbd6', 'char_start__0': 0, 'metadata_json__0': Jsonb({'page_no': 1}), 'chunk_no__0': 0, 'document_id__0': 39, 'vector_version__0': 1, 'created_at__0': datetime.datetime(2026, 4, 7, 10, 42, 28, 631520), 'deleted_at__0': None, 'vector_status__0': 'ready', 'content_hash__0': 'f6ada8c06323952705736deb3dc1a87cbefab9120af166aaa34b7866323189f5', 'embedding_model__0': 'mock-embedding', 'content__0': '泛函分析\\n孙天阳\\n2023 年 6 月 8 日', 'char_end__1': 800, 'page_no__1': 2, 'token_count__1': 399, 'updated_at__1': datetime.datetime(2026, 4, 7, 10, 42, 28, 631528), 'chunk_uid__1': 'e010ee92-0668-49be-91be-742ecbceb2c0', 'char_start__1': 0, 'metadata_json__1': Jsonb({'page_no': 2}), 'chunk_no__1': 1, 'document_id__1': 39, 'vector_version__1': 1, 'created_at__1': datetime.datetime(2026, 4, 7, 10, 42, 28, 631527), 'deleted_at__1': None, 'vector_status__1': 'ready', 'content_hash__1': '657d2ae6c721eeab710a87be1dab3bce2156ea47556abfb9f7e355c4dcdb26ec', 'embedding_model__1': 'mock-embedding', 'content__1': '目录\\n目录 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 2\\n1 拓扑线性空间 3\\n1 局部凸空间 . . . . . . . . . . . . ... (512 characters truncated) ...  . . . . . . . . . . . 7\\n4.2 有限维赋范线性空间的刻画 . . . . . . . . . . . . . . . . . . . . . . . . . . . . 8\\n4.3 商空间 . . . . . . . . . . . . . . . . . . . .', 'char_end__2': 1500, 'page_no__2': 2, 'token_count__2': 400, 'updated_at__2': datetime.datetime(2026, 4, 7, 10, 42, 28, 631531), 'chunk_uid__2': '8109dbb9-f4bc-4c90-824b-6d06dbe08675', 'char_start__2': 700, 'metadata_json__2': Jsonb({'page_no': 2}), 'chunk_no__2': 2, 'document_id__2': 39, 'vector_version__2': 1, 'created_at__2': datetime.datetime(2026, 4, 7, 10, 42, 28, 631530), 'deleted_at__2': None, 'vector_status__2': 'ready', 'content_hash__2': '1a89193837bea0aace5da4f9bf338a590ad8d6736db479f98c380a3eb1740860', 'embedding_model__2': 'mock-embedding', 'content__2': '. . . . . . . . . . . . . . . . . . . . . . . . . 8\\n4.3 商空间 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 8\\n5 凸集与 ... (513 characters truncated) ...  . . . . . . . . . . . . 12\\n3 拓扑线性空间 13\\n4 线性算子 14\\n1 线性算子的概念 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 14\\n2 下有', 'char_end__3': 2200, 'page_no__3': 2 ... 924 parameters truncated ... 'embedding_model__60': 'mock-embedding', 'content__60': 'CHAPTER 7. BANACH 代数 43\\n2 谱\\n定义 2.1. 设 A 是 Banach 代数 U 中的元素， 定义了A 的谱值是什么， 即没有双边逆. 但是它似乎\\n没有区分什么连续谱什么剩余谱什么点谱之类.', 'char_end__61': 36, 'page_no__61': 45, 'token_count__61': 18, 'updated_at__61': datetime.datetime(2026, 4, 7, 10, 42, 28, 631680), 'chunk_uid__61': '27189e35-9d50-4460-981b-0208b22234df', 'char_start__61': 0, 'metadata_json__61': Jsonb({'page_no': 45}), 'chunk_no__61': 61, 'document_id__61': 39, 'vector_version__61': 1, 'created_at__61': datetime.datetime(2026, 4, 7, 10, 42, 28, 631679), 'deleted_at__61': None, 'vector_status__61': 'ready', 'content_hash__61': '55da88492ebc0a89ae01461ec940117196d2b72abc1a031ebc412d199c4d92a9', 'embedding_model__61': 'mock-embedding', 'content__61': '附录 A\\n泛函分析中的反例\\n1 纲\\n• 第一纲集但不无处稠密：Q.\\n44', 'char_end__62': 148, 'page_no__62': 46, 'token_count__62': 74, 'updated_at__62': datetime.datetime(2026, 4, 7, 10, 42, 28, 631682), 'chunk_uid__62': '1ebff0cc-6f83-4456-b068-8e9255d79867', 'char_start__62': 0, 'metadata_json__62': Jsonb({'page_no': 46}), 'chunk_no__62': 62, 'document_id__62': 39, 'vector_version__62': 1, 'created_at__62': datetime.datetime(2026, 4, 7, 10, 42, 28, 631682), 'deleted_at__62': None, 'vector_status__62': 'ready', 'content_hash__62': 'c9811b7d76f2fe68f17d1933ea35b02b00f408072c5b7cb0174e0e28a885db35', 'embedding_model__62': 'mock-embedding', 'content__62': '附录 A. 泛函分析中的反例 45\\n2 映射\\n• 逆映射不连续\\n3\\n定理 3.1 (Riesz 表示定理).\\nLax-Milgram 定理可看作将内积改为满足强制条件 a(u; u) ⩾ \\x0ekuk2 的连续共轭双线性泛函\\na(u; v) 的推广.\\n定理 3.2 (Lax-Milgram 定理).', 'char_end__63': 390, 'page_no__63': 47, 'token_count__63': 195, 'updated_at__63': datetime.datetime(2026, 4, 7, 10, 42, 28, 631685), 'chunk_uid__63': '79f86245-5aea-4927-888c-cb942b30af6d', 'char_start__63': 0, 'metadata_json__63': Jsonb({'page_no': 47}), 'chunk_no__63': 63, 'document_id__63': 39, 'vector_version__63': 1, 'created_at__63': datetime.datetime(2026, 4, 7, 10, 42, 28, 631684), 'deleted_at__63': None, 'vector_status__63': 'ready', 'content_hash__63': 'cfb271fb79bfdeff7f25452a60a8a06777067bb6dab9bb82f45de5e180c5d0d7', 'embedding_model__63': 'mock-embedding', 'content__63': '附录 B\\n套路\\n1 有机会成为一组的东西\\n• 最佳逼近元\\n– 设 X 是赋范线性空间，M 是 X 的有限维子空间， 那么对于任意x 2 X，x 到 M 的距离\\n的最小值能取到.\\n– 如果 M 仅仅是闭子空间，那么虽然可以任意精度逼近，但可能取不到.\\n• 对象分解\\n– 设 X 是 B ... (109 characters truncated) ... 任意 g 2 Y ∗，g(T xn) ! g(y).\\n• T ∗g(xn) ! g(y).\\n• 也就是说，我知道了一部分 X ∗ 中的元素，作用在 fxng 上时，的收敛性.\\n比较，已知 xn 弱收敛到 x，\\n• 我就知道了所有 X ∗ 中的元素，作用在 fxng 上时，的收敛性.\\n46'}]\n(Background on this error at: https://sqlalche.me/e/20/9h9h)"}}}
```

### 失败: test_search_contract.SearchContractTestCase.test_bm25_natural_question_should_return_hilbert_definition_in_top3

```text
Traceback (most recent call last):
  File "/app/test/test_search_contract.py", line 77, in test_bm25_natural_question_should_return_hilbert_definition_in_top3
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
  File "/app/test/test_search_contract.py", line 69, in scenario
    self.assertTrue(
    ~~~~~~~~~~~~~~~^
        any("then we say that X is a Hilbert space" in preview for preview in previews),
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        payload,
        ^^^^^^^^
    )
    ^
AssertionError: False is not true : {'success': True, 'code': 'OK', 'message': 'success', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-07T10:43:00.196864+00:00', 'data': {'query': 'what is Hilbert space?', 'alpha': 1.0, 'retrieval_mode': 'lexical_bm25', 'total': 3, 'items': [{'chunk_id': 5921, 'chunk_uid': '00fd82a6-b3d7-45ca-8191-0c4d4470a067', 'chunk_no': 38, 'page_no': 15, 'score': 6.665651798248291, 'content': '2011 F UNCTIONAL ANALYSIS ALP\n[8] Show that if fM/NAKg is a family of linear subspaces of a linear space X , then MD\\ /NAK M/NAK is a\nlinear subspace of X .\nIf M and N are linear subspaces of a linear space X , under what condition(s) is M[ N a\nlinear subspace of X ?\n12', 'document': {'id': 41, 'document_uid': 'fa3e023f-22f7-4c3a-a934-938445372c68', 'title': 'search_hilbert_question_1775558570247_281473503367952', 'file_name': 'Functional Analysis Notes.pdf', 'category_id': 67, 'version': 1}, 'category': {'id': 67, 'category_code': 'search_hilbert_question_1775558570232_281473503367952', 'name': 'search_hilbert_question_1775558570232_281473503367952'}}, {'chunk_id': 5986, 'chunk_uid': 'd50e6b27-c2d5-480e-a733-e4136be4d538', 'chunk_no': 103, 'page_no': 38, 'score': 5.25549840927124, 'content': 'r a long time until Per Enﬂo in 1973 ans wered it in the negative. He constructed a\nseparable reﬂexive Banach space with no basis.\n2.7.7 Exercise\n[1] Let X be a normed linear space over F. Show that X is ﬁnite-dimensional if and only if every\nbounded sequence in X has a convergent subsequence.\n[2] Complete the proof of Theorem 2.1.1.\n[3] Prove Lemma 2.3.2.\n[4] Prove the claims made in [1] and [2] of Example 2.3.7.\n[5] Prove Theorem 2.5.5.\n[6] Prove Corollary 2.5.8.\n[7] Prove Corollary 2.5.9.\n[8] Prove Corollary 2.5.10.\n[9] Prove Corollary 2.6.2.\n[10] Is .CŒa; b/c141;k/SOHk 1/ complete? What about .CŒa; b/c141;k/SOHk 1/? Fully justify both answers.\n35', 'document': {'id': 41, 'document_uid': 'fa3e023f-22f7-4c3a-a934-938445372c68', 'title': 'search_hilbert_question_1775558570247_281473503367952', 'file_name': 'Functional Analysis Notes.pdf', 'category_id': 67, 'version': 1}, 'category': {'id': 67, 'category_code': 'search_hilbert_question_1775558570232_281473503367952', 'name': 'search_hilbert_question_1775558570232_281473503367952'}}, {'chunk_id': 5886, 'chunk_uid': '985462b3-16df-4f07-9a90-673d8634d2b4', 'chunk_no': 3, 'page_no': 2, 'score': 4.725534915924072, 'content': '. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 36\n3.2 Completeness of Inner Product Spaces . . . . . . . . . . . . . . . . . . . . . . . . . . . . 42\n3.3 Orthogonality . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 42\n3.4 Best Approximation in Hilbert Spaces . . . . . . . . . . . . . . . . . . . . . . . . . . . . 45\n3.5 Orthonormal Sets and Orthonormal Bases . . . . . . . . . . . . . . . . . . . . . . . . . . 49\n4 Bounded Linear Operators and Functionals 62\n4.1 Introduction . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 62\n4.2 Examples of Dual Spaces . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 72\n4.3 The Dual Space of a Hilbert Space . . . . . . . . . . . .', 'document': {'id': 41, 'document_uid': 'fa3e023f-22f7-4c3a-a934-938445372c68', 'title': 'search_hilbert_question_1775558570247_281473503367952', 'file_name': 'Functional Analysis Notes.pdf', 'category_id': 67, 'version': 1}, 'category': {'id': 67, 'category_code': 'search_hilbert_question_1775558570232_281473503367952', 'name': 'search_hilbert_question_1775558570232_281473503367952'}}]}}
```

### 失败: test_search_contract.SearchContractTestCase.test_hybrid_search_chinese_query_should_hit_hilbert_section_in_top3

```text
Traceback (most recent call last):
  File "/app/test/test_search_contract.py", line 105, in test_hybrid_search_chinese_query_should_hit_hilbert_section_in_top3
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
  File "/app/test/test_search_contract.py", line 97, in scenario
    self.assertTrue(
    ~~~~~~~~~~~~~~~^
        any("Hilbert space" in preview for preview in previews),
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        payload,
        ^^^^^^^^
    )
    ^
AssertionError: False is not true : {'success': True, 'code': 'OK', 'message': 'success', 'request_id': None, 'trace_id': None, 'timestamp': '2026-04-07T10:43:21.798651+00:00', 'data': {'query': '什么是希尔伯特空间', 'alpha': 0.5, 'retrieval_mode': 'hybrid', 'total': 3, 'items': [{'chunk_id': 6380, 'chunk_uid': '6b974dcf-2139-4690-b31e-f4228d2c8ca3', 'chunk_no': 188, 'page_no': 71, 'score': 0.2699100375175476, 'content': '/SOHk 0 andk/SOHk on X are equivalent. Hence there are constants ˛\nandˇ such that\n˛kxk0/DC4kxk/DC4ˇkxk0 for all x2 X:\nHence,\nkT xk/DC4kxk0/DC41\n˛kxkD Kkxk;\nwhere KD 1\n˛ . Therefore T is bounded. ■\n4.1.9 Deﬁnition\nLet X and Y be normed linear spaces over a ﬁeld F.\n(1) A sequence .Tn/1\n1\nin B.X; Y/ is said to be uniformly operator convergent to T if\nlim\nn!1\nkTn/NUL TkD 0:\nThis is also referred to as convergence in the uniform topology or convergence in the operator\nnorm topology of B.X; Y/. In this case T is called the uniform operator limit of the sequence\n.Tn/1\n1\n.\n(2) A sequence .Tn/1\n1\nin B.X; Y/ is said to be strongly operator convergent to T if\nlim\nn!1\nkTnx/NUL T xkD 0 for each x2 X:\nIn this case T is called the strong operator limit of the sequence .Tn/1\n1\n.\nOf course, if T is the uni', 'document': {'id': 42, 'document_uid': '35632f61-d429-4a19-b699-45dc1cbecdcd', 'title': 'search_hilbert_cn_1775558591852_281473503368272', 'file_name': 'Functional Analysis Notes.pdf', 'category_id': 68, 'version': 1}, 'category': {'id': 68, 'category_code': 'search_hilbert_cn_1775558591838_281473503368272', 'name': 'search_hilbert_cn_1775558591838_281473503368272'}}, {'chunk_id': 6253, 'chunk_uid': 'e9add5e9-de16-4d33-b9b3-12bc0c551ce6', 'chunk_no': 61, 'page_no': 25, 'score': 0.269867479801178, 'content': '2011 F UNCTIONAL ANALYSIS ALP\nThat is, for each ﬁxed index i , .xn.i//1\n1 is a Cauchy sequence in F. Since F is complete,\nthere exists x.i/2 F such that\nxn.i/! x.i/ as n!1:\nDeﬁne xD.x.1/; x.2/;:::/ . We show that x2`p, and xn! x. T o that end, for each k2 N,\n kX\niD1\njxn.i//NUL xm.i/jp\n! 1\np\n/DC4kxn/NUL xmkpD\n 1X\niD1\njxn.i//NUL xm.i/jp\n! 1\np\n</SI:\nThat is,\nkX\niD1\njxn.i//NUL xm.i/jp </SI p; for all kD 1; 2; 3;::::\nKeep k and n/NAK N ﬁxed and let m!1 . Since we are dealing with a ﬁnite sum,\nkX\niD1\njxn.i//NUL x.i/jp/DC4/SI p:\nNow letting k!1 , then for all n/NAK N ,\n1X\niD1\njxn.i//NUL x.i/jp/DC4/SI p; . 2:3:7:1/\nwhich means that xn/NUL x2`p. Since xn2`p, we have that xD.x/NUL xn/C xn2`p. It also\nfollows from (2.3.7.1) that xn! x as n!1 . ■\n[4] The space `0 of all sequences .xi/1\n1 with only a ﬁ', 'document': {'id': 42, 'document_uid': '35632f61-d429-4a19-b699-45dc1cbecdcd', 'title': 'search_hilbert_cn_1775558591852_281473503368272', 'file_name': 'Functional Analysis Notes.pdf', 'category_id': 68, 'version': 1}, 'category': {'id': 68, 'category_code': 'search_hilbert_cn_1775558591838_281473503368272', 'name': 'search_hilbert_cn_1775558591838_281473503368272'}}, {'chunk_id': 6228, 'chunk_uid': '250edbf4-654e-4a11-b41a-380c05a581e4', 'chunk_no': 36, 'page_no': 14, 'score': 0.26853469014167786, 'content': '2011 F UNCTIONAL ANALYSIS ALP\nProof. Let qD p\np/NUL 1 . If\n1X\nkD1\njxkC ykjpD 0, then the inequality holds. We therefore assume that\n1X\nkD1\njxkC ykjp6D 0. Then\n1X\nkD1\njxkC ykjp D\n1X\nkD1\njxkC ykjp/NUL 1jxkC ykj\n/DC4\n1X\nkD1\njxkC ykjp/NUL 1jxkjC\n1X\nkD1\njxkC ykjp/NUL 1jykj\n/DC4\n 1X\nkD1\njxkC ykj.p/NUL 1/q\n! 1\nq\n2\n4\n 1X\nkD1\njxkjp\n! 1\np\nC\n 1X\nkD1\njykjp\n! 1\np\n3\n5\nD\n 1X\nkD1\njxkC ykjp\n! 1\nq\n2\n4\n 1X\nkD1\njxkjp\n! 1\np\nC\n 1X\nkD1\njykjp\n! 1\np\n3\n5:\nDividing both sides by\n 1X\nkD1\njxkC ykjp\n! 1\nq\n, we have\n 1X\nkD1\njxkC ykjp\n! 1\np\nD\n 1X\nkD1\njxkC ykjp\n!1/NUL 1\nq\n/DC4\n 1X\nkD1\njxkjp\n! 1\np\nC\n 1X\nkD1\njykjp\n! 1\np\n: ■\n1.6.5 Exercise\n[1] Show that the set of all n/STX m real matrices is a real linear space.\n[2] Show that a subset M of a linear space X is a linear subspace if and only if ˛xCˇy2 M\nfor all x; y2 M and all', 'document': {'id': 42, 'document_uid': '35632f61-d429-4a19-b699-45dc1cbecdcd', 'title': 'search_hilbert_cn_1775558591852_281473503368272', 'file_name': 'Functional Analysis Notes.pdf', 'category_id': 68, 'version': 1}, 'category': {'id': 68, 'category_code': 'search_hilbert_cn_1775558591838_281473503368272', 'name': 'search_hilbert_cn_1775558591838_281473503368272'}}]}}
```

### 失败: test_search_contract.SearchContractTestCase.test_search_rejects_empty_query

```text
Traceback (most recent call last):
  File "/app/test/test_search_contract.py", line 42, in test_search_rejects_empty_query
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
  File "/app/test/test_search_contract.py", line 40, in scenario
    self.assert_error(payload, code="INVALID_ARGUMENT", error_type="validation_error")
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/test/base.py", line 64, in assert_error
    self.assertEqual(payload.get("code"), code, payload)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'MCP_TOOL_EXECUTION_ERROR' != 'INVALID_ARGUMENT'
- MCP_TOOL_EXECUTION_ERROR
+ INVALID_ARGUMENT
 : {'success': False, 'code': 'MCP_TOOL_EXECUTION_ERROR', 'message': "Error executing tool kb_search_retrieve: Unable to serialize unknown type: <class 'ValueError'>", 'error': {'type': 'tool_execution_error', 'details': {}}}
```
