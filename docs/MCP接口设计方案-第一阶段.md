# 知识库 MCP Server 接口设计方案（第一阶段）

## 1. 文档目标

本文档用于定义知识库 MCP Server 第一阶段接口设计，面向上层 Agent 调用场景，明确各个 MCP Tool 的输入、输出、执行语义、错误处理方式与数据约束。

第一阶段优先覆盖以下能力：

- 分类新增
- 分类查询
- 文档导入
- 文本检索

后续阶段将在此基础上扩展以下能力：

- 文档查询
- 切片管理
- 向量写入
- 文档更新
- 文档删除

---

## 2. 设计原则

第一阶段接口设计遵循以下原则：

- 语义清晰：每个 Tool 只承担一个明确业务动作
- 输入明确：参数名称、类型、必填项、校验规则明确定义
- 输出统一：采用统一响应结构，便于 Agent 解析与编排
- 错误可识别：区分参数错误、业务冲突、资源不存在、系统异常
- 便于扩展：为分页、过滤、权限、审计、追踪预留扩展字段
- 幂等可控：对可重试操作预留幂等控制能力
- 状态可观测：所有响应支持返回请求标识与时间信息

---

## 3. 接口范围

第一阶段定义以下 MCP Tool：

- `kb_category_create`：新增分类
- `kb_category_get`：查询单个分类详情
- `kb_category_list`：查询分类列表
- `kb_document_import`：导入 PDF 文档
- `kb_search_retrieve`：执行知识库检索

说明：

- `kb_category_create` 用于创建分类
- `kb_category_get` 用于按唯一标识读取单个分类
- `kb_category_list` 用于分页查询和条件过滤
- `kb_document_import` 用于导入 PDF、创建文档记录、触发切片与向量写入
- `kb_search_retrieve` 用于基于 Milvus 执行混合检索，并通过 PostgreSQL 回查业务数据

---

## 4. 通用协议约定

## 4.1 Tool 命名规范

命名规则统一为：

`kb_<domain>_<action>`

当前阶段示例：

- `kb_category_create`
- `kb_category_get`
- `kb_category_list`

命名要求：

- 前缀 `kb` 表示知识库域
- 中间段表示资源域，例如 `category`、`document`、`chunk`
- 末尾段表示动作，例如 `create`、`get`、`list`、`update`、`delete`

---

## 4.2 通用输入约定

所有 Tool 输入均采用 JSON Object。

通用字段如下：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `request_id` | `string` | 否 | 调用方请求标识，用于链路追踪 |
| `operator` | `string` | 否 | 调用主体标识，第一阶段可传 Agent 名称或调用方标识 |
| `trace_id` | `string` | 否 | 链路追踪标识 |

字段约定：

- 第一阶段通用字段均为可选
- 服务端可在响应中回传这些字段
- 后续可扩展审计与权限体系时继续复用

---

## 4.3 通用输出结构

