# 🤖 AI Task Tracker — Backend

> Production-grade FastAPI + PostgreSQL backend for the AI Task Tracker desktop application.

---

## 🏗️ Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.111 |
| Database | PostgreSQL 16 + SQLAlchemy 2 (async) |
| Migrations | Alembic |
| Auth | JWT (access + refresh token rotation) |
| Scheduler | APScheduler (background jobs) |
| Logging | Loguru |
| Testing | pytest + pytest-asyncio + httpx |
| Packaging | Docker + PyInstaller (desktop) |

---

## 📁 Project Structure

```
ai_task_tracker/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/        # Route handlers (one file per resource)
│   │       │   ├── auth.py
│   │       │   ├── users.py
│   │       │   ├── tasks.py
│   │       │   ├── subtasks.py
│   │       │   ├── milestones.py
│   │       │   ├── notifications.py
│   │       │   ├── ai_suggestions.py
│   │       │   ├── dashboard.py
│   │       │   └── admin.py
│   │       └── router.py         # Central router registrations
│   ├── core/
│   │   ├── config.py             # Pydantic Settings
│   │   ├── security.py           # JWT + password hashing
│   │   ├── dependencies.py       # FastAPI DI functions
│   │   ├── exceptions.py         # Custom exceptions + handlers
│   │   ├── logging.py            # Loguru setup
│   │   └── scheduler.py          # APScheduler background jobs
│   ├── db/
│   │   ├── base.py               # DeclarativeBase + mixins
│   │   └── session.py            # Engine + session factory
│   ├── models/                   # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── task.py
│   │   ├── subtask.py
│   │   ├── milestone.py
│   │   ├── notification.py
│   │   ├── ai_suggestion.py
│   │   └── productivity.py
│   ├── schemas/                  # Pydantic request / response schemas
│   ├── services/                 # Business logic (no HTTP concerns)
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── task_service.py
│   │   ├── subtask_service.py
│   │   ├── milestone_service.py
│   │   ├── notification_service.py
│   │   ├── ai_engine.py          # Rule-based AI suggestion engine
│   │   └── productivity_service.py
│   └── utils/
│       ├── pagination.py
│       ├── streak.py
│       └── datetime_utils.py
├── migrations/                   # Alembic migrations
├── scripts/
│   ├── create_admin.py
│   ├── seed_data.py
│   └── generate_migration.py
├── tests/
│   ├── unit/                     # Pure unit tests (no DB)
│   └── integration/              # Full HTTP integration tests
├── main.py                       # Application factory + entry point
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── pytest.ini
├── requirements.txt
└── .env.example
```

---

## ⚡ Quick Start

### 1. Prerequisites

- Python 3.12+
- PostgreSQL 16 running locally (or via Docker)
- Redis (optional – required only for Celery tasks)

### 2. Clone and install

```bash
git clone <repo-url>
cd ai_task_tracker
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env — at minimum set DATABASE_URL and SECRET_KEY
```

### 4. Start PostgreSQL (Docker one-liner)

```bash
docker compose up postgres -d
```

### 5. Run the server

