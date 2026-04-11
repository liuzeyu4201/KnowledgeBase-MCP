---
name: knowledgebase-mcp
description: 指导 Agent 正确调用本项目知识库 MCP Server，包括分类、暂存文件、文档、批量导入任务与检索接口的标准使用方式。
---


# 知识库 MCP Server 使用 Skill

## 目的

本 Skill 只用于指导 Agent 正确使用当前项目已经实现的知识库 MCP Server。

只描述以下内容：

- 当前可用的 MCP Tool
- 远端文件上传与 `from_staged` 导入标准流程
- 调用顺序、关键参数、常见错误边界

不描述以下内容：

- 内部实现细节
- 网页功能
- 历史已废弃接口
- 与 Agent 调用无关的部署细节


## 适用场景

当 Agent 需要执行以下操作时，使用本 Skill：

- 创建、查询、更新、删除分类
- 上传文件到暂存区
- 从暂存文件导入文档
- 查询、更新、删除文档
- 提交、取消、查询批量导入任务
- 执行知识库检索

---

## 核心结论

1. 远端文件导入必须走两段式流程：
   - 先通过 HTTP 上传文件到暂存区
   - 再通过 `*_from_staged` 的 MCP Tool 完成导入或更新

2. 文档检索粒度是 `chunk`，不是整篇文档。

3. 文档更新采用整篇重建，不做局部 patch。

4. 删除文档时会级联处理：
   - PostgreSQL 文档与切片
   - Milvus 向量
   - 原始文件对象

5. 当前支持的文档类型：
   - `application/pdf`
   - `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
   - `text/markdown`

---

## 服务入口

### MCP 入口

- 路径：`/mcp`
- 典型地址：`http://127.0.0.1:8000/mcp`

### 文件上传 HTTP 入口

- 上传文件：`POST /api/staged-files`

上传成功后，后续 MCP Tool 使用的是：

- `staged_file_id`

不是文件路径，不是文件二进制。

---

## 当前可用 Tool

### 分类

- `kb_category_create`
- `kb_category_get`
- `kb_category_list`
- `kb_category_update`
- `kb_category_delete`

### 文档

- `kb_document_import_from_staged`
- `kb_document_get`
- `kb_document_list`
- `kb_document_update_from_staged`
- `kb_document_delete`
- `kb_document_content_get`

### 暂存文件

- `kb_staged_file_get`
- `kb_staged_file_list`
- `kb_staged_file_delete`

### 批量导入任务

- `kb_document_import_batch_submit_from_staged`
- `kb_document_import_batch_cancel`
- `kb_document_import_batch_get`

### 检索

- `kb_search_retrieve`

---

## 标准工作流

## 1. 创建或确认分类

如果分类不存在，先调用：

- `kb_category_create`

最小参数示例：

```json
{
  "category_code": "math",
  "name": "数学"
}
```

如果分类已存在，先调用：

- `kb_category_get`
- 或 `kb_category_list`

导入文档时优先使用返回的：

- `category_id`

---

## 2. 上传文件到暂存区

调用 HTTP 接口：

- `POST /api/staged-files`

请求方式：

- `multipart/form-data`

必填字段：

- `file`

上传成功后，重点读取：

- `data.staged_file.id`
- `data.staged_file.status`

正常情况下：

- `status = uploaded`

---

## 3. 单文档导入

调用：

- `kb_document_import_from_staged`

必填参数：

- `category_id`
- `title`
- `staged_file_id`

示例：

```json
{
  "category_id": 546,
  "title": "Functional Analysis Notes",
  "staged_file_id": 123
}
```

成功后会：

- 创建文档
- 解析原文
- 切分 chunk
- 写入 PostgreSQL
- 写入 Milvus
- 将暂存文件标记为 `consumed`

---

## 4. 查询文档

### 查询单个文档

调用：

- `kb_document_get`

参数二选一：

- `id`
- `document_uid`

### 查询文档列表

调用：

- `kb_document_list`

常用过滤参数：

