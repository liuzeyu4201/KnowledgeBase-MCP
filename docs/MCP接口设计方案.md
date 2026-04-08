# 知识库 MCP Server 接口设计方案

## 1. 文档目的

本文档以当前代码实现为准，定义知识库 MCP Server 已经实现的 MCP Tool、输入输出结构、执行语义、错误处理方式与数据约束。

当前已实现接口：

- `kb_category_create`
- `kb_category_get`
- `kb_category_list`
- `kb_category_update`
- `kb_category_delete`
- `kb_document_import`
- `kb_document_import_batch_submit`
- `kb_document_import_batch_cancel`
- `kb_document_import_batch_get`
- `kb_document_get`
- `kb_document_list`
- `kb_document_update`
- `kb_document_delete`
- `kb_search_retrieve`

---

## 2. 统一协议

## 2.1 Tool 命名规范

统一命名为：

- `kb_<domain>_<action>`

示例：

- `kb_category_create`
- `kb_document_import`
- `kb_search_retrieve`

---

## 2.2 通用输入字段

所有 Tool 输入均为 JSON Object，以下字段在当前实现中为通用可选字段：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `request_id` | `string` | 否 | 请求标识 |
| `operator` | `string` | 否 | 操作主体标识 |
| `trace_id` | `string` | 否 | 链路追踪标识 |

说明：

- 读取类接口通常使用 `request_id`、`trace_id`
- 写入类接口通常同时接受 `operator`
- 服务端会原样回传 `request_id` 与 `trace_id`

---

## 2.3 通用成功响应

