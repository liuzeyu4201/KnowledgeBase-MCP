# MinIO 文件存储设计方案

## 1. 设计目标

本文档描述当前已经落地的 MinIO 文件存储方案，并记录后续可演进方向，覆盖以下文件类型：

- 暂存上传原件
- 正式文档原件
- 文档更新过程中产生的新旧版本原件

本方案不改变当前知识库的核心业务边界：

- PostgreSQL 仍然是业务主库
- Milvus 仍然只负责向量检索
- MinIO 负责原始文件对象存储

本方案当前**不引入多租户权限模型**，但会在对象命名、元数据字段和目录前缀中预留未来演进空间。

---

## 2. 当前实现状态

### 2.1 当前业务文件存储方式

当前项目中的业务文件由 [file_storage.py](/Users/token/Projects/KnowledgeBase/KnowledgeBase/knowledgebase/integrations/storage/file_storage.py) 负责，当前默认写入 MinIO：

- 暂存文件 bucket：`kb-staged-files`
- 正式文档 bucket：`kb-documents`

当前涉及的数据库实体：

- `kb_staged_file`
- `kb_document`

其中：

- `kb_staged_file.storage_backend` 当前默认值为 `minio`
- `kb_staged_file.storage_uri` 当前保存 `s3://bucket/key`
- `kb_document.storage_uri` 当前保存正式原件的 `s3://bucket/key`
- `kb_storage_gc_task` 当前用于记录删除失败后的对象清理任务

### 2.2 当前 MinIO 的实际用途

当前开发与生产编排中已经包含 MinIO，当前已经同时承担两类职责：

- `docker/docker-compose.dev.yml`
- `docker/docker-compose.prod.yml`

1. Milvus 的底层对象存储依赖
2. 业务文件与暂存文件的对象存储

结论：

- 当前 MinIO 已部署
- 业务文件原件当前已经保存到 MinIO
- 数据库通过 `storage_uri` 和 `storage_backend` 记录对象引用
- 删除失败时通过 `kb_storage_gc_task` 做后台补偿清理

---

## 3. 总体设计原则

### 3.1 存储职责边界

新的职责划分如下：

- PostgreSQL：保存文件业务元数据、生命周期状态、对象引用关系
- MinIO：保存原始文件对象本体
- Milvus：保存向量索引

MinIO 不承担：

- 分类、文档、切片主数据管理
- 任务状态管理
- 一致性真相源

### 3.2 一致性原则

必须保证以下目标：

- 不出现数据库存在记录、对象文件不存在的残缺状态
- 不出现文档已删除、对象仍长期滞留且无人可感知的孤儿文件
- 不出现暂存文件已消费但仍被再次导入的状态错乱

约束原则：

- **数据库是文件生命周期真相源**
- **对象存储删除采用“可追踪、可重试”的最终一致性**
- **对象上传失败时优先同步补偿**
- **对象删除失败时必须落库记录待清理状态，不能静默失败**

### 3.3 兼容与演进原则

为了便于后续支持：

- 多租户
- 外部对象存储替换
- 版本化文件管理
- 文件审计

本方案要求数据库中不要只存 `storage_uri` 字符串，还要补充**可结构化解析的对象定位字段**。

---

## 4. MinIO Bucket 与对象路径设计

## 4.1 Bucket 规划

业务文件不要与 Milvus 内部对象混放。

建议新增两个独立 Bucket：

- `kb-staged-files`
- `kb-documents`

说明：

- `kb-staged-files`：仅用于远端上传后的暂存原件
- `kb-documents`：仅用于正式知识库文档原件

不建议：

- 与 Milvus 使用同一个 Bucket
- 通过前缀勉强区分 Milvus 内部对象和业务对象

原因：

- 运维边界不清晰
- 生命周期规则难隔离
- 后续治理和排障困难

## 4.2 对象 Key 设计

虽然当前不做多租户，但对象 key 必须为未来留命名空间。

建议命名规则：

### 暂存文件对象

```text
staged/global/{yyyy}/{mm}/{dd}/{staged_file_uid}/{safe_file_name}
```

示例：

```text
staged/global/2026/04/11/1d6a.../functional-analysis-notes.pdf
```

### 正式文档对象

```text
documents/global/category-{category_id}/{document_uid}/v{version}/{safe_file_name}
```

示例：

```text
documents/global/category-546/3c8f.../v1/functional-analysis-notes.pdf
```

未来如需多租户，只需把 `global` 替换为：