所有 Tool 统一返回如下结构：

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "request_id": "req_001",
  "trace_id": "trace_001",
  "timestamp": "2026-04-07T15:00:00Z",
  "data": {}
}
```

字段定义如下：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `success` | `boolean` | 是 | 是否执行成功 |
| `code` | `string` | 是 | 结果码 |
| `message` | `string` | 是 | 结果说明 |
| `request_id` | `string` | 否 | 请求标识 |
| `trace_id` | `string` | 否 | 链路追踪标识 |
| `timestamp` | `string` | 是 | 服务端响应时间，ISO 8601 格式 |
| `data` | `object` | 否 | 业务结果数据 |

响应要求：

- 成功时 `success=true`
- 失败时 `success=false`
- `code` 使用标准错误码
- `message` 用于简洁描述结果
- `data` 仅承载业务数据，不承载错误说明

---

## 4.4 错误响应结构

错误响应统一如下：

```json
{
  "success": false,
  "code": "CATEGORY_NAME_CONFLICT",
  "message": "category name already exists",
  "request_id": "req_001",
  "trace_id": "trace_001",
  "timestamp": "2026-04-07T15:00:00Z",
  "error": {
    "type": "business_error",
    "details": {
      "field": "name",
      "value": "产品文档"
    }
  }
}
```

字段定义如下：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `success` | `boolean` | 是 | 固定为 `false` |
| `code` | `string` | 是 | 错误码 |
| `message` | `string` | 是 | 错误描述 |
| `request_id` | `string` | 否 | 请求标识 |
| `trace_id` | `string` | 否 | 链路追踪标识 |
| `timestamp` | `string` | 是 | 响应时间 |
| `error.type` | `string` | 是 | 错误类型 |
| `error.details` | `object` | 否 | 错误详情 |

错误类型定义：

- `validation_error`：参数校验失败
- `business_error`：业务约束冲突
- `not_found`：目标资源不存在
- `system_error`：服务内部异常

---

## 4.5 标准错误码约定

第一阶段统一使用以下错误码：

| 错误码 | 错误类型 | 说明 |
|---|---|---|
| `OK` | - | 执行成功 |
| `INVALID_ARGUMENT` | `validation_error` | 参数不合法 |
| `MISSING_REQUIRED_FIELD` | `validation_error` | 缺少必填字段 |
| `INVALID_FIELD_FORMAT` | `validation_error` | 字段格式错误 |
| `CATEGORY_NAME_CONFLICT` | `business_error` | 分类名称冲突 |
| `CATEGORY_CODE_CONFLICT` | `business_error` | 分类编码冲突 |
| `CATEGORY_NOT_FOUND` | `not_found` | 分类不存在 |
| `CATEGORY_STATUS_INVALID` | `business_error` | 分类状态不合法 |
| `DOCUMENT_NOT_FOUND` | `not_found` | 文档不存在 |
| `DOCUMENT_IMPORT_FAILED` | `system_error` | 文档导入失败 |
| `DOCUMENT_PARSE_FAILED` | `system_error` | 文档解析失败 |
| `FILE_NOT_FOUND` | `not_found` | 文件不存在 |
| `FILE_TYPE_UNSUPPORTED` | `validation_error` | 文件类型不支持 |
| `FILE_TOO_LARGE` | `validation_error` | 文件大小超限 |
| `SEARCH_QUERY_EMPTY` | `validation_error` | 检索文本为空 |
| `SEARCH_ALPHA_INVALID` | `validation_error` | 检索权重参数不合法 |
| `SEARCH_TOPK_INVALID` | `validation_error` | 检索返回数量不合法 |
| `SEARCH_EXECUTION_FAILED` | `system_error` | 检索执行失败 |
| `PAGE_OUT_OF_RANGE` | `validation_error` | 分页参数超出允许范围 |
| `INTERNAL_ERROR` | `system_error` | 系统内部异常 |
| `DB_ERROR` | `system_error` | 数据库访问异常 |

---

## 5. 数据约束定义

第一阶段分类实体基于 `kb_category` 表，接口层遵循以下约束：

| 字段 | 约束 |
|---|---|
| `category_code` | 长度 `1~64`，仅允许字母、数字、下划线、中划线，需全局唯一 |
| `name` | 长度 `1~128`，去除首尾空格后不能为空，需全局唯一 |
| `description` | 最大长度 `512` |
| `status` | 仅允许 `1` 或 `0` |

补充约束：

- 所有字符串字段在入库前应执行首尾空格清理
- 空字符串按无效值处理
- 查询接口默认过滤软删除数据
- 第一阶段分类删除能力未开放，因此查询结果默认仅返回 `deleted_at IS NULL` 的记录

### 5.1 文档导入字段约束

第一阶段文档导入接口基于 `kb_document` 表与文件存储能力，遵循以下约束：

| 字段 | 约束 |
|---|---|
| `category_id` | 必填，必须为有效且未删除的分类 ID |
| `title` | 长度 `1~256`，去除首尾空格后不能为空 |
| `file_name` | 长度 `1~256`，不能为空 |
| `file_content_base64` | 必填，与 `file_name` 组合用于生成原始文件 |
| `mime_type` | 第一阶段固定支持 `application/pdf` |
| `file_size` | 必须大于 `0`，上限由服务端配置控制 |

补充约束：

- 第一阶段仅支持 PDF 文件导入
- 文件摘要 `file_sha256` 由服务端生成
- 文档导入成功后必须创建文档记录
- 切片与向量写入可以同步执行，也可以由任务链路异步执行

### 5.2 检索字段约束

第一阶段检索接口基于 Milvus 检索与 PostgreSQL 回查，遵循以下约束：

| 字段 | 约束 |
|---|---|
| `query` | 必填，去除首尾空格后不能为空 |
| `alpha` | 取值范围 `0.0~1.0` |
| `top_k` | 取值范围 `1~100`，默认 `10` |
| `filters.category_id` | 可选，必须为正整数 |
| `filters.document_id` | 可选，必须为正整数 |
| `filters.document_ids` | 可选，数组长度建议不超过 `100` |

检索权重约定：

- `alpha = 0.0`：纯语义检索，仅使用向量检索分数
- `alpha = 1.0`：纯全文匹配，仅使用关键词匹配分数
- `0.0 < alpha < 1.0`：混合检索，按配置公式融合语义分数与全文匹配分数

执行要求：

- 检索核心能力由 Milvus 承担
- PostgreSQL 负责业务回查、状态过滤和结果补充

---

## 6. Tool 设计

## 6.1 `kb_category_create`

### 6.1.1 目标

用于新增分类记录。

### 6.1.2 执行语义

- 创建一个新的分类
- 若分类编码已存在，则返回冲突错误
- 若分类名称已存在，则返回冲突错误
- 默认创建为启用状态，除非显式传入 `status=0`

### 6.1.3 输入参数

```json
{
  "request_id": "req_001",
  "operator": "agent_a",
  "trace_id": "trace_001",
  "category_code": "product_docs",
  "name": "产品文档",
  "description": "产品说明书与产品资料分类",
  "status": 1
}
```

参数定义如下：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `request_id` | `string` | 否 | 请求标识 |
| `operator` | `string` | 否 | 调用主体标识 |
| `trace_id` | `string` | 否 | 链路追踪标识 |
| `category_code` | `string` | 是 | 分类编码 |
| `name` | `string` | 是 | 分类名称 |
| `description` | `string` | 否 | 分类描述 |
| `status` | `integer` | 否 | 分类状态，默认 `1` |

### 6.1.4 输入校验规则

- `category_code` 必填
- `name` 必填
- `category_code` 长度必须在 `1~64`
- `name` 长度必须在 `1~128`
- `description` 长度不得超过 `512`
- `status` 仅允许 `0` 或 `1`
- `category_code` 仅允许字符集：`a-z`、`A-Z`、`0-9`、`_`、`-`
- `category_code` 与 `name` 在业务上均需唯一

### 6.1.5 成功输出

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "request_id": "req_001",
  "trace_id": "trace_001",
  "timestamp": "2026-04-07T15:00:00Z",
  "data": {
    "category": {
      "id": 1,
      "category_code": "product_docs",
      "name": "产品文档",
      "description": "产品说明书与产品资料分类",
      "status": 1,
      "created_at": "2026-04-07T15:00:00Z",
      "updated_at": "2026-04-07T15:00:00Z"
    }
  }
}
```

