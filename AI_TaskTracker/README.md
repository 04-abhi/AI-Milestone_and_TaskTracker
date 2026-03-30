# AI Task Tracker v3

A desktop-first task management application built with FastAPI + vanilla JS.
Wrappable into a desktop app via PyWebView + PyInstaller.

## Bugs fixed from v2
| Bug | Root Cause | Fix |
|-----|-----------|-----|
| **Homepage shows nothing** | `Router.init()` fired before routes were registered | Moved `Router.init()` to the bottom of `pages.js`, after all `Router.register()` calls |
| **Opens at `/dashboard`** | SPA catch-all route didn't properly exclude static asset paths | Added explicit prefix guards in `main.py` |
| **Push not subscribing** | VAPID keys missing from `.env` | See setup below |

## New in v3
- ✅ **Subtasks** — add checklist items to any task
- 🏷️ **Tags** — comma-separated labels, filterable
- 📥 **Archive** — soft-delete; tasks hidden but kept
- 📊 **Progress bar** on dashboard
- ⏰ **Due in 48h** panel on dashboard
- ⌨️ **Keyboard shortcut** — press `N` anywhere to create a task

---

## Quick Start

### 1. Prerequisites
- Python 3.11+
- PostgreSQL running locally

### 2. Create database
```sql
CREATE DATABASE ait_v3;
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure `.env`
Edit `.env` and set your database credentials.
The defaults assume `postgres:root@localhost:5432`.

### 5. Run
```bash
python main.py
```

Open http://127.0.0.1:8000

Default login: `admin@ait.com` / `Admin@1234`

---

## Push Notifications Setup

Push notifications use the VAPID protocol and work in Chrome, Edge, Firefox, and Android Chrome.

### Step 1 — Generate keys (once)
```bash
python scripts/generate_vapid.py
```

### Step 2 — Add to `.env`
```
VAPID_PRIVATE_KEY="-----BEGIN EC PRIVATE KEY-----\n..."
VAPID_PUBLIC_KEY=BF2abc...xyz
VAPID_CLAIMS_EMAIL=your@email.com
```

### Step 3 — Enable in browser
Go to Settings → Push Notifications → Enable Notifications.

Reminders are sent automatically for tasks due within 24 hours (checked every 15 minutes).

---

## Project Structure

```
ait_v3/
├── main.py                        # FastAPI app entry point
├── .env                           # Config (copy and edit)
├── requirements.txt
├── app/
│   ├── api/v1/
│   │   ├── router.py
│   │   └── endpoints/
│   │       ├── auth.py            # Login, register, refresh
│   │       ├── users.py           # Profile, password, delete
│   │       ├── tasks.py           # Tasks + subtask CRUD
│   │       └── push.py            # Push notification endpoints
│   ├── core/
│   │   ├── config.py              # Settings from .env
│   │   ├── security.py            # JWT + bcrypt
│   │   ├── deps.py                # get_current_user dependency
│   │   └── scheduler.py           # APScheduler — due reminders
│   ├── db/
│   │   ├── base.py                # SQLAlchemy Base + TimestampMixin
│   │   └── session.py             # Async engine, get_db
│   ├── models/
│   │   ├── user.py
│   │   ├── task.py                # Task + Subtask models
│   │   └── push_subscription.py
│   ├── schemas/
│   │   ├── user.py
│   │   ├── task.py                # TaskCreate/Update/Out + Subtask schemas
│   │   └── push.py
│   └── services/
│       ├── user_service.py
│       ├── task_service.py        # Task + subtask business logic
│       └── push_service.py
├── frontend/
│   ├── index.html                 # SPA — single page app
│   ├── sw.js                      # Service worker (push notifications)
│   ├── css/style.css
│   └── js/
│       ├── api.js                 # HTTP client (tasks, subtasks, push)
│       ├── app.js                 # Router, Theme, Toast, Modal, State
│       ├── push.js                # PushManager
│       └── pages.js               # All page logic + Router.init() at bottom
└── scripts/
    └── generate_vapid.py          # Run once to generate VAPID keys
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | Login → tokens |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| GET  | `/api/v1/tasks` | List tasks (filters: status, priority, search, tag, include_archived) |
| POST | `/api/v1/tasks` | Create task |
| PATCH | `/api/v1/tasks/{id}` | Update task |
| POST | `/api/v1/tasks/{id}/archive` | Archive task |
| DELETE | `/api/v1/tasks/{id}` | Delete task |
| GET  | `/api/v1/tasks/{id}/subtasks` | List subtasks |
| POST | `/api/v1/tasks/{id}/subtasks` | Add subtask |
| PATCH | `/api/v1/tasks/{id}/subtasks/{sid}` | Update subtask |
| DELETE | `/api/v1/tasks/{id}/subtasks/{sid}` | Remove subtask |

Full interactive docs: http://127.0.0.1:8000/api/docs
