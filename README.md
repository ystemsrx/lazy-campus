<div align="right">
  <strong>English</strong> | <a href="./README.zh.md">简体中文</a>
</div>

# LaZy Campus

<p align="center">
  <strong>A campus-oriented task matching platform with built-in risk control review, real-time chat, and optional AI agent execution capabilities.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Vue-3-42b883?logo=vue.js&logoColor=white" alt="Vue 3" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/TypeScript-5-3178c6?logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/SQLite-default-003b57?logo=sqlite&logoColor=white" alt="SQLite" />
  <img src="https://img.shields.io/badge/AI%20Agent-Docker%20%2B%20Kimi-111827" alt="AI Agent" />
</p>

## Authentication and Account Model

- Administrator accounts are local accounts configured through `backend/.env`.
- Regular users can register locally when registration is enabled.
- User login also supports fallback through third-party authentication. After a successful third-party login, user information is synchronized to the local database.
- Before entering the system for the first time, regular users must complete their email address and gender information.

## Tech Stack

- Frontend: Vue 3, TypeScript, Vite, Pinia, Vue Router, Three.js.
- Backend: FastAPI, SQLAlchemy, Pydantic Settings, JWT authentication, with SQLite as the default database.
- AI agent: Docker session containers managed by the backend, optional Redis queueing, and gateway access to Kimi upstream services.
- Storage: local SQLite database, regular uploaded files in `backend/uploads/`, and agent task workspaces in `backend/agent_sessions/`.

## Quick Start

### Option A: Deployment-style startup with `manage.sh`

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

./manage.sh start
```

This script is closer to a Linux server deployment workflow and will automatically:

- Create a backend virtual environment and install `backend/requirements.txt`
- Install frontend dependencies and build `frontend/dist`
- Start FastAPI on `127.0.0.1:8000`
- Keep the frontend as static assets for Nginx to serve

Common commands:

```bash
./manage.sh status
./manage.sh stop
./manage.sh restart
./manage.sh nginx
```

Among them, `./manage.sh nginx` generates an HTTP Nginx configuration for the API domain and the frontend static site.

### Option B: Local separated development

1. Copy the environment variable files:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

2. Start the local mock third-party authentication service:

```bash
cd backend
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
uvicorn scripts.mock_auth_service:app --reload --port 9000
```

3. Start the backend in another terminal:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

4. Start the frontend in another terminal:

```bash
cd frontend
npm install
npm run dev
```

After startup, you can access:

- Frontend: `http://localhost:5173`
- Backend docs: `http://127.0.0.1:8000/docs`

> [!TIP]
> On backend startup, tables are created automatically and the lightweight migration logic in `backend/app/db/init_db.py` is executed.

## Configuration Files

| File            | Purpose                                                                        | Key fields                                                                              |
| --------------- | ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------- |
| `.env`          | Root-level deployment script configuration                                     | `API_DOMAIN`, `LINK_DOMAIN`                                                             |
| `backend/.env`  | Backend runtime, authentication, database, agent, and public URL configuration | `DATABASE_URL`, `THIRD_PARTY_AUTH_URL`, `ADMIN_ACCOUNT`, `ADMIN_PASSWORD`, `SECRET_KEY` |
| `frontend/.env` | Frontend title and API endpoint configuration                                  | `VITE_APP_TITLE`, `VITE_API_BASE_URL_DEV`, `VITE_API_BASE_URL_PROD`, `VITE_APP_LOGO`    |

## AI Agent Notes

> [!WARNING]
> The AI agent is not a feature that works by configuring only frontend and backend environment variables. It also requires Docker on the host machine and a valid Kimi upstream key configured in `backend/.env`.

- Only tasks under categories with `ai_agent_enabled` can start agent sessions.
- Users must have remaining `agent_usage_remaining` quota to start an agent.
- The current backend limits are: at most 8 interaction rounds per session, up to 5 files per message, and a maximum file size of 50 MB per file.
- `REDIS_URL` is optional. If configured, it is used to share agent queue status.

## Directory Structure

```text
.
├── manage.sh                     # One-click build, start, stop, and nginx config generation
├── frontend/                     # Vue 3 frontend
├── backend/
│   ├── app/                      # FastAPI app, models, APIs, and services
│   ├── agent/                    # Agent images, runtime configuration, and workspace templates
│   ├── scripts/                  # Helper scripts, such as the mock authentication service
│   └── .env.example              # Example backend environment variables
└── .env.example                  # Example root deployment environment variables
```

## License

Apache License 2.0. See [LICENSE](./LICENSE) for details.
