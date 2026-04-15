# KnowledgeBase

这个项目提供一套可直接给 Agent 调用的知识库，主要功能：
- 管理知识库分类与文档
- 将文件导入为可检索内容
- 通过向量检索与关键词检索返回结果

当前项目同时提供：

- MCP 交互入口
- 文件上传入口
- 可视化网页界面
- 项目内置的知识库使用 Skill

许可证：`Apache-2.0`，见 [LICENSE](LICENSE)。

## 1. 项目简介

KnowledgeBase 适合这样的使用方式：

- 让 Claude Code 或其他 Agent 通过 MCP 直接操作知识库
- 先上传文件，再通过 MCP 导入到知识库
- 在网页中查看分类、文档、导入任务和内容

当前主要能力包括：

- 分类管理：创建、查询、更新、删除分类
- 文档管理：导入、查询、更新、删除文档
- 暂存文件：上传文件后再导入
- 批量导入：批量提交、查询、取消任务
- 检索能力：向量检索、BM25 检索、混合检索
- 可视化界面：通过浏览器查看知识库内容

## 2. 安装

这一节只关注实际使用需要的命令：配置 API、启动服务、配置 MCP、查看 Skill。



### 2.1 配置 API
配置 embedding模型（默认使用ollama）
已支持嵌入模型提供商：
- ollama
- ailiyun
统一使用 `dev` 配置：

```bash
cp env/.env.dev.example env/.env.dev
```

### 2.3 启动服务

启动服务：

```bash
docker compose -f docker/docker-compose.dev.yml --env-file env/.env.dev up --build -d
```


### 2.4 MCP 配置

项目提供了一个 MCP 配置示例文件：

- [env/.mcp.json](env/.mcp.json)


如果你使用 Claude Code，也可以直接用命令注册当前项目提供的 MCP 交互入口：

```bash
claude mcp add --transport http --scope project knowledgebase http://127.0.0.1:8000/mcp
```

检查是否注册成功：

```bash
claude mcp list
claude mcp get knowledgebase
```

### 2.5 Skills 配置

项目已经内置知识库使用 Skill：

- [skills/knowledgebase-mcp/SKILL.md](skills/knowledgebase-mcp/SKILL.md)

根据运行时环境配置skills

## 3. 使用

### 3.1 通过 Claude Code 使用

推荐流程：

1. 先启动知识库服务
2. 把 MCP 交互入口挂到 Claude Code
3. 在 Claude Code 中直接用自然语言调用知识库能力

然后你可以在 Claude Code 里直接描述任务，例如：

- 创建一个分类“投资研究”
- 上传并导入一份 PDF 到指定分类
- 查询某个分类下的全部文档
- 检索“中美利差”相关内容


### 3.2 查看可视化界面

服务启动后，直接访问：

```text
http://127.0.0.1:8080/ui
```