- `category_id`
- `title`
- `file_name`
- `parse_status`
- `vector_status`
- `page`
- `page_size`

---

## 5. 查看文档内容

调用：

- `kb_document_content_get`

作用：

- 查看文档原文视图
- 查看已入库的 chunk 原文

常用参数：

- `id` 或 `document_uid`
- `source_page`
- `source_page_size`
- `chunk_page`
- `chunk_page_size`

说明：

- `source_pages` 更接近原件解析后的内容
- `chunks` 是系统真实入库、真实参与检索的文本片段

---

## 6. 更新文档

调用：

- `kb_document_update_from_staged`

### 仅更新元数据

可传：

- `id` 或 `document_uid`
- `title`
- `category_id`

### 替换源文件并重建

先上传新文件，再传：

- `id` 或 `document_uid`
- `staged_file_id`

可选：

- `title`
- `category_id`

说明：

- 传入 `staged_file_id` 后，会执行整篇重建

---

## 7. 删除文档

调用：

- `kb_document_delete`

参数二选一：

- `id`
- `document_uid`

说明：

- 不能删除单个 chunk
- 只能删除整个文档

---

## 8. 删除分类

调用：

- `kb_category_delete`

前提：

- 该分类下不能还有未删除文档

如果分类下仍有文档，会返回：

- `CATEGORY_HAS_DOCUMENTS`

正确顺序：

1. 先删文档
2. 再删分类

---

## 9. 批量导入

调用：

- `kb_document_import_batch_submit_from_staged`

请求核心字段：

- `items`

每个 `item` 至少包含：

- `category_id`
- `title`
- `staged_file_id`

可选：

- `priority`
- `max_attempts`
- `idempotency_key`

提交后可继续调用：

- `kb_document_import_batch_get`
- `kb_document_import_batch_cancel`

---

## 10. 检索

调用：

- `kb_search_retrieve`

核心参数：

- `query`
- `alpha`
- `limit`

可选过滤：

- `category_id`
- `document_id`

`alpha` 语义：

- `0.0`：纯语义检索
- `1.0`：纯 BM25 词法检索
- `0.0 ~ 1.0`：混合检索

说明：

- 返回结果已经过 PostgreSQL 回查
- 可以直接作为上层引用或问答上下文

---

## 最小调用顺序

### 新增一篇文档

1. `kb_category_get` 或 `kb_category_list`
2. 不存在则 `kb_category_create`
3. `POST /api/staged-files`
4. `kb_document_import_from_staged`
5. `kb_document_get` 或 `kb_document_list`
6. 必要时 `kb_search_retrieve`

### 替换一篇文档

1. `POST /api/staged-files`
2. `kb_document_update_from_staged`
3. `kb_document_get`

### 删除一个分类

1. `kb_document_list(category_id=...)`
2. 逐个 `kb_document_delete`
3. `kb_category_delete`

### 批量导入

1. 逐个 `POST /api/staged-files`
2. 收集所有 `staged_file_id`
3. `kb_document_import_batch_submit_from_staged`
4. `kb_document_import_batch_get`
5. 必要时 `kb_document_import_batch_cancel`

---

## 常见错误理解

### 不要直接传文件二进制给 MCP Tool

错误：

- 试图把 PDF / DOCX / Markdown 内容直接塞进 MCP 参数

正确做法：

- 先上传文件
- 再传 `staged_file_id`

### 不要删除单个 chunk

当前系统不提供 chunk 删除接口。

### 不要绕过分类直接导入

导入文档必须绑定：

- `category_id`

### 不要把 Milvus 当主数据源

检索结果只是召回结果，业务真相源仍然是 PostgreSQL。

---

## Agent 执行建议

1. 写操作前，先用查询接口确认目标是否存在。
2. 删除分类前，先查该分类下的文档并清空。
3. 导入或更新文件前，先确认上传成功并拿到 `staged_file_id`。
4. 检索效果不理想时，优先调整：
   - `alpha`
   - `category_id`
   - `document_id`
5. 对于长文档，优先使用文档查询和内容查询接口确认导入结果，再做检索判断。
