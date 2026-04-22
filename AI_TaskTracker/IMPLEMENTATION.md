# AI Task Tracker v3 — Implementation Summary

## What Was Built

A complete task management system with **AI-powered planning** and **procrastination detection/recovery**.

---

## Core Features Implemented

### 1. **AI Milestone Planner** (🚀)
**Purpose:** Break down any goal into a realistic day-by-day action plan  
**How it works:**
- User enters: goal title, description, deadline in days
- Frontend sends request to backend `/api/v1/ai/plan`
- Backend calls Grok AI (xAI Cloud) with structured prompt
- Grok returns JSON with day-by-day tasks and subtasks
- Frontend shows preview — user can edit before saving
- On save: creates individual tasks (Day 1, Day 2, etc.) with proper due dates and subtasks

**Example flow:**
```
Input: "Learn React", "Want to build interactive UIs", 14 days
↓
Backend calls Grok AI (/v1/chat/completions)
↓
Returns: {"title":"Learn React","plan":[{"day":1,"task":"Setup & basics","subtasks":[...]},{"day":2,...}]}
↓
Frontend renders editable cards
↓
User saves → 14 tasks created, spaced across 14 days
```

---

### 2. **Procrastination Tracker & Recovery** (⏰)
**Purpose:** Detect overdue/stalled tasks and help recover with AI-assisted plans

#### Detection Algorithm
A task is flagged when it matches **any two** of:
- **Overdue:** `due_date < now` and `status != done`
- **Stale:** Last update > 3 days ago, still not done
- **Deadline extended 2+:** User rescheduled it multiple times

#### User Actions

**Option 1: Reschedule**
- Click **📅 Reschedule**
- Pick new due date
- If task has tags: choose to reschedule ONLY this task OR all tasks with that tag
- Increments `deadline_extended_count`
- Resets procrastination notification flag

**Option 2: AI Break Down**
- Click **🤖 Break Down**
- Enter how many days to spread remaining work
- Backend calls Grok AI with:
  - Task title, description
  - Days overdue
  - Already-completed subtasks (AI skips these)
  - Remaining subtasks
- AI generates recovery plan for remaining work only
- Frontend shows preview with editable day cards
- On save: creates recovery tasks (Day 1, Day 2, etc.) tagged with "recovery"
- Original task marked `status=in_progress` with new due date

**Option 3: Quick Actions**
- **✅ Mark Done** — Complete immediately
- **🗑 Delete** — Remove task

#### Automatic Notifications
- **Every 6 hours:** Scheduler finds unnotified overdue tasks
- Sends grouped push notification: "⏰ 3 tasks need your attention: Task A, Task B, ..."
- Each task notified only once per procrastination episode

---

### 3. **Backend Architecture**

#### New Files Added

**`app/services/ai_service.py`** — AI integration layer
- `_call_grok()` — Posts to Grok OpenAI-compatible API
- `generate_milestone_plan()` — Returns structured day-wise plan
- `generate_breakdown_plan()` — Generates recovery plan, skips done subtasks
- `_strip_fences()` — Cleans markdown wrappers from AI responses
- `_parse_json_response()` — Parses & validates JSON with error handling

**`app/api/v1/endpoints/ai.py`** — REST endpoints
- `POST /api/v1/ai/plan` — Request: title, description, days → Response: plan JSON
- `POST /api/v1/ai/breakdown` — Request: task details, recovery days → Response: recovery plan

**Updated `app/models/task.py`**
- Added: `original_due_date` — Preserves original deadline on first extension
- Added: `deadline_extended_count` — Tracks reschedules
- Added: `procrastination_notified` — Throttles notifications (one per episode)

**Updated `app/services/task_service.py`**
- `compute_procrastination_score()` — Calculates 0–3 score (1=overdue, 2=stale, 3=both)
- `get_procrastinated_tasks()` — Returns overdue tasks sorted by score
- `reschedule_task()` — Updates due date, increments extension count
- `reschedule_by_tag()` — Reschedules all tasks with a tag
- `get_overdue_unnotified_tasks()` — For scheduler
- `mark_procrastination_notified()` — Marks task as notified

**Updated `app/core/scheduler.py`**
- Added `_send_procrastination_alerts()` job running every 6 hours
- Groups tasks by user, sends one notification per user
- Marks tasks as notified to prevent spam