```text
tenant/{tenant_id}
```

### 命名要求

- 保留 `uid` 级唯一目录，避免重名覆盖
- 文件名只作为可读信息，不作为唯一标识
- 任何业务逻辑都不能依赖对象 key 中的文件名判断文件身份

---

## 5. 数据库模型调整建议

## 5.1 `kb_staged_file` 调整

当前 `kb_staged_file` 已具备：

- `storage_backend`
- `storage_uri`

建议增加以下字段：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `storage_bucket` | `VARCHAR(128)` | 是 | MinIO bucket 名称 |
| `storage_key` | `VARCHAR(1024)` | 是 | 对象 key |
| `object_etag` | `VARCHAR(128)` | 否 | 上传后对象 etag |
| `object_version_id` | `VARCHAR(128)` | 否 | 若未来开启 bucket versioning，可保存版本号 |
| `storage_backend` | `VARCHAR(32)` | 是 | 固定为 `minio`，兼容未来多后端 |

保留 `storage_uri`，但其语义应调整为规范化 URI，例如：

```text
s3://kb-staged-files/staged/global/2026/04/11/xxx/file.pdf
```

`storage_uri` 继续保留的原因：

- 便于日志输出
- 便于调试
- 便于跨系统展示

但业务实现不应只靠解析 `storage_uri` 字符串。

## 5.2 `kb_document` 调整

当前 `kb_document` 只有：

- `storage_uri`

建议补充：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `storage_backend` | `VARCHAR(32)` | 是 | 正式文档文件存储后端 |
| `storage_bucket` | `VARCHAR(128)` | 是 | 正式文档原件所在 bucket |
| `storage_key` | `VARCHAR(1024)` | 是 | 正式文档原件对象 key |
| `object_etag` | `VARCHAR(128)` | 否 | 正式对象 etag |
| `object_version_id` | `VARCHAR(128)` | 否 | 对象版本号，预留未来开启版本控制 |

### 设计结论

为了兼容未来演进，`kb_staged_file` 和 `kb_document` 最终都应同时持有：

- 人类可读的 `storage_uri`
- 程序可靠使用的 `storage_bucket + storage_key + storage_backend`

---

## 6. 文件生命周期设计

## 6.1 暂存文件生命周期

状态建议保持现有主语义，并扩展为更清晰的对象生命周期：

- `uploaded`
- `consumed`
- `expired`
- `deleted`
- `failed`

含义如下：

- `uploaded`：对象已成功写入 MinIO，数据库记录已创建，允许被导入
- `consumed`：已经被正式文档消费，不允许重复导入
- `expired`：超过 TTL 未被消费，等待清理
- `deleted`：暂存对象及数据库记录已删除
- `failed`：上传或后续处理失败，但需要保留故障信息

## 6.2 正式文档生命周期

正式文档原件遵循当前文档生命周期：

- 导入成功后成为正式原件
- 更新时生成新对象版本
- 删除文档时删除正式原件对象

注意：

- 文档对象不做“就地覆盖”
- 更新采用**新对象写入 + 旧对象延迟清理**

这样更利于补偿和回滚。

---

## 7. 一致性设计

## 7.1 上传暂存文件一致性

目标：不留下“对象存在但数据库无记录”的失控文件。

推荐流程：

1. 服务端生成 `staged_file_uid`
2. 流式上传到 MinIO 的暂存 key
3. 获得 `etag`、大小、sha256
4. 开启数据库事务，写入 `kb_staged_file`
5. 事务提交成功后，上传完成

失败处理：

- 如果对象上传成功，但数据库写入失败：
  - 立即同步删除刚上传的对象
- 如果删除对象也失败：
  - 记录错误日志
  - 生成待清理记录，不能静默吞掉

结论：

- 上传创建阶段采用**同步补偿优先**
- 因为这是单对象创建场景，立即补偿成本低，应该尽量强收敛

## 7.2 `from_staged` 导入一致性

目标：避免出现“文档导入失败，但暂存对象状态已变更”或“正式对象存在但数据库无文档记录”。

推荐流程：

1. 锁定 `kb_staged_file`
2. 校验状态必须是 `uploaded` 或可重试的 `failed`
3. 从 MinIO 读取暂存对象流
4. 写入正式文档对象到 `kb-documents`
5. 开启数据库事务：
   - 创建/更新 `kb_document`
   - 创建 `kb_chunk`
   - 更新 `kb_staged_file.status=consumed`
   - 记录正式对象引用
