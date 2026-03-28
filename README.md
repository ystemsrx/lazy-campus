<div align="right">
  <strong>English</strong> | <a href="./README.zh.md">简体中文</a>
</div>

<div align="center">
  <h1>LaZy Campus</h1>
  <p>Campus task matching platform with risk control, real-time chat, and AI agent execution.</p>

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

## Features

<table>
<tr>
<td width="50%">

**Task Marketplace**
- Publish, browse, and accept campus tasks
- Category-based organization with price and deadline
- Publisher/worker rating system

</td>
<td width="50%">

**Real-time Chat**
- Built-in messaging between task participants
- File sharing support
- Unread message notifications

</td>
</tr>
<tr>
<td>

**Moderation & Risk Control**
- Admin review panel for content moderation
- User reports and banning system
- Newcomer rewards management

</td>
<td>

**AI Agent (Optional)**
- Docker-isolated execution environment
- Code generation, document writing, data analysis
- Gateway-forwarded Kimi API integration

</td>
</tr>
</table>

## Tech Stack

| Layer | Technologies |
|:------|:-------------|
| **Frontend** | Vue 3, TypeScript, Vite, Pinia, Vue Router, Three.js |
| **Backend** | FastAPI, SQLAlchemy, Pydantic, JWT auth, SQLite |
| **AI Agent** | Docker containers, Kimi upstream, optional Redis queue |
| **Storage** | SQLite DB, `backend/uploads/`, `backend/agent_sessions/` |

## Quick Start

### Option A &mdash; Deploy with `manage.sh`

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

./manage.sh start
```

The script automatically creates a Python venv, installs dependencies, builds the frontend, and starts FastAPI on `127.0.0.1:8000`.

<details>
<summary><b>More commands</b></summary>

```bash
./manage.sh status    # Check service status
./manage.sh stop      # Stop all services
./manage.sh restart   # Restart all services
./manage.sh nginx     # Generate Nginx config for API + static site
```

</details>

### Option B &mdash; Local Development

**1. Copy env files**

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

**2. Start mock auth service** (optional)

```bash
cd backend
uv venv .venv && source .venv/bin/activate
uv pip install -r requirements.txt
uvicorn scripts.mock_auth_service:app --reload --port 9000
```

**3. Start backend**

```bash
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**4. Start frontend**

```bash
cd frontend && npm install && npm run dev
```

> [!TIP]
> Tables are auto-created on backend startup. Migration logic lives in `backend/app/db/init_db.py`.

| Service | URL |
|:--------|:----|
| Frontend | `http://localhost:5173` |
| API Docs | `http://127.0.0.1:8000/docs` |

## Configuration

| File | Purpose | Key Fields |
|:-----|:--------|:-----------|
| `.env` | Deployment script | `API_DOMAIN`, `LINK_DOMAIN` |
| `backend/.env` | Backend runtime & auth | `DATABASE_URL`, `SECRET_KEY`, `ADMIN_ACCOUNT`, `ADMIN_PASSWORD`, `THIRD_PARTY_AUTH_URL` |
| `frontend/.env` | Frontend config | `VITE_APP_TITLE`, `VITE_API_BASE_URL_DEV`, `VITE_API_BASE_URL_PROD` |

## Authentication

- **Admin** &mdash; local account configured via `backend/.env`
- **Users** &mdash; local registration (when enabled) or third-party auth fallback
- First-time users must complete email and gender before entering the system

## AI Agent

> [!WARNING]
> The AI agent requires **Docker** on the host and a valid **Kimi API key** in `backend/.env`. It is not enabled by frontend/backend env vars alone.

- Only task categories with `ai_agent_enabled` can start agent sessions
- Users need remaining `agent_usage_remaining` quota
- Limits: **8 rounds** per session, **5 files** per message, **50 MB** per file
- `REDIS_URL` is optional &mdash; enables shared agent queue status

## Project Structure

```
.
├── manage.sh                # Build, start, stop, nginx config
├── frontend/                # Vue 3 + TypeScript SPA
├── backend/
│   ├── app/                 # FastAPI app, models, APIs, services
│   ├── agent/               # Docker image, runtime config, skills
│   ├── scripts/             # Helpers (mock auth service, etc.)
│   └── .env.example
└── .env.example
```

## License

[Apache License 2.0](./LICENSE)