**Updated `app/core/config.py`**
- `GROK_API_KEY` — From .env
- `GROK_MODEL` — Model name (gpt-oss:120b)
- `GROK_API_BASE` — API endpoint (https://api.x.ai/v1)

---

### 4. **Frontend Changes**

#### New JS Objects/Methods

**MilestonePlanner (pages.js)**
- `render()` — Initialize page
- `generate()` — Calls `/api/v1/ai/plan`, shows skeleton, handles response
- `_renderPreview()` — Shows editable day cards
- `_dayCard()` — Renders single day with task & subtasks inputs
- `saveAll()` — Creates tasks for each day with proper due dates & subtasks
- `reset()` — Clears form & state

**ProcrastinationTracker (pages.js)**
- `render()` — Loads and displays procrastinated tasks
- `_load()` — Fetches `/api/v1/tasks/procrastinated`
- `_taskCard()` — Renders overdue task with score badge, progress, actions
- `openReschedule()` — Modal: pick new date, choose to apply to tag or single task
- `confirmReschedule()` — POSTs to `/api/v1/tasks/{id}/reschedule`
- `openBreakdown()` — Modal: set recovery days
- `generateBreakdown()` — Calls `/api/v1/ai/breakdown`, shows preview
- `saveBreakdown()` — Creates recovery tasks
- `silentCheck()` — Called after login/task save, updates nav badge count

#### New API Endpoints (frontend)
**api.js**
- `API.ai.plan(data)` → POST `/api/v1/ai/plan`
- `API.ai.breakdown(data)` → POST `/api/v1/ai/breakdown`

#### New Pages & Modals
- **Page:** `#/procrastination` (Catch Up tab)
- **Modal:** `#modal-reschedule` (reschedule form)
- **Modal:** `#modal-breakdown` (break down task flow)

#### UI Removals
- Removed "Send Test" notification button from Settings
- Removed `PushManager.sendTest()` method
- Kept push subscription/unsubscription intact

---

### 5. **Configuration**

#### New `.env.example` Variables
```
GROK_API_KEY=xai-...          # From https://console.x.ai/
GROK_MODEL=gpt-oss:120b       # Grok model
GROK_API_BASE=https://api.x.ai/v1
```

#### Flow Without Ollama
**Before:** Frontend → localhost:11434 (Ollama on same machine)  
**Now:** Frontend → Backend → xAI Cloud (Grok API)

**Benefits:**
- No local Ollama installation needed
- Grok 120B model (much faster, better quality than 20B)
- Scales easily for production
- Pay-as-you-go (xAI free tier includes credits)

---

## File Structure

```
AI_TaskTracker_modified/
├── app/
│   ├── api/v1/
│   │   ├── endpoints/
│   │   │   ├── ai.py                  ✨ NEW
│   │   │   ├── tasks.py               ✏️ UPDATED (reschedule endpoints)
│   │   │   └── ...
│   │   └── router.py                  ✏️ UPDATED (register AI router)
│   ├── models/
│   │   └── task.py                    ✏️ UPDATED (procrastination fields)
│   ├── services/
│   │   ├── ai_service.py              ✨ NEW (Grok API calls)
│   │   ├── task_service.py            ✏️ UPDATED (procrastination logic)
│   │   └── ...
│   ├── core/
│   │   ├── config.py                  ✏️ UPDATED (Grok config)
│   │   ├── scheduler.py               ✏️ UPDATED (procrastination alerts)
│   │   └── ...
│   └── db/
├── frontend/
│   ├── js/
│   │   ├── pages.js                   ✏️ UPDATED (MilestonePlanner, ProcrastinationTracker)
│   │   ├── api.js                     ✏️ UPDATED (AI endpoints)
│   │   ├── push.js                    ✏️ UPDATED (removed test notification)
│   │   └── ...
│   ├── index.html                     ✏️ UPDATED (new pages, modals, nav)
│   ├── css/style.css                  ✏️ UPDATED (procrastination styles)
│   └── ...
├── main.py                            (unchanged)
├── requirements.txt                   ✏️ UPDATED (added httpx)
├── SETUP.md                           ✨ NEW (detailed setup guide)
├── .env.example                       ✨ NEW (configuration template)
└── README.md                          (original)
```

---

## Testing the Implementation

### 1. Start the App
```bash
cp .env.example .env
# Edit .env: add GROK_API_KEY from https://console.x.ai/
pip install -r requirements.txt
python main.py
```

### 2. Access Frontend
- **URL:** http://localhost:8000
- **Login:** admin@ait.com / Admin@1234

### 3. Test Milestone Planner
1. Click **🚀 AI Planner** in sidebar
2. Enter:
   - Title: "Learn Python"
   - Description: "From zero to building scripts"
   - Days: "10"
3. Click **✨ Generate Plan**
4. Watch skeleton loader → Grok generates 10-day plan
5. Edit day cards if desired
6. Click **💾 Save All Tasks** → 10 tasks created

### 4. Test Procrastination Tracker
1. Create a task with due date = 5 days ago
2. Don't mark as done
3. Navigate to **⏰ Catch Up**
4. Task should appear with "🔴 Overdue" badge
5. Test actions:
   - **📅 Reschedule** — Pick new date
   - **🤖 Break Down** — Generate recovery plan
   - **✅ Mark Done** — Complete
   - **🗑 Delete** — Remove

### 5. Test Bulk Reschedule
1. Create 3 tasks with tag "work" and due date = 3 days ago
2. Go to **⏰ Catch Up**
3. Click **📅 Reschedule** on one task
4. Select "All work tasks"
5. All 3 tasks should reschedule to new date

### 6. Check Notifications
1. Go to **⚙️ Settings** → Push Notifications
2. Click **🔔 Enable Notifications**
3. Grant browser permission
4. Wait for scheduler (every 6 hours) or manually trigger via API

---

## Architecture Diagrams

### Milestone Planner Flow
```
User Input (Goal)
    ↓
Frontend: /api/v1/ai/plan
    ↓
Backend receives { title, description, days }
    ↓
ai_service.generate_milestone_plan()
    ↓
Grok API (xAI Cloud) via httpx.AsyncClient
    ↓
Grok returns: { "plan": [...] }
    ↓
Backend parses & validates JSON
    ↓
Frontend receives plan
    ↓
User edits day cards (optional)
    ↓
Frontend: /api/v1/tasks (POST x days)
    ↓
Tasks created with proper due dates & subtasks
```

### Procrastination Detection Flow
```
Every 6 hours: Scheduler runs _send_procrastination_alerts()
    ↓
Query: Tasks with due_date < now, status != done, procrastination_notified=false
    ↓
For each task: compute_procrastination_score()
    ↓
Score >= 1: Task is procrastinated
    ↓
Group by user → Send push notification
    ↓
Mark tasks: procrastination_notified=true
    ↓
User sees: ⏰ 3 tasks need your attention
    ↓
Click → Navigates to /procrastination page
    ↓
GET /api/v1/tasks/procrastinated
    ↓
Frontend shows cards with action buttons
```

### Recovery Plan Flow
```
User clicks: 🤖 Break Down
    ↓
Modal: Enter recovery days
    ↓
Frontend: /api/v1/ai/breakdown
    ↓
Body: { title, description, due_date, recovery_days, done_subtasks, pending_subtasks }
    ↓
Backend: ai_service.generate_breakdown_plan()
    ↓
Grok API (with prompt emphasizing: skip done work, plan remaining only)
    ↓
Grok returns: { "plan": [...day 1, day 2, ...], "remaining_summary": "..." }
    ↓
Frontend shows preview
    ↓
User edits (optional)
    ↓
User clicks: 💾 Save Recovery Plan
    ↓
For each recovery day:
    - Create task: "Day N – {task}"
    - Add subtasks
    - Set due date: today + (N-1) days
    - Tag: "recovery"
    ↓
Original task: reschedule to last recovery day, mark in_progress
    ↓
Done!
```

---

## API Reference

### Milestone Planner

**Request:**
```bash
POST /api/v1/ai/plan
Content-Type: application/json
Authorization: Bearer {access_token}

{
  "title": "Learn React",
  "description": "Want to build interactive UIs with hooks and state",
  "days": 14
}
```

**Response:**
```json
{
  "title": "Learn React",
  "description": "Want to build interactive UIs with hooks and state",
  "deadline_days": 14,
  "plan": [
    {
      "day": 1,
      "task": "Setup React environment",
      "subtasks": [
        "Install Node.js and npm",
        "Create new React app with create-react-app",
        "Explore project structure"
      ]
    },
    {
      "day": 2,
      "task": "Learn JSX basics",
      "subtasks": [...]
    }
    ...
  ]
}
```

### Breakdown Planner

**Request:**
```bash
POST /api/v1/ai/breakdown
Content-Type: application/json
Authorization: Bearer {access_token}

{
  "title": "Build Portfolio Website",
  "description": "Personal website with projects and blog",
  "due_date": "2024-04-10T09:00:00Z",
  "recovery_days": 7,
  "done_subtasks": ["Design mockup", "Set up hosting"],
  "pending_subtasks": ["Code frontend", "Set up database", "Deploy"]
}
```

**Response:**
```json
{
  "title": "Build Portfolio Website",
  "remaining_summary": "Complete frontend code, setup database, and deploy to production.",
  "recovery_days": 7,
  "plan": [
    {
      "day": 1,
      "task": "Setup development environment",
      "subtasks": [...]
    },
    ...
  ]
}
```

### Reschedule Task

**Request:**
```bash
POST /api/v1/tasks/{id}/reschedule
Content-Type: application/json
Authorization: Bearer {access_token}

{
  "new_due_date": "2024-05-15T09:00:00Z",
  "apply_to_tag": "work"  // Optional: null for single task, "work" for all with tag
}
```

**Response:**
```json
[
  {
    "id": 123,
    "title": "Task 1",
    "due_date": "2024-05-15T09:00:00Z",
    "deadline_extended_count": 2,
    ...
  },
  {
    "id": 124,
    "title": "Task 2",
    "due_date": "2024-05-15T09:00:00Z",
    "deadline_extended_count": 1,
    ...
  }
]
```

### Get Procrastinated Tasks

**Request:**
```bash
GET /api/v1/tasks/procrastinated
Authorization: Bearer {access_token}
```

**Response:**
```json
[
  {
    "id": 1,
    "title": "Overdue task",
    "due_date": "2024-04-10T09:00:00Z",
    "procrastination_score": 3,
    "status": "todo",
    "deadline_extended_count": 2,
    "subtasks": [
      {"id": 1, "title": "Subtask", "is_done": false}
    ],
    ...
  }
]
```

---

## Key Decisions & Rationale

| Decision | Rationale |
|----------|-----------|
| Backend AI calls | Security: API key never exposed to frontend |
| Grok xAI vs Ollama | Speed: 120B model faster than 20B. Scalable. Cloud-based. |
| Procrastination scoring | Composite (overdue + stale + extended) catches more cases |
| Skip completed subtasks in breakdown | Respects user progress. Regenerates only remaining work. |
| Bulk reschedule by tag | Saves time: one action reschedules related tasks |
| 6-hour notification check | Balances awareness (not spammy) with timely nudges |
| Separate recovery tasks | Clear visual separation. Easy to track recovery separately. |

---

## Future Enhancements

- [ ] Analytics dashboard: procrastination patterns by tag/priority
- [ ] Smart suggestions: "You procrastinate 'writing' tasks 60% of the time"
- [ ] Custom AI models: user-trained models for personalized plans
- [ ] Recurring tasks: templates that repeat daily/weekly
- [ ] Time tracking: actual time spent vs estimated
- [ ] Collaboration: share tasks/plans with others
- [ ] Mobile app: React Native version
- [ ] Offline mode: service worker caching for offline task viewing

---

## Deployment Checklist

- [ ] `.env` configured with Grok API key
- [ ] PostgreSQL database created and running
- [ ] `python main.py` starts without errors
- [ ] Browser opens to login page
- [ ] Can create task, milestone plan, and procrastinated task
- [ ] AI endpoints return valid responses
- [ ] Push notifications work (if VAPID keys set)
- [ ] Scheduler runs without errors

---

## Support

For setup help, see `SETUP.md` in the project root.

For API documentation, visit http://localhost:8000/api/docs after starting the app.

---

**Built with FastAPI, SQLAlchemy, PostgreSQL, and Grok AI** 🚀
