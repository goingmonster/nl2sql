# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 在此代码库中工作时提供指导。

## 架构概述

这是一个 NL2SQL（自然语言转 SQL）一体化应用，采用单体容器设计，包括：
- **后端**：FastAPI 应用（`/hyrw/`）使用 SQLAlchemy ORM
- **前端**：Vue 3 SPA（`/nlsql_front/nlsql-vue-app/`）使用 Element Plus UI
- **部署**：单个 Docker 容器，包含 Nginx 反向代理和 Supervisor 进程管理

该应用可将自然语言查询转换为 SQL，支持多种数据库类型（PostgreSQL、ClickHouse、MySQL、SQLite）。

## 常用命令

### 完整应用（Docker）
```bash
# 构建并运行完整应用
docker-compose up --build

# 应用运行在 http://localhost:8080
# 内部 API 运行在 8000 端口，通过 Nginx 代理
```

### 后端开发
```bash
# 进入后端目录
cd hyrw/

# 安装依赖
pip install -r requirements.txt

# 运行开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 运行测试
pytest
pytest tests/test_specific_file.py  # 运行单个测试文件
pytest -k "test_function_name"      # 运行特定测试
```

### 前端开发
```bash
# 进入前端目录
cd nlsql_front/nlsql-vue-app/

# 安装依赖
npm install

# 运行开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

## 核心后端组件

### API 结构（`/hyrw/app/api/v1/`）
API 按领域特定模块组织：
- `db-config/` - 数据库连接管理
- `llm-config/` - 语言模型配置
- `table-metadata/` - 表模式存储
- `user-prompt-config/` - 自定义提示模板
- `nlsql-task-config/` - NL2SQL 任务设置
- `table-level-prompt/` - 表级别提示
- `table-field-prompt/` - 字段级别提示
- `table-field-relation/` - 字段关系映射
- `qa-embedding/` - 用于训练的问答对
- `metadata/` - 自动模式发现
- `task-chat/` - 交互式 NL2SQL 接口

### 服务（`/hyrw/app/services/`）
核心业务逻辑实现：
- `openai_service.py` - OpenAI API 集成
- `create_sql_agent.py` - 自然语言转 SQL 转换引擎
- `metadata_extractor.py` - 自动模式发现
- PostgreSQL 和 ClickHouse 的数据库客户端

### 模型（`/hyrw/app/models/`）
数据持久化的 SQLAlchemy 模型，默认使用 SQLite 作为元数据数据库。

## 前端架构

使用 Vue 3 组合式 API 和 `<script setup>` 语法构建：
- 使用 Element Plus 作为 UI 组件库
- Vue Router 用于导航
- Axios 用于向后端 API 发送 HTTP 请求
- API 基础 URL：`/api/v1/`

## 数据库配置

应用支持多种用户查询数据库类型：
- SQLite（元数据默认）
- PostgreSQL
- ClickHouse
- MySQL（已配置但客户端需要添加到 requirements.txt）

数据库连接通过 `db-config` API 端点配置，并存储在 SQLite 元数据数据库中。

## 测试

- 后端测试使用 `pytest` 和 `pytest-asyncio` 支持异步
- 测试配置在 `pytest.ini` 中
- 测试文件位于 `/hyrw/tests/`
- 快速测试脚本：`hyrw/quick_test.py`

## 部署说明

- 单个容器同时运行 Nginx（80 端口）和 FastAPI（8000 端口）
- Supervisor 管理两个进程
- 前端静态文件由 Nginx 从 `/usr/share/nginx/html` 提供服务
- 日志写入 `/var/log/nlsql/`
- 容器暴露 80 端口，docker-compose 映射到 8080

## 开发工作流

1. 后端更改：修改 `/hyrw/` 中的文件并重启 uvicorn
2. 前端更改：修改 `/nlsql_front/nlsql-vue-app/` 中的文件，运行 `npm run build` 进行容器测试
3. 完整容器测试：使用 `docker-compose up --build`
4. 本地运行后端时，API 文档可在 `http://localhost:8000/docs` 访问

## 本地构建镜像
```
cd nlsql_front/nlsql-vue-app
npm run build

cd /Users/macbook/sthg/code/nlsql_for_docker
docker compose up -d --build
```