### 6.1.6 失败输出

分类编码冲突：

```json
{
  "success": false,
  "code": "CATEGORY_CODE_CONFLICT",
  "message": "category code already exists",
  "request_id": "req_001",
  "trace_id": "trace_001",
  "timestamp": "2026-04-07T15:00:00Z",
  "error": {
    "type": "business_error",
    "details": {
      "field": "category_code",
      "value": "product_docs"
    }
  }
}
```

分类名称冲突：

```json
{
  "success": false,
  "code": "CATEGORY_NAME_CONFLICT",
  "message": "category name already exists",
  "request_id": "req_001",
  "trace_id": "trace_001",
  "timestamp": "2026-04-07T15:00:00Z",
  "error": {
    "type": "business_error",
    "details": {
      "field": "name",
      "value": "产品文档"
    }
  }
}
```

参数缺失：

```json
{
  "success": false,
  "code": "MISSING_REQUIRED_FIELD",
  "message": "missing required field",
  "request_id": "req_001",
  "trace_id": "trace_001",
  "timestamp": "2026-04-07T15:00:00Z",
  "error": {
    "type": "validation_error",
    "details": {
      "field": "name"
    }
  }
}
```

---

## 6.2 `kb_category_get`

### 6.2.1 目标

用于查询单个分类详情。