当前所有 Tool 统一返回：

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "request_id": "req_001",
  "trace_id": "trace_001",
  "timestamp": "2026-04-08T10:00:00+00:00",
  "data": {}
}
```

字段说明：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `success` | `boolean` | 是 | 成功时固定为 `true` |
| `code` | `string` | 是 | 成功时固定为 `OK` |
| `message` | `string` | 是 | 当前固定为 `success` |
| `request_id` | `string` | 否 | 请求标识 |
| `trace_id` | `string` | 否 | 链路追踪标识 |
| `timestamp` | `string` | 是 | UTC ISO 8601 时间 |
| `data` | `object` | 是 | 业务结果 |

---

## 2.4 通用错误响应

当前所有 Tool 统一返回：

```json
{
  "success": false,
  "code": "INVALID_ARGUMENT",
  "message": "invalid request",
  "request_id": "req_001",
  "trace_id": "trace_001",
  "timestamp": "2026-04-08T10:00:00+00:00",
  "error": {
    "type": "validation_error",
    "details": {
      "errors": []
    }
  }
}
```

字段说明：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `success` | `boolean` | 是 | 失败时固定为 `false` |
| `code` | `string` | 是 | 错误码 |
| `message` | `string` | 是 | 错误描述 |
| `request_id` | `string` | 否 | 请求标识 |
| `trace_id` | `string` | 否 | 链路追踪标识 |
| `timestamp` | `string` | 是 | UTC ISO 8601 时间 |
| `error.type` | `string` | 是 | 错误类型 |
| `error.details` | `object` | 是 | 错误详情 |

错误类型：

- `validation_error`
- `business_error`
- `not_found`
- `system_error`

说明：

- 当前实现会把错误详情递归转换为可 JSON 序列化结构
- 参数错误不会再被包装成非标准 MCP 执行错误

---

## 2.5 当前代码实际使用的错误码

### 2.5.1 通用错误码

| 错误码 | 类型 | 说明 |
|---|---|---|
| `OK` | - | 成功 |
| `INVALID_ARGUMENT` | `validation_error` | 参数不合法 |
| `DB_ERROR` | `system_error` | 数据库访问失败 |
| `INTERNAL_ERROR` | `system_error` | 未归类内部异常 |

### 2.5.2 分类相关错误码

| 错误码 | 类型 | 说明 |
|---|---|---|
| `CATEGORY_CODE_CONFLICT` | `business_error` | 分类编码冲突 |
| `CATEGORY_NAME_CONFLICT` | `business_error` | 分类名称冲突 |
| `CATEGORY_NOT_FOUND` | `not_found` | 分类不存在 |
| `CATEGORY_HAS_DOCUMENTS` | `business_error` | 分类下仍有未删除文档，禁止删除 |

### 2.5.3 文档相关错误码

| 错误码 | 类型 | 说明 |
|---|---|---|
| `DOCUMENT_NOT_FOUND` | `not_found` | 文档不存在 |
| `DOCUMENT_PARSE_FAILED` | `system_error` | 文档无法生成切片 |
| `DOCUMENT_IMPORT_FAILED` | `system_error` | 文档导入失败 |
| `DOCUMENT_UPDATE_FAILED` | `system_error` | 文档更新失败 |
| `DOCUMENT_DELETE_FAILED` | `system_error` | 文档删除失败 |
| `DELETE_CLEANUP_FAILED` | `system_error` | 文档已删但暂存文件清理失败 |
| `UPDATE_CLEANUP_FAILED` | `system_error` | 文档已更新但旧文件清理失败 |
| `CONSISTENCY_ROLLBACK_FAILED` | `system_error` | 跨存储回滚失败 |
| `DELETE_FILE_STAGE_FAILED` | `system_error` | 删除前文件暂存失败 |

说明：

- `file_content_base64` 非法时，当前返回 `INVALID_ARGUMENT`
- `mime_type` 非 `application/pdf` 时，当前返回 `INVALID_ARGUMENT`

### 2.5.4 批量导入任务相关错误码

| 错误码 | 类型 | 说明 |
|---|---|---|
| `IMPORT_TASK_NOT_FOUND` | `not_found` | 批量导入任务不存在 |
| `TASK_CANCELED` | `business_error` | 任务在协作式检查点被取消 |

说明：

- `TASK_CANCELED` 主要用于 worker 内部执行链路，不是对外接口的典型终态错误
- 对外取消接口成功时，仍返回 `OK`

---

## 3. 数据约束

## 3.1 分类字段约束

| 字段 | 约束 |
|---|---|
| `category_code` | `1~64` 字符，只允许字母、数字、下划线、中划线 |
| `name` | `1~128` 字符，去除首尾空格后不能为空 |
| `description` | 最大 `512` 字符 |
| `status` | 仅允许 `0` 或 `1` |

补充说明：

- 分类查询默认过滤软删除数据
- 分类列表的 `category_code`、`name` 为模糊匹配

---

## 3.2 文档字段约束

| 字段 | 约束 |
|---|---|
| `category_id` | 正整数，且分类必须存在 |
| `title` | `1~256` 字符 |
| `file_name` | `1~256` 字符 |
| `mime_type` | 当前仅允许 `application/pdf` |
| `file_content_base64` | 必填时必须能被正确解码且内容非空 |
| `document_uid` | `1~36` 字符 |

补充说明：

- 当前代码不接受“本地路径导入”，只接受 `file_content_base64`
- 更新文档时，如果传 `file_content_base64`，则 `file_name` 和 `mime_type` 必须同时传入

---

## 3.3 检索字段约束

| 字段 | 约束 |
|---|---|
| `query` | `1~2048` 字符，去除首尾空格后不能为空 |
| `alpha` | `0.0~1.0` |
| `limit` | `1~20`，默认 `10` |
| `category_id` | 可选，正整数 |
| `document_id` | 可选，正整数 |

说明：

- 当前检索参数是 `limit`，不是 `top_k`
- 当前过滤参数是顶层字段，不是 `filters` 对象

---

## 3.4 批量导入任务字段约束

| 字段 | 约束 |
|---|---|
| `priority` | `0~1000`，默认 `50`，数值越大优先级越高 |
| `max_attempts` | `1~10`，默认 `3` |
| `idempotency_key` | 可选，最大长度 `128` |
| `items` | 至少 `1` 条，最多 `100` 条 |
| `items[].category_id` | 正整数 |
| `items[].title` | `1~256` 字符 |
| `items[].file_name` | `1~256` 字符 |
| `items[].mime_type` | 当前仅支持 `application/pdf` |
| `items[].file_content_base64` | 必填，必须可正确解码 |
| `items[].priority` | 可选，`0~1000` |

补充说明：

- 当前批量导入接口先将文件写入任务暂存目录，不直接把大体积文件内容持久化到数据库
- 任务查询默认返回子任务明细，除非显式指定 `include_items=false`

---

## 4. Tool 设计

## 4.1 分类接口

### 4.1.1 `kb_category_create`

用途：

- 新增分类

输入参数：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `category_code` | `string` | 是 | 分类编码 |
| `name` | `string` | 是 | 分类名称 |
| `description` | `string` | 否 | 分类描述 |
| `status` | `integer` | 否 | 默认 `1` |
| `request_id` | `string` | 否 | 请求标识 |
| `operator` | `string` | 否 | 操作主体 |
| `trace_id` | `string` | 否 | 链路追踪 |

执行语义：

- 校验参数
- 校验 `category_code` 唯一
- 校验 `name` 唯一
- 写入 `kb_category`

成功返回：

- `data.category`

主要错误码：

- `INVALID_ARGUMENT`
- `CATEGORY_CODE_CONFLICT`
- `CATEGORY_NAME_CONFLICT`

---

### 4.1.2 `kb_category_get`

用途：

- 按 `id` 或 `category_code` 查询单个分类

输入参数：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | `integer` | 否 | 分类主键 |
| `category_code` | `string` | 否 | 分类编码 |
| `request_id` | `string` | 否 | 请求标识 |
| `trace_id` | `string` | 否 | 链路追踪 |

执行语义：

- `id` 与 `category_code` 至少传一个
- 如果同时传入，必须指向同一记录
- 仅返回未软删除分类

成功返回：

- `data.category`

主要错误码：

- `INVALID_ARGUMENT`
- `CATEGORY_NOT_FOUND`

---

### 4.1.3 `kb_category_list`

用途：

- 分页查询分类列表

输入参数：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `category_code` | `string` | 否 | 分类编码模糊过滤 |
| `name` | `string` | 否 | 分类名称模糊过滤 |
| `status` | `integer` | 否 | 分类状态过滤 |
| `page` | `integer` | 否 | 默认 `1` |
| `page_size` | `integer` | 否 | 默认 `20`，范围 `1~100` |
| `request_id` | `string` | 否 | 请求标识 |
| `trace_id` | `string` | 否 | 链路追踪 |

执行语义：

- 过滤条件均为顶层字段
- 默认按 `id DESC` 返回
- 默认过滤软删除数据

成功返回：

- `data.items`
- `data.pagination`

主要错误码：

- `INVALID_ARGUMENT`

---

### 4.1.4 `kb_category_update`

用途：

- 更新分类信息

输入参数：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | `integer` | 否 | 分类主键 |
| `category_code` | `string` | 否 | 当前分类编码 |
| `new_category_code` | `string` | 否 | 新分类编码 |
| `name` | `string` | 否 | 新名称 |
| `description` | `string` | 否 | 新描述 |
| `status` | `integer` | 否 | 新状态 |
| `request_id` | `string` | 否 | 请求标识 |
| `operator` | `string` | 否 | 操作主体 |
| `trace_id` | `string` | 否 | 链路追踪 |

执行语义：

- 按 `id` 或 `category_code` 定位目标分类
- 至少需要一个更新字段
- 变更编码和名称时校验唯一性

成功返回：

- `data.category`

主要错误码：

- `INVALID_ARGUMENT`
- `CATEGORY_NOT_FOUND`
- `CATEGORY_CODE_CONFLICT`
- `CATEGORY_NAME_CONFLICT`

---

### 4.1.5 `kb_category_delete`

用途：

- 删除分类

输入参数：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | `integer` | 否 | 分类主键 |
| `category_code` | `string` | 否 | 分类编码 |
| `request_id` | `string` | 否 | 请求标识 |
| `operator` | `string` | 否 | 操作主体 |
| `trace_id` | `string` | 否 | 链路追踪 |

执行语义：

- 当前为软删除
- 删除前会检查分类下是否仍有关联未删除文档

成功返回：

- `data.deleted`
- `data.category_id`
- `data.category_code`
- `data.deleted_at`

主要错误码：

- `INVALID_ARGUMENT`
- `CATEGORY_NOT_FOUND`
- `CATEGORY_HAS_DOCUMENTS`

---

## 4.2 文档接口

### 4.2.1 `kb_document_import`

用途：

- 导入 PDF 文档并写入切片与检索索引

输入参数：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `category_id` | `integer` | 是 | 分类 ID |
| `title` | `string` | 是 | 文档标题 |
| `file_name` | `string` | 是 | 文件名 |
| `mime_type` | `string` | 是 | 当前仅支持 `application/pdf` |
| `file_content_base64` | `string` | 是 | PDF 内容 Base64 |
| `request_id` | `string` | 否 | 请求标识 |
| `operator` | `string` | 否 | 操作主体 |
| `trace_id` | `string` | 否 | 链路追踪 |

执行语义：

- 校验分类存在
- 保存原始 PDF
- 创建文档记录
- 解析 PDF
- 切片并写入 `kb_chunk`
- 生成稠密向量
- 写入 Milvus
- 由 Milvus 自动生成 BM25 稀疏索引
- 更新文档状态为 `success/ready`

成功返回：

- `data.document`
- `data.chunks.count`
- `data.vector_store`

`vector_store` 当前固定返回：

- `provider=milvus`
- `collection_name`
- `dense_model`
- `sparse_strategy=milvus_bm25`

主要错误码：

- `INVALID_ARGUMENT`
- `CATEGORY_NOT_FOUND`
- `DOCUMENT_PARSE_FAILED`
- `DOCUMENT_IMPORT_FAILED`
- `CONSISTENCY_ROLLBACK_FAILED`

---

### 4.2.2 `kb_document_import_batch_submit`

用途：

- 提交批量文档导入异步任务

输入参数：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `items` | `array<object>` | 是 | 批量导入子项 |
| `priority` | `integer` | 否 | 任务优先级，默认 `50` |
| `max_attempts` | `integer` | 否 | 最大尝试次数，默认 `3` |
| `idempotency_key` | `string` | 否 | 幂等键 |
| `request_id` | `string` | 否 | 请求标识 |
| `operator` | `string` | 否 | 操作主体 |
| `trace_id` | `string` | 否 | 链路追踪 |

`items[]` 字段：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `category_id` | `integer` | 是 | 分类 ID |
| `title` | `string` | 是 | 文档标题 |
| `file_name` | `string` | 是 | 文件名 |
| `mime_type` | `string` | 是 | 当前仅支持 `application/pdf` |
| `file_content_base64` | `string` | 是 | PDF 内容 Base64 |
| `priority` | `integer` | 否 | 子任务优先级，默认继承主任务优先级 |

执行语义：

- 校验批量任务参数
- 若传入 `idempotency_key` 且已有同键任务，则直接返回已有任务
- 先将每个文件写入任务暂存目录
- 在数据库中创建主任务和子任务记录
- 返回任务主状态与子任务明细
- 实际导入由后台 worker 异步执行

成功返回：

- `data.task`

`task` 当前包含：

- 任务基础信息
- 聚合进度字段
- `items` 子任务列表

主要错误码：

- `INVALID_ARGUMENT`
- `DB_ERROR`
- `INTERNAL_ERROR`

---

### 4.2.3 `kb_document_import_batch_cancel`

用途：

- 取消批量文档导入异步任务

输入参数：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | `integer` | 否 | 任务主键 |
| `task_uid` | `string` | 否 | 稳定任务标识 |
| `request_id` | `string` | 否 | 请求标识 |
| `operator` | `string` | 否 | 操作主体 |
| `trace_id` | `string` | 否 | 链路追踪 |

执行语义：

- `id` 和 `task_uid` 至少传一个
- 若任务尚未开始，直接标记任务和全部子任务为 `canceled`
- 若任务正在执行，设置 `cancel_requested=true`
- worker 在协作式检查点停止后续执行
- 已完成子任务不回滚，未执行子任务标记为 `canceled`

成功返回：

- `data.task`

主要错误码：

- `INVALID_ARGUMENT`
- `IMPORT_TASK_NOT_FOUND`

---

### 4.2.4 `kb_document_import_batch_get`

用途：

- 查询批量文档导入异步任务状态

输入参数：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | `integer` | 否 | 任务主键 |
| `task_uid` | `string` | 否 | 稳定任务标识 |
| `include_items` | `boolean` | 否 | 是否返回子任务明细，默认 `true` |
| `request_id` | `string` | 否 | 请求标识 |
| `trace_id` | `string` | 否 | 链路追踪 |

执行语义：

- `id` 和 `task_uid` 至少传一个
- 若同时传入，必须指向同一任务
- 默认返回子任务明细

成功返回：

- `data.task`

`task.status` 当前可能值：

- `queued`
- `running`
- `cancel_requested`
- `canceled`
- `success`
- `partial_success`
- `failed`

主要错误码：

- `INVALID_ARGUMENT`
- `IMPORT_TASK_NOT_FOUND`

---

### 4.2.5 `kb_document_get`

用途：

- 按 `id` 或 `document_uid` 查询单个文档

输入参数：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | `integer` | 否 | 文档主键 |
| `document_uid` | `string` | 否 | 文档稳定标识 |
| `request_id` | `string` | 否 | 请求标识 |
| `trace_id` | `string` | 否 | 链路追踪 |

执行语义：

- `id` 和 `document_uid` 至少传一个
- 若同时传入，必须指向同一文档
- 默认仅返回未删除文档

成功返回：

- `data.document`

`document` 当前包含：

- 文档基础字段
- `storage_uri`
- `file_sha256`
- `parse_status`
- `vector_status`
- `version`
- `chunk_count`
- `last_error`
- 嵌套 `category`

主要错误码：

- `INVALID_ARGUMENT`
- `DOCUMENT_NOT_FOUND`

---

### 4.2.6 `kb_document_list`

用途：

- 分页查询文档列表

输入参数：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `category_id` | `integer` | 否 | 分类过滤 |
| `title` | `string` | 否 | 标题模糊过滤 |
| `file_name` | `string` | 否 | 文件名模糊过滤 |
| `parse_status` | `string` | 否 | 解析状态过滤 |
| `vector_status` | `string` | 否 | 向量状态过滤 |
| `page` | `integer` | 否 | 默认 `1` |
| `page_size` | `integer` | 否 | 默认 `20`，范围 `1~100` |
| `request_id` | `string` | 否 | 请求标识 |
| `trace_id` | `string` | 否 | 链路追踪 |

执行语义：

- 所有过滤条件都是顶层字段
- `title`、`file_name` 使用模糊匹配
- 默认按 `id DESC` 返回
- 默认仅返回未删除文档

成功返回：

- `data.items`
- `data.pagination`

主要错误码：

- `INVALID_ARGUMENT`

---

### 4.2.7 `kb_document_update`

用途：

- 更新文档元数据
- 或整篇替换 PDF 并重建切片与向量

输入参数：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | `integer` | 否 | 文档主键 |
| `document_uid` | `string` | 否 | 文档稳定标识 |
| `category_id` | `integer` | 否 | 新分类 ID |
| `title` | `string` | 否 | 新标题 |
| `file_name` | `string` | 否 | 新文件名 |
| `mime_type` | `string` | 否 | 当前仅支持 `application/pdf` |
| `file_content_base64` | `string` | 否 | 新 PDF 内容 |
| `request_id` | `string` | 否 | 请求标识 |
| `operator` | `string` | 否 | 操作主体 |
| `trace_id` | `string` | 否 | 链路追踪 |

执行语义：

- `id` 和 `document_uid` 至少传一个
- 至少需要一个更新字段
- 只更新元数据时，仅更新 `category_id`、`title`
- 如果传 `file_content_base64`，则必须同时传 `file_name` 和 `mime_type`
- 替换 PDF 时采用整篇重建
- 成功后文档 `version + 1`

成功返回：

- `data.document`
- `data.chunks.count`
- `data.vector_store`

主要错误码：

- `INVALID_ARGUMENT`
- `DOCUMENT_NOT_FOUND`
- `CATEGORY_NOT_FOUND`
- `DOCUMENT_PARSE_FAILED`
- `DOCUMENT_UPDATE_FAILED`
- `UPDATE_CLEANUP_FAILED`
- `CONSISTENCY_ROLLBACK_FAILED`

---

### 4.2.8 `kb_document_delete`

用途：

- 删除文档，并级联处理切片、Milvus 记录与原始文件

输入参数：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | `integer` | 否 | 文档主键 |
| `document_uid` | `string` | 否 | 文档稳定标识 |
| `request_id` | `string` | 否 | 请求标识 |
| `operator` | `string` | 否 | 操作主体 |
| `trace_id` | `string` | 否 | 链路追踪 |

执行语义：

- 当前业务库删除方式为软删除
- 删除前会备份 Milvus 记录并暂存原始文件
- 数据库提交成功后，才最终删除暂存文件

成功返回：

- `data.deleted`
- `data.document_id`
- `data.document_uid`
- `data.chunk_count`

主要错误码：

- `INVALID_ARGUMENT`
- `DOCUMENT_NOT_FOUND`
- `DOCUMENT_DELETE_FAILED`
- `DELETE_CLEANUP_FAILED`
- `CONSISTENCY_ROLLBACK_FAILED`

---

## 4.3 检索接口

### 4.3.1 `kb_search_retrieve`

用途：

- 执行语义检索、BM25 检索或混合检索

输入参数：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `query` | `string` | 是 | 查询文本 |
| `alpha` | `float` | 否 | 默认 `0.0` |
| `limit` | `integer` | 否 | 默认 `10`，范围 `1~20` |
| `category_id` | `integer` | 否 | 分类过滤 |
| `document_id` | `integer` | 否 | 文档过滤 |
| `request_id` | `string` | 否 | 请求标识 |
| `operator` | `string` | 否 | 操作主体 |
| `trace_id` | `string` | 否 | 链路追踪 |

执行语义：

- `alpha <= 0.0`：纯语义检索
- `alpha >= 1.0`：纯 BM25 检索
- `0.0 < alpha < 1.0`：混合检索
- 纯 BM25 检索不依赖 Embedding 服务
- 命中 Milvus 后，会回查 PostgreSQL 补全文档和分类信息
- 只返回未删除且文档状态为 `success/ready` 的结果

当前 `retrieval_mode` 返回值：

- `semantic`
- `lexical_bm25`
- `hybrid`

当前结果结构：

- `data.query`
- `data.alpha`
- `data.retrieval_mode`
- `data.total`
- `data.items`

每个 `item` 包含：

- `chunk_id`
- `chunk_uid`
- `chunk_no`
- `page_no`
- `score`
- `content`
- `document`
- `category`

补充说明：

- 检索前会做轻量查询归一化，用于清洗英文问句模板和扩展部分中英术语别名
- 当前代码参数名是 `limit`，不是 `top_k`

主要错误码：

- `INVALID_ARGUMENT`
- `DB_ERROR`
- `INTERNAL_ERROR`

---

## 5. 当前实现与早期设计的主要差异

当前已经按代码修正以下差异：

- 接口范围不再只有分类查询、文档导入、检索，文档和分类的更新、删除接口也已实现
- 批量导入异步任务接口已经实现，不再停留在设计阶段
- 文档查询和分类列表的过滤参数均为顶层字段，不使用 `filters` 对象
- 检索接口当前参数名是 `limit`，不是 `top_k`
- 检索接口当前只支持 `category_id` 和 `document_id` 两个过滤字段
- 文档导入当前是同步链路，不再描述为“可同步可异步”
- 批量导入接口当前采用“任务提交同步落库 + 后台 worker 异步执行”的模式
- `alpha=1.0` 当前明确表示纯 BM25 检索，返回 `retrieval_mode=lexical_bm25`
- 错误码按实际代码更新，删除了文档中未被代码使用的占位错误码

---

## 6. 结论

当前接口文档已经与实际代码对齐，可作为以下工作的基线：

- 上层 Agent 调用约定
- MCP Tool 契约测试
- 后续接口扩展
- 回归测试与联调文档
