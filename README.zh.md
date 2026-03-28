<div align="right">
  <a href="./README.md">English</a> | <strong>简体中文</strong>
</div>

<div align="center">
  <h1>LaZy Campus</h1>
  <p>面向校园场景的任务撮合平台，内置风控审核、即时聊天与 AI 代理执行能力。</p>

  <p>
    <img src="https://img.shields.io/badge/Vue-3-42b883?logo=vue.js&logoColor=white" alt="Vue 3" />
    <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
    <img src="https://img.shields.io/badge/TypeScript-5-3178c6?logo=typescript&logoColor=white" alt="TypeScript" />
    <img src="https://img.shields.io/badge/SQLite-default-003b57?logo=sqlite&logoColor=white" alt="SQLite" />
    <img src="https://img.shields.io/badge/AI%20Agent-Docker%20%2B%20Kimi-111827" alt="AI Agent" />
    <img src="https://img.shields.io/badge/License-Apache%202.0-blue" alt="License" />
  </p>
</div>

<br/>

## 功能特性

<table>
<tr>
<td width="50%">

**任务市场**
- 发布、浏览、接取校园任务
- 按分类组织，支持价格与截止日期
- 发布者/接单者互评体系

</td>
<td width="50%">

**即时聊天**
- 任务参与者内置消息通道
- 文件共享支持
- 未读消息提醒

</td>
</tr>
<tr>
<td>

**审核与风控**
- 管理员内容审核面板
- 用户举报与封禁系统
- 新人奖励管理

</td>
<td>

**AI 代理（可选）**
- Docker 隔离执行环境
- 代码生成、文档撰写、数据分析
- 网关转发接入 Kimi API

</td>
</tr>
</table>

## 技术栈

| 层级 | 技术 |
|:-----|:-----|
| **前端** | Vue 3、TypeScript、Vite、Pinia、Vue Router、Three.js |
| **后端** | FastAPI、SQLAlchemy、Pydantic、JWT 鉴权、SQLite |
| **AI 代理** | Docker 会话容器、Kimi 上游、可选 Redis 队列 |
| **存储** | SQLite 数据库、`backend/uploads/`、`backend/agent_sessions/` |

## 快速开始

### 方案 A &mdash; 使用 `manage.sh` 部署

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

./manage.sh start
```

脚本会自动创建 Python 虚拟环境、安装依赖、构建前端，并在 `127.0.0.1:8000` 启动 FastAPI。

<details>
<summary><b>更多命令</b></summary>

```bash
./manage.sh status    # 查看服务状态
./manage.sh stop      # 停止所有服务
./manage.sh restart   # 重启所有服务
./manage.sh nginx     # 生成 API + 静态站点的 Nginx 配置
```

</details>

### 方案 B &mdash; 本地分离开发

**1. 复制环境变量文件**

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

**2. 启动模拟认证服务**（可选）

```bash
cd backend
uv venv .venv && source .venv/bin/activate
uv pip install -r requirements.txt
uvicorn scripts.mock_auth_service:app --reload --port 9000
```

**3. 启动后端**

```bash
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**4. 启动前端**

```bash
cd frontend && npm install && npm run dev
```

> [!TIP]
> 后端启动时会自动建表，迁移逻辑位于 `backend/app/db/init_db.py`。

| 服务 | 地址 |
|:-----|:-----|
| 前端 | `http://localhost:5173` |
| API 文档 | `http://127.0.0.1:8000/docs` |

## 配置说明

| 文件 | 用途 | 关键字段 |
|:-----|:-----|:---------|
| `.env` | 部署脚本配置 | `API_DOMAIN`、`LINK_DOMAIN` |
| `backend/.env` | 后端运行与鉴权 | `DATABASE_URL`、`SECRET_KEY`、`ADMIN_ACCOUNT`、`ADMIN_PASSWORD`、`THIRD_PARTY_AUTH_URL` |
| `frontend/.env` | 前端配置 | `VITE_APP_TITLE`、`VITE_API_BASE_URL_DEV`、`VITE_API_BASE_URL_PROD` |

## 认证模型

- **管理员** &mdash; 本地账号，通过 `backend/.env` 配置
- **普通用户** &mdash; 本地注册（开启时）或第三方认证回退
- 首次进入系统需补全邮箱和性别信息

## AI 代理

> [!WARNING]
> AI 代理需要宿主机安装 **Docker** 并在 `backend/.env` 中配置有效的 **Kimi API 密钥**，仅配置前后端环境变量无法启用。

- 仅开启 `ai_agent_enabled` 的分类下的任务可发起代理会话
- 用户需有剩余 `agent_usage_remaining` 额度
- 限制：单会话 **8 轮**交互、单次 **5 个**文件、单文件 **50 MB**
- `REDIS_URL` 为可选项 &mdash; 用于共享代理排队状态

## 目录结构

```
.
├── manage.sh                # 构建、启动、停止、生成 Nginx 配置
├── frontend/                # Vue 3 + TypeScript 单页应用
├── backend/
│   ├── app/                 # FastAPI 应用、模型、接口、服务
│   ├── agent/               # Docker 镜像、运行时配置、技能模板
│   ├── scripts/             # 辅助脚本（模拟认证服务等）
│   └── .env.example
└── .env.example
```

## License

[Apache License 2.0](./LICENSE)
