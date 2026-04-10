# KnowledgeBase MCP Server

面向知识库场景的 MCP Server。当前实现基于 `Python + uv + PostgreSQL + Milvus`，用于给上层 Agent 提供稳定的知识库管理与检索能力。

许可证：`Apache-2.0`，见 [LICENSE](LICENSE)。

## 项目定位


当前实现目标：

- 提供可被 Agent 调用的 MCP Tool
- 提供远端可用的大文件上传与导入链路
- 用 PostgreSQL 维护业务主数据
- 用 Milvus 提供语义检索、BM25 检索和混合检索
- 支持同步文档操作和异步批量导入任务

---

## 当前能力

### 分类能力

- `kb_category_create`
- `kb_category_get`
- `kb_category_list`
- `kb_category_update`
- `kb_category_delete`

### 文档能力

- `kb_document_get`
- `kb_document_list`
- `kb_document_import_from_staged`
- `kb_document_update_from_staged`
- `kb_document_delete`

### 暂存文件能力

- `POST /api/staged-files`
- `GET /api/staged-files/{staged_file_id}`
- `GET /api/staged-files`
- `DELETE /api/staged-files/{staged_file_id}`
- `kb_staged_file_get`
- `kb_staged_file_list`
- `kb_staged_file_delete`

### 批量异步任务能力

- `kb_document_import_batch_submit_from_staged`
- `kb_document_import_batch_get`
- `kb_document_import_batch_cancel`

### 检索能力

- `kb_search_retrieve`

当前支持文档类型：

- `application/pdf`
- `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- `text/markdown`

### 可视化网页能力

- `GET /` 或 `GET /ui`：知识库分类首页
- `GET /ui/categories/{category_id}`：分类文档列表页
- `GET /api/visualization/categories`
- `GET /api/visualization/categories/{category_id}/documents`
- `GET /api/visualization/import-tasks/{task_id}`
- `GET /ws/import-tasks/{task_id}`

---

## 标准导入流程

远端部署下，标准流程不是把文件内容直接塞进 MCP Tool，而是两段式：

1. 通过 HTTP 上传接口把文件上传到暂存区
2. 通过 `*_from_staged` 的 MCP Tool 完成导入或更新

### 单文档导入

1. `kb_category_get` 或 `kb_category_list` 找到目标分类
2. 若分类不存在，调用 `kb_category_create`
3. `POST /api/staged-files` 上传文件
4. 调用 `kb_document_import_from_staged`
5. 调用 `kb_document_get` 或 `kb_document_list` 验证导入结果
6. 调用 `kb_search_retrieve` 做召回验证

### 文档更新

1. 先上传新文件到 `/api/staged-files`
2. 调用 `kb_document_update_from_staged`
3. 系统执行整篇重建

### 批量异步导入

1. 逐个上传文件到 `/api/staged-files`
2. 收集多个 `staged_file_id`
3. 调用 `kb_document_import_batch_submit_from_staged`
4. 轮询 `kb_document_import_batch_get`
5. 必要时调用 `kb_document_import_batch_cancel`

---

## 已移除的旧接口

以下旧接口已移除，不应再调用：

- `kb_document_import`
- `kb_document_update`
- `kb_document_import_batch_submit`

原因：

- 旧接口依赖 MCP 参数承载大文件内容
- 远端部署下不适合大文件传输
- 当前标准方案已统一为 `staged_file + *_from_staged`

---

## 架构说明

### 业务主库

- PostgreSQL

负责：

- 分类
- 文档
- 切片
- 暂存文件
- 批量导入任务

### 向量检索

- Milvus

负责：

- 稠密向量检索
- BM25 词法检索
- 混合检索

### 文件存储

当前开发环境默认走本地存储目录，远端标准协议通过 HTTP 上传接口创建暂存文件。

### 检索策略

- 稠密向量：Embedding 模型
- 词法检索：Milvus BM25
- `content` 字段启用 analyzer
- 当前 analyzer 为中英文自动识别：
  - 英文：`standard + lowercase`
  - 中文：`jieba + removepunct`

### 检索粒度

- `chunk`

不是整篇文档。

---

## 目录结构

```text
knowledgebase/
  app/            配置与应用初始化
  db/             数据库会话与建表入口
  domain/         领域异常与常量
  http/           普通 HTTP 接口
  integrations/   外部集成（解析、切分、Milvus、存储、Embedding）
  mcp/            MCP Server 与 Tool 注册
  models/         ORM 模型
  repositories/   仓储层
  schemas/        Pydantic 输入输出模型
  services/       业务服务层
  worker/         后台任务 worker