### 6.2.2 执行语义

- 根据唯一条件读取单个分类
- 支持按 `id` 或 `category_code` 查询
- `id` 与 `category_code` 至少传一个
- 若同时传入，优先要求两者指向同一分类记录
- 查询结果默认不返回软删除记录

### 6.2.3 输入参数

```json
{
  "request_id": "req_002",
  "trace_id": "trace_002",
  "id": 1,
  "category_code": "product_docs"
}
```

参数定义如下：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `request_id` | `string` | 否 | 请求标识 |
| `trace_id` | `string` | 否 | 链路追踪标识 |
| `id` | `integer` | 否 | 分类主键 |
| `category_code` | `string` | 否 | 分类编码 |

### 6.2.4 输入校验规则

- `id` 与 `category_code` 至少传一个
- `id` 必须大于 `0`
- `category_code` 若传入，需满足编码格式要求
- 若 `id` 与 `category_code` 同时传入且不匹配，返回参数错误

### 6.2.5 成功输出

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "request_id": "req_002",
  "trace_id": "trace_002",
  "timestamp": "2026-04-07T15:10:00Z",
  "data": {
    "category": {
      "id": 1,
      "category_code": "product_docs",
      "name": "产品文档",
      "description": "产品说明书与产品资料分类",
      "status": 1,
      "created_at": "2026-04-07T15:00:00Z",
      "updated_at": "2026-04-07T15:00:00Z"
    }
  }
}
```

### 6.2.6 失败输出

分类不存在：

```json
{
  "success": false,
  "code": "CATEGORY_NOT_FOUND",
  "message": "category not found",
  "request_id": "req_002",
  "trace_id": "trace_002",
  "timestamp": "2026-04-07T15:10:00Z",
  "error": {
    "type": "not_found",
    "details": {
      "id": 1
    }
  }
}
```

参数不合法：

```json
{
  "success": false,
  "code": "INVALID_ARGUMENT",
  "message": "id or category_code is required",
  "request_id": "req_002",
  "trace_id": "trace_002",
  "timestamp": "2026-04-07T15:10:00Z",
  "error": {
    "type": "validation_error",
    "details": {}
  }
}
```

---

## 6.3 `kb_category_list`

### 6.3.1 目标

用于按条件分页查询分类列表。

### 6.3.2 执行语义

- 支持按分类名称、分类编码、状态进行过滤
- 支持分页查询
- 默认按 `id DESC` 返回
- 默认仅查询未软删除数据

### 6.3.3 输入参数

```json
{
  "request_id": "req_003",
  "trace_id": "trace_003",
  "filters": {
    "category_code": "product",
    "name": "产品",
    "status": 1
  },
  "page": 1,
  "page_size": 20
}
```

参数定义如下：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `request_id` | `string` | 否 | 请求标识 |
| `trace_id` | `string` | 否 | 链路追踪标识 |
| `filters` | `object` | 否 | 过滤条件 |
| `filters.category_code` | `string` | 否 | 分类编码模糊过滤 |
| `filters.name` | `string` | 否 | 分类名称模糊过滤 |
| `filters.status` | `integer` | 否 | 分类状态过滤 |
| `page` | `integer` | 否 | 页码，默认 `1` |
| `page_size` | `integer` | 否 | 每页数量，默认 `20` |

### 6.3.4 输入校验规则

- `page` 必须大于等于 `1`
- `page_size` 允许范围 `1~100`
- `filters.status` 仅允许 `0` 或 `1`
- 所有字符串过滤项在处理前执行首尾空格清理

### 6.3.5 成功输出

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "request_id": "req_003",
  "trace_id": "trace_003",
  "timestamp": "2026-04-07T15:20:00Z",
  "data": {
    "items": [
      {
        "id": 2,
        "category_code": "manuals",
        "name": "使用手册",
        "description": "设备和系统使用手册",
        "status": 1,
        "created_at": "2026-04-07T15:05:00Z",
        "updated_at": "2026-04-07T15:05:00Z"
      },
      {
        "id": 1,
        "category_code": "product_docs",
        "name": "产品文档",
        "description": "产品说明书与产品资料分类",
        "status": 1,
        "created_at": "2026-04-07T15:00:00Z",
        "updated_at": "2026-04-07T15:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 2,
      "has_next": false
    }
  }
}
```

