# 知识库 MCP Server 使用 Skill

## 适用范围

当 Agent 需要调用本项目提供的知识库 MCP Server 时，使用本 Skill。

本 Skill 只描述**当前代码真实实现**的接口与推荐调用顺序，不描述历史已移除接口。

---

## 核心原则

1. 远端文件导入必须走两段式流程：
   - 先通过 HTTP 上传接口把文件传到暂存区
   - 再通过 `*_from_staged` 的 MCP Tool 完成导入或更新

2. 不要再尝试调用以下旧接口：
   - `kb_document_import`
   - `kb_document_update`
   - `kb_document_import_batch_submit`

3. 文档检索粒度是 `chunk`，不是整篇文档。

4. Milvus 检索结果已经回查 PostgreSQL，返回结果可直接给上层问答或引用逻辑使用。

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

- 上传：`POST /api/staged-files`
- 单文件查询：`GET /api/staged-files/{staged_file_id}`
- 文件列表：`GET /api/staged-files`
- 文件删除：`DELETE /api/staged-files/{staged_file_id}`

---

## 统一响应约定

成功响应：

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "data": {}
}
```

失败响应：

```json
{
  "success": false,
  "code": "INVALID_ARGUMENT",
  "message": "invalid request",
  "error": {
    "type": "validation_error",
    "details": {}
  }
}
```

常见 `error.type`：

- `validation_error`
- `business_error`
- `not_found`
- `system_error`

---

## 标准工作流

## 1. 创建分类

先用 `kb_category_create` 建分类，再进行文档导入。

最小参数：

```json
{
  "category_code": "math",
  "name": "数学"
}
```

推荐做法：

- `category_code` 使用稳定英文标识
- 后续文档接口优先使用返回的 `category.id`

---

## 2. 上传文件到暂存区

### HTTP 接口

- `POST /api/staged-files`

### 请求方式

- `multipart/form-data`

### 必填字段

- `file`

### 可选字段

- `request_id`
- `operator`
- `trace_id`

### curl 示例

```bash
curl -X POST http://127.0.0.1:8000/api/staged-files \
  -F "file=@/path/to/example.pdf;type=application/pdf"
