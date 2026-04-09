# AGENTS.md

## 项目声明

本项目旨在构建一个**面向知识库场景的 MCP Server**，供上层 Agent 通过标准化协议调用，实现对底层知识库与向量数据库的**增、删、改、查（CRUD）**操作。

项目核心目标如下：

1. **服务目标明确**
   提供一个可被 Agent 稳定调用的 MCP Server，使其能够围绕知识库数据完成写入、查询、更新、删除等能力，并支持后续扩展检索增强、权限控制、审计追踪、任务编排等功能。

2. **技术栈统一**

   * 编程语言：Python
   * 包管理与运行环境：uv
   * 向量数据库：Milvus
   * 协议定位：MCP Server

3. **工程要求**
   本项目必须以**可扩展、稳定、生产级、模块化**为基本建设原则，避免一次性脚本式开发。所有实现应优先满足以下要求：

   * 清晰的分层架构
   * 明确的模块边界
   * 可维护的目录结构
   * 可测试的核心逻辑
   * 可观测的运行状态
   * 可配置的部署方式
   * 可演进的接口设计

4. **使用场景**
   上层 Agent 通过调用 MCP Server，执行知识库相关操作，例如：

   * 新增知识条目
   * 删除知识条目
   * 更新知识内容与元数据
   * 查询知识条目
   * 基于向量索引进行检索
   * 结合结构化条件进行过滤查询

5. **设计原则**
   在后续所有需求拆解、提示词编写、文档设计与代码生成中，默认遵循以下原则：

   * **中文优先**：所有提示词、文档、说明、注释、接口描述均使用中文
   * **生产导向**：默认按生产级项目标准进行设计，而非教学示例或最小可运行 Demo
   * **模块化优先**：各功能应解耦设计，便于替换存储层、扩展工具集与接入更多 Agent
   * **稳定性优先**：重点考虑异常处理、边界校验、日志记录、配置管理与兼容性
   * **扩展性优先**：为未来增加权限系统、检索策略、多数据源接入、多租户支持预留空间

6. **后续协作约定**
   在本对话中，所有后续需求将默认基于上述项目背景展开。对于用户输入中可能存在的口语化、简写、目标不清、边界模糊等情况，应优先进行以下处理：

   * 识别真实目标
   * 补全缺失约束
   * 将模糊描述重写为更精确的工程需求
   * 输出适合直接用于开发、设计或提示词驱动的规范化内容

---
## 一句话定义

这是一个基于 **Python + uv + Milvus** 构建的、供 **Agent 调用的知识库 MCP Server** 项目，目标是以**生产级、模块化、可扩展、稳定**的方式，提供面向知识库数据的标准化管理与检索能力。

---

## 当前进度记录

以下内容作为当前项目的长期记忆，后续协作默认以此为准。

### 1. 当前分支约定

* `dev`：主开发分支，当前功能修复与集成结果以该分支为准
* `test`：测试分支，用于集中补测试、压测和失败场景验证

### 2. 当前已实现能力

#### 分类接口

* `kb_category_create`
* `kb_category_get`
* `kb_category_list`
* `kb_category_update`
* `kb_category_delete`

#### 文档接口

* `kb_document_import_from_staged`
* `kb_document_get`
* `kb_document_list`
* `kb_document_update_from_staged`
* `kb_document_delete`

#### 暂存文件接口

* `kb_staged_file_get`
* `kb_staged_file_list`
* `kb_staged_file_delete`

#### 批量导入任务接口

* `kb_document_import_batch_submit_from_staged`
* `kb_document_import_batch_cancel`
* `kb_document_import_batch_get`

#### 检索接口

* `kb_search_retrieve`

### 3. 当前存储与检索实现状态

* 业务主库使用 PostgreSQL
* 向量检索使用 Milvus
* 原始 PDF 使用本地文件存储
* Milvus 当前采用：
  * 稠密向量：Embedding 模型生成
  * 词法检索：Milvus BM25
  * `content` 字段开启 analyzer
* 当前 analyzer 已切到中英文自动识别：
  * 英文走 `standard + lowercase`
  * 中文走 `jieba + removepunct`

### 4. 当前工程关键约定

* 文档检索粒度是 `chunk`，不是整篇文档
* 远端标准导入路径是：先上传暂存文件，再通过 `*_from_staged` 接口导入
* PDF 更新采用整篇重建，不做局部增量更新
* 删除、更新、导入都要求跨 PostgreSQL / Milvus / 文件存储的一致性补偿
* Milvus 不是业务主库，检索结果必须回查 PostgreSQL 后再返回

### 5. 当前已修复的重要问题

* 修复了参数校验失败时部分接口被 MCP 包成非标准错误的问题
* 修复了 PDF 文本中含 `NUL (0x00)` 字节导致 PostgreSQL 插入失败的问题
* 修复了英文问句和中英术语检索时排序质量偏差的问题
* 当前全量测试结果为 `124/124` 通过

### 6. 当前测试资产

* 测试目录：`test/`
* 测试报告输出位置：`docs/测试文档-time.md`
* 测试覆盖包括：
  * 契约测试
  * 边界测试
  * 失败测试
  * 并发测试
  * 压力测试

---

## 常用命令

以下命令是当前项目里最常用的一组操作，后续协作优先复用。

### 1. 基础环境

```bash
uv sync
```

```bash
PYTHONPYCACHEPREFIX=/tmp/knowledgebase-pyc python3 -m compileall knowledgebase test main.py
```

### 2. Docker 开发环境

启动开发环境：

```bash
docker compose -f docker-compose.dev.yml --env-file .env.dev up --build -d
```

仅重启应用容器：

```bash
docker compose -f docker-compose.dev.yml --env-file .env.dev restart app
```

查看容器状态：

```bash
docker compose -f docker-compose.dev.yml --env-file .env.dev ps
```

查看应用日志：

```bash
docker compose -f docker-compose.dev.yml --env-file .env.dev logs --tail 200 app
```

停止开发环境：

```bash
docker compose -f docker-compose.dev.yml --env-file .env.dev down
```

### 3. 进入容器执行命令

```bash
docker exec knowledgebase-app-dev sh -lc 'cd /app && /opt/venv/bin/python -m test.run_suite'
```

```bash
docker exec knowledgebase-app-dev sh -lc 'cd /app && /opt/venv/bin/python -m unittest -v test.test_search_contract'
```

```bash
docker exec knowledgebase-app-dev sh -lc 'curl -i http://127.0.0.1:8000/mcp'
```

### 4. Git 操作

查看分支和工作区：

```bash
git status --short --branch
```

查看最近提交：

```bash
git log --oneline --decorate -8
```

切换分支：

```bash
git switch dev
git switch test
```

把 `test` 合并到 `dev`：

```bash
git switch dev
git merge --no-ff test
```

### 5. 当前最常用的测试入口

全量测试：

```bash
docker exec knowledgebase-app-dev sh -lc 'cd /app && /opt/venv/bin/python -m test.run_suite'
```

运行后检查报告：

```bash
sed -n '1,120p' docs/测试文档-time.md
```