### 6.3.6 空结果输出

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "request_id": "req_003",
  "trace_id": "trace_003",
  "timestamp": "2026-04-07T15:20:00Z",
  "data": {
    "items": [],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 0,
      "has_next": false
    }
  }
}
```

### 6.3.7 失败输出

分页参数非法：

```json
{
  "success": false,
  "code": "PAGE_OUT_OF_RANGE",
  "message": "page_size must be between 1 and 100",
  "request_id": "req_003",
  "trace_id": "trace_003",
  "timestamp": "2026-04-07T15:20:00Z",
  "error": {
    "type": "validation_error",
    "details": {
      "field": "page_size",
      "value": 1000
    }
  }
}
```

---

## 6.4 `kb_document_import`

### 6.4.1 目标

用于导入 PDF 文档，并创建文档主记录。

### 6.4.2 执行语义

- 接收 PDF 文件内容与基础元数据
- 校验分类是否存在且可用
- 将原始 PDF 写入文件存储
- 创建 `kb_document` 记录
- 触发 PDF 解析、切片生成、向量写入链路
- 默认返回文档基础信息和当前处理状态

第一阶段处理模式约定：

- 支持同步导入模式
- 支持受理后异步处理模式
- 响应中必须明确返回 `parse_status` 与 `vector_status`

### 6.4.3 输入参数

```json
{
  "request_id": "req_101",
  "operator": "agent_a",
  "trace_id": "trace_101",
  "category_id": 1,
  "title": "A1000 产品说明书",
  "file_name": "A1000.pdf",
  "mime_type": "application/pdf",
  "file_content_base64": "JVBERi0xLjQKJ..."
}
```

参数定义如下：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `request_id` | `string` | 否 | 请求标识 |
| `operator` | `string` | 否 | 调用主体标识 |
| `trace_id` | `string` | 否 | 链路追踪标识 |
| `category_id` | `integer` | 是 | 归属分类 ID |
| `title` | `string` | 是 | 文档标题 |
| `file_name` | `string` | 是 | 原始文件名 |
| `mime_type` | `string` | 是 | 文件 MIME 类型 |
| `file_content_base64` | `string` | 是 | PDF 文件内容，Base64 编码 |

### 6.4.4 输入校验规则

- `category_id` 必填且必须大于 `0`
- `title` 必填，长度必须在 `1~256`
- `file_name` 必填
- `mime_type` 必须为 `application/pdf`
- `file_content_base64` 必填且必须可被正确解码
- 文件大小不得超过服务端配置上限
- 分类不存在时返回 `CATEGORY_NOT_FOUND`

### 6.4.5 成功输出

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "request_id": "req_101",
  "trace_id": "trace_101",
  "timestamp": "2026-04-07T16:00:00Z",
  "data": {
    "document": {
      "id": 1001,
      "document_uid": "c8f2bf4e-7fd6-4572-bae7-9b5bb5d6ef0a",
      "category_id": 1,
      "title": "A1000 产品说明书",
      "source_type": "pdf",
      "file_name": "A1000.pdf",
      "mime_type": "application/pdf",
      "file_size": 2483921,
      "file_sha256": "8c30e5b9e6f2d4f2496cf9dbb7af33f7dbfd887744b4e9dbe2cbfe0f85f26d49",
      "parse_status": "processing",
      "vector_status": "pending",
      "version": 1,
      "chunk_count": 0,
      "created_at": "2026-04-07T16:00:00Z",
      "updated_at": "2026-04-07T16:00:00Z"
    }
  }
}
```