6. 写入 Milvus
7. 事务提交成功后，将暂存对象加入“待删除队列”

失败处理分两类：

### 场景 A：正式对象已上传，但数据库事务失败

处理：

- 立即同步删除本次新写入的正式对象
- `kb_staged_file` 状态不改为 `consumed`
- 保持可重试

### 场景 B：数据库提交成功，但删除暂存对象失败

处理：

- 业务上仍视为导入成功
- 暂存对象清理转入后台补偿队列
- 不能因为“清理动作失败”回滚已成功的文档导入

结论：

- **创建类对象优先同步补偿**
- **删除类对象采用异步可重试清理**

## 7.3 文档更新一致性

文档更新继续保持当前“整篇重建”语义：

1. 上传新的暂存对象
2. 调用 `kb_document_update_from_staged`
3. 读取新暂存对象
4. 新写正式对象
5. 新建 chunk、新建向量
6. 事务内更新文档元数据为新对象引用
7. 事务成功后，把旧正式对象和新暂存对象加入删除队列

失败处理：

- 若事务失败，同步删除新正式对象
- 旧正式对象保持不动
- 文档仍指向旧版本

## 7.4 文档删除一致性

文档删除时当前已经包含：

- PostgreSQL 删除/软删
- Milvus 删除
- 文件删除补偿

切换到 MinIO 后，文件删除建议改为：

1. 事务内软删文档与 chunk，删除 Milvus
2. 提交后生成“正式对象删除任务”
3. 后台异步删除 MinIO 对象

原因：

- 对象删除不应阻塞主业务事务提交
- 删除失败必须可追踪、可重试

---

## 8. 对象清理与孤儿文件治理设计

## 8.1 为什么必须单独设计清理机制

对象存储和数据库不是同一事务域。即使主链路设计正确，仍可能存在：

- 上传后数据库失败但对象未删成功
- 文档删除后对象清理失败
- 更新成功后旧对象清理失败
- 暂存文件过期但未及时清理

因此，系统必须内建**对象治理机制**，而不是依赖人工排查。

## 8.2 建议新增对象清理表

建议新增：

- `kb_storage_gc_task`

用途：

- 记录所有待执行的对象删除任务
- 提供统一的重试、补偿和故障排查入口

建议字段：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | `BIGSERIAL` | 是 | 主键 |
| `resource_type` | `VARCHAR(32)` | 是 | `staged_file` / `document` |
| `resource_id` | `BIGINT` | 是 | 对应业务记录 ID |
| `storage_backend` | `VARCHAR(32)` | 是 | 固定 `minio` |
| `bucket` | `VARCHAR(128)` | 是 | bucket |
| `object_key` | `VARCHAR(1024)` | 是 | 对象 key |
| `action` | `VARCHAR(32)` | 是 | 当前主要为 `delete` |
| `status` | `VARCHAR(32)` | 是 | `pending/running/success/failed` |
| `retry_count` | `INT` | 是 | 已重试次数 |
| `max_retry_count` | `INT` | 是 | 最大重试次数 |
| `last_error` | `TEXT` | 否 | 最近一次失败原因 |
| `next_retry_at` | `TIMESTAMP` | 否 | 下次重试时间 |
| `created_at` | `TIMESTAMP` | 是 | 创建时间 |
| `updated_at` | `TIMESTAMP` | 是 | 更新时间 |

## 8.3 清理策略

对象清理分三类：

### 1. 暂存文件过期清理

- 找出 `status=uploaded` 且 `expires_at < now()`
- 标记为 `expired`
- 生成 `kb_storage_gc_task`
- 清理成功后标记 `deleted`

### 2. 已消费暂存对象清理

- 导入成功后，旧暂存对象不再需要
- 进入 `kb_storage_gc_task`
- 清理成功后可保留 `kb_staged_file` 记录，仅状态更新，不必硬删除历史记录

### 3. 正式文档对象清理

- 文档删除或更新后，旧对象进入清理队列
- 清理失败可重试
- 数据库中对应文档已不可见，但不会丢失清理任务

## 8.4 孤儿文件巡检

建议提供周期性巡检任务：

- 从 `kb_staged_file`、`kb_document`、`kb_storage_gc_task` 汇总所有“应存在对象”
- 对比 MinIO bucket 实际对象
- 找出：
  - 数据库有记录但对象缺失
  - 对象存在但数据库无引用

该能力用于：

- 补偿失效排查
- 升级迁移校验
- 灾难恢复后的健康检查

---