```

### 成功后关注字段

- `data.staged_file.id`
- `data.staged_file.staged_file_uid`
- `data.staged_file.status`

通常上传成功后的状态为：

- `uploaded`

---

## 3. 从暂存文件导入知识库文档

### MCP Tool

- `kb_document_import_from_staged`

### 必填参数

- `category_id`
- `title`
- `staged_file_id`

### 示例

```json
{
  "category_id": 2,
  "title": "Functional Analysis Notes",
  "staged_file_id": 123
}
```

### 结果

成功后会：

- 创建文档记录
- 解析源文件
- 生成切片
- 写入 PostgreSQL
- 写入 Milvus
- 将暂存文件状态变为 `consumed`

### 适用场景

- 单文件导入 PDF
- 单文件导入 Markdown
- 单文件导入 Word

---

## 4. 查询文档

### 查询单个文档

- Tool：`kb_document_get`

参数二选一：

- `id`
- `document_uid`

示例：

```json
{
  "id": 10
}
```

### 查询文档列表

- Tool：`kb_document_list`

可选过滤：

- `category_id`
- `title`
- `file_name`
- `parse_status`
- `vector_status`
- `page`
- `page_size`

典型用途：

- 查某个分类下有哪些文档
- 查失败文档
- 查向量未就绪文档

---

## 5. 更新文档

### 仅更新元数据

使用 `kb_document_update_from_staged`，但不传 `staged_file_id`。

可更新字段：

- `category_id`
- `title`

示例：

```json
{
  "id": 10,
  "title": "新的标题"
}
```

### 替换源文件并重建文档

先上传新文件，再调用 `kb_document_update_from_staged`。

参数：

- `id` 或 `document_uid`
- 可选 `category_id`
- 可选 `title`
- `staged_file_id`

示例：

```json
{
  "id": 10,
  "title": "更新后的标题",
  "staged_file_id": 456
}
```

说明：

- 更新采用整篇重建
- 不做局部 patch

---

## 6. 删除文档

### MCP Tool

- `kb_document_delete`

参数二选一：

- `id`
- `document_uid`

示例：

```json
{
  "id": 10
}
```

删除会级联处理：

- 文档记录
- chunk 记录
- Milvus 向量
- 源文件

---

## 7. 检索知识库

### MCP Tool

- `kb_search_retrieve`

### 必填参数

- `query`

### 可选参数

- `alpha`
- `limit`
- `category_id`
- `document_id`

### `alpha` 语义

- `0.0`：纯语义检索
- `1.0`：纯 BM25 词法检索
- `0.0 ~ 1.0` 之间：混合检索

### 示例

```json
{
  "query": "what is Hilbert space?",
  "alpha": 1.0,
  "limit": 5
}
```

### 推荐经验

- 英文术语问法、精确关键词召回：优先 `alpha=1.0`
- 自然语言语义问法：优先 `alpha=0.0 ~ 0.5`
- 已知分类范围时，尽量加 `category_id`

---

## 8. 批量异步导入

### 提交任务

- Tool：`kb_document_import_batch_submit_from_staged`

### 必填结构

顶层参数：

- `items`

每个 `item` 最少包含：

- `category_id`
- `title`
- `staged_file_id`

可选：

- `priority`

顶层可选：

- `priority`
- `max_attempts`
- `idempotency_key`

### 示例

```json
{
  "items": [
    {
      "category_id": 2,
      "title": "文档A",
      "staged_file_id": 101
    },
    {
      "category_id": 2,
      "title": "文档B",
      "staged_file_id": 102,
      "priority": 80
    }
  ],
  "priority": 50,
  "max_attempts": 3,
  "idempotency_key": "batch-import-001"
}
```

### 任务状态查询

- Tool：`kb_document_import_batch_get`

参数：

- `id` 或 `task_uid`
- `include_items` 默认 `true`

轮询时建议：

- 平时设 `include_items=false`
- 只有排错时再看子项明细

### 任务取消

- Tool：`kb_document_import_batch_cancel`

参数：

- `id` 或 `task_uid`

说明：

- 支持 queued 直接取消
- running 状态下是协作式取消
- 刚取消后可能先看到 `cancel_requested`
- 终态通常是：
  - `success`
  - `partial_success`
  - `failed`
  - `canceled`

---

## 9. 暂存文件治理

### 查询单个暂存文件

- Tool：`kb_staged_file_get`

参数：

- `id` 或 `staged_file_uid`

适合：

- 确认上传是否成功
- 确认是否已被消费

### 查询暂存文件列表

- Tool：`kb_staged_file_list`

可选过滤：

- `status`
- `mime_type`
- `linked_document_id`
- `page`
- `page_size`

适合：

- 找未消费文件
- 找失败文件
- 做清理治理

### 删除暂存文件

- Tool：`kb_staged_file_delete`

参数：

- `id` 或 `staged_file_uid`

说明：

- 已消费文件通常不允许删除
- 这是治理接口，不是业务导入接口

---

## 分类接口清单

### `kb_category_create`

用途：

- 新建分类

最小参数：

- `category_code`
- `name`

可选：

- `description`
- `status`

### `kb_category_get`

用途：

- 查询单个分类

参数：

- `id` 或 `category_code`

### `kb_category_list`

用途：

- 分页查询分类

可选过滤：

- `category_code`
- `name`
- `status`
- `page`
- `page_size`

### `kb_category_update`

用途：

- 更新分类

定位参数：

- `id` 或 `category_code`

可修改字段：

- `new_category_code`
- `name`
- `description`
- `status`

### `kb_category_delete`

用途：

- 删除分类

限制：

- 分类下仍有文档时会拒绝删除

---

## 推荐调用顺序

## 场景一：新增一个 PDF 到知识库

1. `kb_category_get` 或 `kb_category_list` 找分类
2. 如果分类不存在，调用 `kb_category_create`
3. `POST /api/staged-files` 上传 PDF
4. 调 `kb_document_import_from_staged`
5. 用 `kb_document_get` 或 `kb_document_list` 验证
6. 用 `kb_search_retrieve` 做召回验证

## 场景二：批量导入多个文件

1. 逐个调用 `POST /api/staged-files`
2. 收集所有 `staged_file_id`
3. 调 `kb_document_import_batch_submit_from_staged`
4. 轮询 `kb_document_import_batch_get`
5. 如需中断，调用 `kb_document_import_batch_cancel`

## 场景三：替换已存在文档的源文件

1. 先用 `kb_document_get` 确认目标文档
2. `POST /api/staged-files` 上传新文件
3. 调 `kb_document_update_from_staged`
4. 再用 `kb_document_get` 和 `kb_search_retrieve` 校验

---

## 明确禁止事项

1. 不要调用已经移除的旧接口：
   - `kb_document_import`
   - `kb_document_update`
   - `kb_document_import_batch_submit`

2. 不要把大文件内容直接塞进 MCP Tool 参数。

3. 不要把 Milvus 返回结果直接当最终业务结果，必须使用系统已封装好的检索返回。

4. 不要把分类名硬编码进文档内容代替 `category_id`。

---

## 终态与判断规则

### 文档导入成功判断

满足以下任一即可继续下游流程：

- `kb_document_import_from_staged` 返回 `success=true`
- `kb_document_get` 看到：
  - `parse_status=success`
  - `vector_status=ready`

### 批量任务终态

以下状态视为终态：

- `success`
- `partial_success`
- `failed`
- `canceled`

以下状态不是终态：

- `pending`
- `queued`
- `running`
- `cancel_requested`

---

## 给其他 Agent 的执行建议

1. 优先使用返回的主键：
   - `category.id`
   - `document.id`
   - `staged_file.id`
   - `task.id`

2. 写入类操作后，尽量立即用查询类接口校验结果。

3. 批量任务不要假设“提交成功等于导入成功”，必须轮询任务状态。

4. 对远端大文件，一律走：
   - 上传接口
   - `*_from_staged`

5. 如果目标是“新增文档”，优先顺序固定为：
   - 分类
   - 上传
   - 导入
   - 校验
   - 检索
