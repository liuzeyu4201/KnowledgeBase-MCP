# KnowledgeBase MCP Server

## 项目说明

本项目是一个面向知识库场景的 MCP Server，当前阶段已完成：

- PostgreSQL 主数据建模
- 分类新增与查询
- MCP Tool 基础结构
- Docker Compose 开发环境与生产环境封装

## 目录说明

- `knowledgebase/`：应用代码
- `sql/`：初始化 SQL 脚本
- `docs/`：设计文档
- `docker-compose.dev.yml`：开发环境编排
- `docker-compose.prod.yml`：生产环境编排
- `Dockerfile`：开发/生产通用镜像构建文件

## 环境变量

开发环境：

```bash
cp .env.dev.example .env.dev
```

生产环境：

```bash
cp .env.prod.example .env.prod
```

## 开发环境启动

```bash
docker compose -f docker-compose.dev.yml --env-file .env.dev up --build
```

启动后可访问：

- MCP HTTP 地址：`http://localhost:8000/mcp`
- PostgreSQL：`localhost:5432`
- MinIO API：`http://localhost:9000`
- MinIO Console：`http://localhost:9001`
- Milvus：`localhost:19530`
- Milvus Web UI：`http://localhost:9091/webui/`

## 生产环境启动

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up --build -d
```

## 停止环境

开发环境：

```bash
docker compose -f docker-compose.dev.yml --env-file .env.dev down
```

生产环境：

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod down
```

如需同时删除数据卷：

```bash
docker compose -f docker-compose.dev.yml --env-file .env.dev down -v
docker compose -f docker-compose.prod.yml --env-file .env.prod down -v
```

## 当前运行约定

- 应用容器默认使用 FastMCP HTTP 传输模式
- 数据库表会在应用启动时自动初始化
- PostgreSQL 为业务主库
- Milvus 为向量检索引擎

## 后续开发建议

- 接入文档导入能力
- 接入 Milvus 检索实现
- 增加 Alembic 迁移管理
- 增加测试与启动健康检查