## 9. MinIO 集成接口设计建议

## 9.1 存储抽象层

当前 `FileStorage` 应演进为统一抽象，例如：

- `ObjectStorage`

再提供具体实现：

- `LocalFileStorage`
- `MinioObjectStorage`

这样可以：

- 平滑迁移
- 保留本地开发 fallback 能力
- 便于测试时替换实现

## 9.2 推荐方法集合

建议统一抽象的方法：

- `save_staged_file_stream`
- `read_file_bytes`
- `open_file_stream`
- `copy_object`
- `delete_file`
- `stage_delete_file`
- `restore_staged_file`
- `finalize_staged_file_delete`

其中：

- 本地文件系统可以继续用“重命名到临时路径”的方式实现 `stage_delete_file`
- MinIO 版本不建议模拟重命名，应改成：
  - 记录删除计划
  - 提交后异步删除

也就是说：

- 当前接口名可以保留
- 但 MinIO 实现的语义需要从“本地 rename”切换为“延迟删除任务”

---

## 10. MinIO 配置设计建议

建议新增配置项：

| 配置项 | 说明 |
|---|---|
| `KNOWLEDGEBASE_OBJECT_STORAGE_PROVIDER` | `local` / `minio` |
| `KNOWLEDGEBASE_MINIO_ENDPOINT` | MinIO API 地址 |
| `KNOWLEDGEBASE_MINIO_ACCESS_KEY` | Access Key |
| `KNOWLEDGEBASE_MINIO_SECRET_KEY` | Secret Key |
| `KNOWLEDGEBASE_MINIO_SECURE` | 是否使用 HTTPS |
| `KNOWLEDGEBASE_MINIO_STAGED_BUCKET` | 暂存 bucket |
| `KNOWLEDGEBASE_MINIO_DOCUMENT_BUCKET` | 正式文档 bucket |
| `KNOWLEDGEBASE_MINIO_REGION` | region，默认可为空或 `us-east-1` |

说明：

- Milvus 现有 MinIO 配置不要直接复用为业务配置名
- 业务对象存储应有单独配置，避免职责混淆

---

## 11. 迁移策略建议

本次改造建议分阶段实施。

### 阶段一：新增 MinIO 存储能力

- 引入 `MinioObjectStorage`
- 新上传文件写 MinIO
- 旧本地文件继续可读

### 阶段二：数据库字段扩展

- 给 `kb_document` 增加结构化对象字段
- 给 `kb_staged_file` 增加对象字段
- 新写入全部按 MinIO 字段落库

### 阶段三：清理任务能力

- 新增 `kb_storage_gc_task`
- 接管更新/删除/过期清理中的对象删除

### 阶段四：历史文件迁移

- 扫描现有本地 `storage_uri`
- 上传到 MinIO
- 更新数据库对象字段
- 校验后再删除本地文件

迁移期间要求：

- 读路径兼容 `local` 和 `minio`
- 写路径统一收敛到 `minio`

---

## 12. 与现有接口的关系

本方案不要求立即重写 MCP 接口语义。

现有对外接口可保持不变：

- `POST /api/staged-files`
- `kb_document_import_from_staged`
- `kb_document_update_from_staged`
- `kb_document_import_batch_submit_from_staged`

变化点仅在服务内部：

- 上传落点从本地磁盘改为 MinIO
- `storage_uri` 从本地路径改为 `s3://...`
- 删除补偿从本地文件删除改为 MinIO 对象治理

这意味着：

- 上层 Agent 不需要理解 MinIO 细节
- 但系统内部需要具备完整的一致性机制

---

## 13. 最终建议

综合当前项目现状，建议明确采用以下方案：

1. 继续保留 PostgreSQL 作为业务元数据真相源。
2. 将业务原始文件从本地磁盘迁移到 MinIO。
3. MinIO 使用独立 bucket：
   - `kb-staged-files`
   - `kb-documents`
4. `kb_staged_file` 与 `kb_document` 同时保存：
   - `storage_uri`
   - `storage_backend`
   - `storage_bucket`
   - `storage_key`
5. 文件创建失败采用同步补偿。
6. 文件删除失败采用数据库可追踪的异步清理队列。
7. 不与 Milvus 复用同一业务 bucket。
8. 当前预留 `global` 命名空间，为未来多租户演进保留路径。

本方案的核心目标不是“把文件从磁盘搬到对象存储”这么简单，而是建立一套**可恢复、可追踪、可治理、可扩展**的文件对象生命周期管理机制。