### 6.4.6 失败输出

分类不存在：

```json
{
  "success": false,
  "code": "CATEGORY_NOT_FOUND",
  "message": "category not found",
  "request_id": "req_101",
  "trace_id": "trace_101",
  "timestamp": "2026-04-07T16:00:00Z",
  "error": {
    "type": "not_found",
    "details": {
      "field": "category_id",
      "value": 999
    }
  }
}
```

文件类型不支持：

```json
{
  "success": false,
  "code": "FILE_TYPE_UNSUPPORTED",
  "message": "only pdf is supported in phase one",
  "request_id": "req_101",
  "trace_id": "trace_101",
  "timestamp": "2026-04-07T16:00:00Z",
  "error": {
    "type": "validation_error",
    "details": {
      "field": "mime_type",
      "value": "application/msword"
    }
  }
}
```

导入失败：

```json
{
  "success": false,
  "code": "DOCUMENT_IMPORT_FAILED",
  "message": "document import failed",
  "request_id": "req_101",
  "trace_id": "trace_101",
  "timestamp": "2026-04-07T16:00:00Z",
  "error": {
    "type": "system_error",
    "details": {
      "stage": "storage"
    }
  }
}
```

---

## 6.5 `kb_search_retrieve`

### 6.5.1 目标

用于执行知识库检索，并返回切片级结果。

### 6.5.2 执行语义

- 接收查询文本、过滤条件与检索参数
- 检索核心能力由 Milvus 承担
- Milvus 负责语义检索、全文匹配能力承载以及混合检索打分
- PostgreSQL 负责根据 `chunk_id` 回查切片、文档、分类等业务数据
- 返回经过业务过滤后的最终结果

第一阶段检索模式约定：

- 支持纯语义检索
- 支持纯全文匹配
- 支持混合检索

混合检索权重参数：

- `alpha = 0.0`：纯语义检索，仅使用向量检索
- `alpha = 1.0`：纯全文匹配
- `0.0 < alpha < 1.0`：混合检索

推荐融合表达式：

`final_score = (1 - alpha) * semantic_score + alpha * keyword_score`

### 6.5.3 输入参数

```json
{
  "request_id": "req_201",
  "operator": "agent_a",
  "trace_id": "trace_201",
  "query": "A1000 设备支持哪些通信协议",
  "alpha": 0.3,
  "top_k": 5,
  "filters": {
    "category_id": 1,
    "document_id": 1001
  }
}
```

参数定义如下：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `request_id` | `string` | 否 | 请求标识 |
| `operator` | `string` | 否 | 调用主体标识 |
| `trace_id` | `string` | 否 | 链路追踪标识 |
| `query` | `string` | 是 | 检索文本 |
| `alpha` | `number` | 否 | 检索权重参数，默认 `0.0` |
| `top_k` | `integer` | 否 | 返回结果数量，默认 `10` |
| `filters` | `object` | 否 | 检索过滤条件 |
| `filters.category_id` | `integer` | 否 | 分类过滤 |
| `filters.document_id` | `integer` | 否 | 单文档过滤 |
| `filters.document_ids` | `integer[]` | 否 | 多文档过滤 |

### 6.5.4 输入校验规则

- `query` 必填，清理首尾空格后不能为空
- `alpha` 取值必须在 `0.0~1.0`
- `top_k` 取值必须在 `1~100`
- `filters.category_id` 如传入必须大于 `0`
- `filters.document_id` 如传入必须大于 `0`
- `filters.document_ids` 中每个元素必须大于 `0`
- `filters.document_id` 与 `filters.document_ids` 不建议同时传入