```bash
# Development (auto-reload)
make dev
# or
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

On first run the application will:
- Create all database tables automatically
- Seed the first admin user (credentials from `.env`)

### 6. Explore the API

Open **http://localhost:8000/api/docs** for the interactive Swagger UI.

---

## 🔑 Authentication Flow

```
POST /api/v1/auth/register   → Create account
POST /api/v1/auth/login      → { access_token, refresh_token }
GET  /api/v1/auth/me         → Current user (Bearer token required)
POST /api/v1/auth/refresh    → Rotate tokens
POST /api/v1/auth/logout     → Revoke session
POST /api/v1/auth/logout-all → Revoke all sessions
```

All protected routes require:
```
Authorization: Bearer <access_token>
```

---

## 📡 API Endpoints Summary

| Resource | Base Path |
|---|---|
| Auth | `/api/v1/auth` |
| Users | `/api/v1/users` |
| Tasks | `/api/v1/tasks` |
| Subtasks | `/api/v1/tasks/{id}/subtasks` |
| Milestones | `/api/v1/milestones` |
| Notifications | `/api/v1/notifications` |
| AI Suggestions | `/api/v1/ai-suggestions` |
| Dashboard | `/api/v1/dashboard` |
| Admin | `/api/v1/admin` |

---

## 🤖 AI Suggestion Engine

The rule-based engine in `app/services/ai_engine.py` analyses the user's tasks and productivity history every 6 hours (configurable) and generates contextual suggestions:

| Rule | Trigger |
|---|---|
| `OVERDUE_ALERT` | 1+ tasks are overdue |
| `DEADLINE_WARNING` | Task due within 24 hours |
| `PRIORITIZATION` | Urgent task not yet started |
| `WORKLOAD_BALANCE` | 10+ active tasks |
| `PRODUCTIVITY_BOOST` | 30-day completion rate < 40% |
| `BREAK_REMINDER` | 5+ tasks completed today |
| `STREAK_MOTIVATION` | Streak milestone reached (3/7/14/30/60/90 days) |
| `TASK_BREAKDOWN` | High-priority task with no subtasks |
| `FOCUS_MODE` | 3+ tasks in progress simultaneously |
| `TIME_MANAGEMENT` | 7-day average productivity score < 70 |

Manually trigger suggestions:
```
POST /api/v1/ai-suggestions/generate
```

---

## 🕐 Background Scheduler Jobs

| Job | Schedule | Purpose |
|---|---|---|
| Daily productivity log | 00:05 UTC | Snapshot metrics for all users |
| AI suggestions | Every 6 hours | Generate new suggestions |
| Overdue notifications | Every hour | Alert users on newly overdue tasks |
| Streak update | 00:01 UTC | Recalculate streak_days |
| Session cleanup | 03:00 UTC | Delete expired JWT sessions |
| Milestone status | Every 2 hours | Mark overdue milestones |

---

## 🗄️ Database Migrations

```bash
# Apply all pending migrations
make migrate

# Generate a new migration after model changes
make migration MSG="add user preferences table"

# Or manually
alembic revision --autogenerate -m "your message"
alembic upgrade head
```

---

## 🧪 Testing

```bash
# Run all tests
make test

# Unit tests only
make test-unit

# Integration tests only
make test-integration
```

Tests use a separate `ai_task_tracker_test` database. Each test runs in a transaction that is rolled back automatically.

---

## 🌱 Seed Demo Data

```bash
make seed
# Login: demo@aitasktracker.com / Demo@123456
```

---

## 🐳 Docker

```bash
# Start only infrastructure (DB + Redis)
docker compose up postgres redis -d

# Start full stack including API
docker compose --profile full up -d

# Include pgAdmin
docker compose --profile tools up -d
```

---

## 🖥️ Desktop Packaging (PyWebView + PyInstaller)

The backend is designed to be embedded in a desktop app:

```python
# desktop_app.py (frontend project)
import threading
import webview
import uvicorn
from main import app

def start_backend():
    uvicorn.run(app, host="127.0.0.1", port=8765)

threading.Thread(target=start_backend, daemon=True).start()
webview.create_window("AI Task Tracker", "http://127.0.0.1:8765")
webview.start()
```

Build executable:
```bash
pyinstaller --onefile --windowed desktop_app.py
```

---

## 🔒 Security Notes

- Change `SECRET_KEY` in `.env` before deploying (minimum 32 characters)
- Swagger UI is disabled in `production` mode
- All passwords are bcrypt-hashed (cost factor 12)
- Refresh tokens are rotated on every use
- Soft-delete is used for users and tasks (data preserved)
- Admin routes are protected by `is_admin` flag

---

## 📄 License

MIT — see `LICENSE` for details.