docs/             设计文档与测试报告
sql/              初始化 SQL
test/             测试
skills/           供其他 Agent 使用的技能文档
```

---

## 环境准备

开发环境：

```bash
cp .env.dev.example .env.dev
```

生产环境：

```bash
cp .env.prod.example .env.prod
```

本地依赖同步：

```bash
uv sync
```

语法检查：

```bash
PYTHONPYCACHEPREFIX=/tmp/knowledgebase-pyc python3 -m compileall knowledgebase test main.py
```

---

## Docker 开发环境

启动：

```bash
docker compose -f docker-compose.dev.yml --env-file .env.dev up --build -d
```

网页入口：

```bash
http://127.0.0.1:${NGINX_PORT:-8080}/ui
```

查看状态：

```bash
docker compose -f docker-compose.dev.yml --env-file .env.dev ps
```

查看应用日志：

```bash
docker compose -f docker-compose.dev.yml --env-file .env.dev logs --tail 200 app
```

查看 worker 日志：

```bash
docker compose -f docker-compose.dev.yml --env-file .env.dev logs --tail 200 worker
```

查看 nginx 日志：

```bash
docker compose -f docker-compose.dev.yml --env-file .env.dev logs --tail 200 nginx
```

停止：

```bash
docker compose -f docker-compose.dev.yml --env-file .env.dev down
```

---

## Docker 生产环境

启动：

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up --build -d
```

停止：

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod down
```

---

## 启动后的主要地址

- MCP HTTP: `http://127.0.0.1:8000/mcp`
- 文件上传 HTTP: `http://127.0.0.1:8000/api/staged-files`
- PostgreSQL: `127.0.0.1:5432`
- Milvus: `127.0.0.1:19530`
- MinIO API: `http://127.0.0.1:9000`
- MinIO Console: `http://127.0.0.1:9001`

---

## Claude Code 连接 MCP

项目本地运行后，可以把 Claude Code 接到当前 MCP Server：

```bash
claude mcp add --transport http --scope project knowledgebase http://127.0.0.1:8000/mcp
```

检查：

```bash
claude mcp list
claude mcp get knowledgebase
```

---

## 文件上传示例

```bash
curl -X POST http://127.0.0.1:8000/api/staged-files \
  -F "file=@/path/to/example.pdf;type=application/pdf"
```

成功后返回：

- `data.staged_file.id`
- `data.staged_file.staged_file_uid`
- `data.staged_file.status`

随后再调用：

- `kb_document_import_from_staged`

---

## 检索示例

`kb_search_retrieve` 的 `alpha` 语义：

- `0.0`：纯语义检索
- `1.0`：纯 BM25 检索
- 中间值：混合检索

经验建议：

- 英文定理名、术语名：优先 `alpha=1.0`
- 自然语言问法：优先 `alpha=0.0 ~ 0.5`
- 已知分类或文档范围时，尽量带上 `category_id` 或 `document_id`

---

## 测试

全量测试：

```bash
docker exec knowledgebase-app-dev sh -lc 'cd /app && /opt/venv/bin/python -m test.run_suite'
```

查看最新测试报告：

```bash
sed -n '1,120p' docs/测试文档-time.md
```

当前最新结果应以测试报告为准。

---

## 重要文档

- [数据库设计方案.md](docs/数据库设计方案.md)
- [MCP接口设计方案.md](docs/MCP接口设计方案.md)
- [测试文档-time.md](docs/测试文档-time.md)
- [AGENTS.md](AGENTS.md)
- [SKILL.md](skills/knowledgebase-mcp/SKILL.md)

---

## 当前工程约定

1. PostgreSQL 是业务真相源，Milvus 不是主库。
2. 文档更新采用整篇重建。
3. 检索结果必须经 PostgreSQL 回查后返回。
4. 跨 PostgreSQL / Milvus / 文件存储操作需要补偿与一致性控制。
5. 远端标准导入路径统一使用 `staged_file + *_from_staged`。