### 6.5.5 成功输出

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "request_id": "req_201",
  "trace_id": "trace_201",
  "timestamp": "2026-04-07T16:10:00Z",
  "data": {
    "query": "A1000 设备支持哪些通信协议",
    "alpha": 0.3,
    "top_k": 5,
    "items": [
      {
        "chunk_id": 90001,
        "document_id": 1001,
        "document_uid": "c8f2bf4e-7fd6-4572-bae7-9b5bb5d6ef0a",
        "category_id": 1,
        "category_name": "产品文档",
        "title": "A1000 产品说明书",
        "page_no": 12,
        "chunk_no": 31,
        "content": "A1000 设备支持 Modbus TCP、MQTT 和 OPC UA 协议。",
        "score": 0.9123,
        "semantic_score": 0.9411,
        "keyword_score": 0.8450,
        "vector_version": 1
      }
    ],
    "search_meta": {
      "engine": "milvus",
      "mode": "hybrid",
      "returned": 1
    }
  }
}
```

### 6.5.6 空结果输出

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "request_id": "req_201",
  "trace_id": "trace_201",
  "timestamp": "2026-04-07T16:10:00Z",
  "data": {
    "query": "A1000 设备支持哪些通信协议",
    "alpha": 0.3,
    "top_k": 5,
    "items": [],
    "search_meta": {
      "engine": "milvus",
      "mode": "hybrid",
      "returned": 0
    }
  }
}
```

### 6.5.7 失败输出

检索文本为空：

```json
{
  "success": false,
  "code": "SEARCH_QUERY_EMPTY",
  "message": "query must not be empty",
  "request_id": "req_201",
  "trace_id": "trace_201",
  "timestamp": "2026-04-07T16:10:00Z",
  "error": {
    "type": "validation_error",
    "details": {
      "field": "query"
    }
  }
}
```

权重参数非法：

```json
{
  "success": false,
  "code": "SEARCH_ALPHA_INVALID",
  "message": "alpha must be between 0.0 and 1.0",
  "request_id": "req_201",
  "trace_id": "trace_201",
  "timestamp": "2026-04-07T16:10:00Z",
  "error": {
    "type": "validation_error",
    "details": {
      "field": "alpha",
      "value": 1.2
    }
  }
}
```

检索执行失败：

```json
{
  "success": false,
  "code": "SEARCH_EXECUTION_FAILED",
  "message": "search execution failed",
  "request_id": "req_201",
  "trace_id": "trace_201",
  "timestamp": "2026-04-07T16:10:00Z",
  "error": {
    "type": "system_error",
    "details": {
      "engine": "milvus"
    }
  }
}
```

---

## 7. 执行语义补充约定

## 7.1 事务语义

第一阶段接口采用如下事务语义。

要求如下：

- `kb_category_create` 在同一事务内完成唯一性校验与写入
- `kb_category_get` 和 `kb_category_list` 采用只读查询
- `kb_document_import` 在文档主记录创建阶段采用数据库事务控制
- `kb_document_import` 涉及文件存储、PDF 解析、Milvus 写入时，采用最终一致性处理
- `kb_search_retrieve` 不开启写事务，采用只读链路执行
- 若数据库异常发生，统一返回 `DB_ERROR` 或 `INTERNAL_ERROR`

---

## 7.2 幂等语义

第一阶段约定如下：

- `kb_category_create` 默认非幂等
- `kb_document_import` 默认非幂等
- 调用方若重复提交相同 `category_code` 或 `name`，返回冲突错误
- 后续如需支持幂等创建，可新增 `idempotency_key` 扩展字段

---

## 7.3 排序语义

第一阶段 `kb_category_list` 固定排序如下：

- 默认按 `id DESC`

后续如需支持自定义排序，可扩展以下字段：

- `sort_by`
- `sort_order`

---

## 7.4 软删除语义

第一阶段分类查询接口默认过滤软删除数据。

约定如下：

