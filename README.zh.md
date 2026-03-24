<div align="right">
  <a href="./README.md">English</a> | <strong>简体中文</strong>
</div>

# LaZy Campus

<p align="center">
  <strong>一个面向校园场景的任务撮合平台，内置风控审核、即时聊天，以及可选的 AI 代理执行能力。</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Vue-3-42b883?logo=vue.js&logoColor=white" alt="Vue 3" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/TypeScript-5-3178c6?logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/SQLite-default-003b57?logo=sqlite&logoColor=white" alt="SQLite" />
  <img src="https://img.shields.io/badge/AI%20Agent-Docker%20%2B%20Kimi-111827" alt="AI Agent" />
</p>

## 认证与账号模型

- 管理员账号是本地账号，通过 `backend/.env` 配置。
- 普通用户在开启注册时可直接本地注册。
- 用户登录同时支持第三方认证回退；第三方登录成功后，会把用户信息同步到本地数据库。
- 普通用户首次进入系统前，需要补全邮箱和性别信息。

## 技术栈

- 前端：Vue 3、TypeScript、Vite、Pinia、Vue Router、Three.js。
- 后端：FastAPI、SQLAlchemy、Pydantic Settings、JWT 鉴权，默认使用 SQLite。
- AI 代理：由后端管理 Docker 会话容器，可选 Redis 队列，并通过网关接入 Kimi 上游。
- 存储：本地 SQLite 数据库，普通上传文件在 `backend/uploads/`，代理任务工作区在 `backend/agent_sessions/`。

## 快速开始

### 方案 A：使用 `manage.sh` 进行部署式启动

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

./manage.sh start
```

这个脚本更偏向 Linux 服务器部署流程，会自动：

- 创建后端虚拟环境并安装 `backend/requirements.txt`
- 安装前端依赖并构建 `frontend/dist`
- 将 FastAPI 启动在 `127.0.0.1:8000`
- 保留前端为静态产物，交给 Nginx 托管

常用命令：

```bash
./manage.sh status
./manage.sh stop
./manage.sh restart
./manage.sh nginx
```

其中 `./manage.sh nginx` 会生成 API 域名和前端静态站点的 HTTP Nginx 配置。

### 方案 B：本地分离开发

1. 复制环境变量文件：

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

2. 启动本地模拟第三方认证服务：

```bash
cd backend
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
uvicorn scripts.mock_auth_service:app --reload --port 9000
```

3. 在另一个终端启动后端：

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

4. 在另一个终端启动前端：

```bash
cd frontend
npm install
npm run dev
```

启动后可访问：

- 前端：`http://localhost:5173`
- 后端文档：`http://127.0.0.1:8000/docs`

> [!TIP]
> 后端启动时会自动建表，并执行 `backend/app/db/init_db.py` 中的轻量迁移逻辑。

## 配置文件说明

| 文件            | 用途                                       | 关键字段                                                                                |
| --------------- | ------------------------------------------ | --------------------------------------------------------------------------------------- |
| `.env`          | 根目录部署脚本配置                         | `API_DOMAIN`、`LINK_DOMAIN`                                                             |
| `backend/.env`  | 后端运行、鉴权、数据库、代理、公网地址配置 | `DATABASE_URL`、`THIRD_PARTY_AUTH_URL`、`ADMIN_ACCOUNT`、`ADMIN_PASSWORD`、`SECRET_KEY` |
| `frontend/.env` | 前端标题与 API 地址配置                    | `VITE_APP_TITLE`、`VITE_API_BASE_URL_DEV`、`VITE_API_BASE_URL_PROD`、`VITE_APP_LOGO`    |

## AI 代理说明

> [!WARNING]
> AI 代理不是只配前后端环境变量就能运行的功能。它还要求宿主机提供 Docker，并在 `backend/.env` 中配置可用的 Kimi 上游密钥。

- 只有分类开启了 `ai_agent_enabled`，该分类下的任务才能发起代理会话。
- 用户需要有剩余 `agent_usage_remaining` 次数，才能启动代理。
- 当前后端限制为：单会话最多 8 轮交互、单次消息最多 5 个文件、单文件最大 50 MB。
- `REDIS_URL` 不是必填；配置后会用于共享代理排队状态。

## 目录结构

```text
.
├── manage.sh                     # 一键构建、启动、停止、生成 nginx 配置
├── frontend/                     # Vue 3 前端
├── backend/
│   ├── app/                      # FastAPI 应用、模型、接口、服务
│   ├── agent/                    # 代理镜像与运行时配置、工作区模板
│   ├── scripts/                  # 辅助脚本，如模拟认证服务
│   └── .env.example              # 后端环境变量示例
└── .env.example                  # 根目录部署环境变量示例
```

## License

Apache License 2.0。详见 [LICENSE](./LICENSE)。