- `deleted_at IS NULL` 的记录视为有效数据
- 已软删除分类不在 `get` 与 `list` 结果中返回
- 已软删除文档与切片不参与 `kb_search_retrieve` 结果返回
- 后续如需管理已删除数据，可扩展 `include_deleted` 查询参数

---

## 7.5 检索执行语义

第一阶段检索链路采用以下执行方式：

- Milvus 是检索核心执行引擎
- 语义检索由 Milvus 向量检索完成
- 全文匹配能力由 Milvus 稀疏向量或全文匹配相关能力承载
- 混合检索统一在 Milvus 侧完成主召回与主排序
- PostgreSQL 仅用于业务回查、状态过滤和结果补充

标准链路如下：

1. 接收检索请求
2. 生成查询向量和关键词检索表达
3. 调用 Milvus 执行召回和打分
4. 获取命中的 `chunk_id`
5. 使用 PostgreSQL 回查 `kb_chunk`、`kb_document`、`kb_category`
6. 返回最终结果

---

## 8. MCP Tool 输入输出摘要

## 8.1 `kb_category_create`

输入核心字段：

- `category_code`
- `name`
- `description`
- `status`

输出核心字段：

- `category.id`
- `category.category_code`
- `category.name`
- `category.description`
- `category.status`

---

## 8.2 `kb_category_get`

输入核心字段：

- `id` 或 `category_code`

输出核心字段：

- `category.id`
- `category.category_code`
- `category.name`
- `category.description`
- `category.status`

---

## 8.3 `kb_category_list`

输入核心字段：

- `filters`
- `page`
- `page_size`

输出核心字段：

- `items`
- `pagination.page`
- `pagination.page_size`
- `pagination.total`
- `pagination.has_next`

---

## 8.4 `kb_document_import`

输入核心字段：

- `category_id`
- `title`
- `file_name`
- `mime_type`
- `file_content_base64`

输出核心字段：

- `document.id`
- `document.document_uid`
- `document.category_id`
- `document.parse_status`
- `document.vector_status`
- `document.version`

---

## 8.5 `kb_search_retrieve`

输入核心字段：

- `query`
- `alpha`
- `top_k`
- `filters`

输出核心字段：

- `items[].chunk_id`
- `items[].document_id`
- `items[].content`
- `items[].score`
- `items[].semantic_score`
- `items[].keyword_score`
- `search_meta.engine`
- `search_meta.mode`

## 9. 后续扩展预留

后续阶段将在当前接口体系上继续扩展以下 Tool：

- `kb_category_update`
- `kb_category_delete`
- `kb_document_get`
- `kb_document_list`
- `kb_document_delete`
- `kb_chunk_list`
- `kb_chunk_get`
- `kb_vector_rebuild`
- `kb_document_update`
- `kb_document_reimport`
- `kb_search_rerank`

后续扩展字段预留如下：

- `operator`
- `trace_id`
- `tenant_id`
- `idempotency_key`
- `permissions`
- `audit_context`

---

## 10. 第一阶段接口基线

第一阶段 MCP Server 接口基线定义如下：

- 使用统一 Tool 命名规范：`kb_<domain>_<action>`
- 使用统一响应结构：`success/code/message/data`
- 使用统一错误结构：`error.type/error.details`
- 第一阶段 Tool 包括分类创建、分类详情查询、分类列表查询、文档导入、知识库检索
- 分类接口拆分为创建、单体查询、列表查询三个独立 Tool
- 分类主键查询与分类编码查询统一由 `kb_category_get` 承载
- 分类列表查询统一由 `kb_category_list` 承载分页与过滤
- 文档导入统一由 `kb_document_import` 承载
- 检索统一由 `kb_search_retrieve` 承载
- 检索核心能力由 Milvus 承担
- PostgreSQL 作为关系型业务主库，负责文档、切片、分类回查与业务过滤

该文档作为知识库 MCP Server 第一阶段接口设计基线，直接用于后续：

- MCP Tool 定义
- Pydantic Schema 设计
- Service 接口实现
- Repository 查询接口实现
- 错误码与异常体系设计
