# AI Task Tracker v3 — Quick Start (5 Minutes)

## Prerequisites
- Python 3.10+
- PostgreSQL 13+
- Grok API Key (free from https://console.x.ai/)

## Install & Run

### 1. Extract & Setup
```bash
unzip AI_TaskTracker_Complete.zip
cd AI_TaskTracker_modified
cp .env.example .env
```

### 2. Add Grok API Key
Edit `.env` and add your API key from https://console.x.ai/:
```
GROK_API_KEY=xai-xxx...
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Start Backend
```bash
python main.py
```

You should see:
```
═══════════════════════════════════════════════════
  AI Task Tracker  v3.0
  Running at  http://127.0.0.1:8000
  API Docs:   http://127.0.0.1:8000/api/docs
═══════════════════════════════════════════════════

✓ Database ready
✓ Admin created: admin@ait.com
✓ Scheduler started
```

### 5. Open Browser
```
http://localhost:8000
```

**Login:**
- Email: `admin@ait.com`
- Password: `Admin@1234`

## Quick Demo (2 Minutes)

### Test 1: Create a Task
1. Click **✅ My Tasks**
2. Click **+ New Task**
3. Title: "Learn React", Due: Tomorrow, Priority: High
4. Save

### Test 2: AI Milestone Planner
1. Click **🚀 AI Planner**
2. Title: "Master Python"
3. Description: "From beginner to building scripts"
4. Days: "7"
5. Click **✨ Generate Plan**
6. Wait for AI to generate → Review → Click **💾 Save All Tasks**
7. Check **✅ My Tasks** — you'll see 7 tasks created automatically!

### Test 3: Procrastination Tracker
1. Click **✅ My Tasks**
2. Create a task with due date = **5 days ago**
3. **Don't mark as done**
4. Click **⏰ Catch Up** in sidebar
5. See your overdue task with 🔴 Critical badge
6. Try actions:
   - **📅 Reschedule** — Pick new date
   - **🤖 Break Down** — Generate AI recovery plan
   - **✅ Mark Done** — Complete
   - **🗑 Delete** — Remove

## File Structure

| File | What It Does |
|------|-------------|
| `SETUP.md` | Detailed installation & usage guide |
| `IMPLEMENTATION.md` | Architecture, APIs, technical details |
| `.env.example` | Configuration template |
| `requirements.txt` | Python dependencies |
| `main.py` | Start the app here |
| `app/` | Backend code |
| `frontend/` | HTML, CSS, JavaScript |

## Common Issues

**"GROK_API_KEY is not set"**
→ Add it to `.env` file, restart app

**"Could not connect to PostgreSQL"**
→ Make sure PostgreSQL is running
→ Check `DATABASE_URL` in `.env`

**"AI generation times out"**
→ Try simpler description
→ Check internet connection
→ Verify API key works

## Next Steps

- Read `SETUP.md` for full configuration
- Read `IMPLEMENTATION.md` for technical details
- Visit http://localhost:8000/api/docs for API documentation
- Enable push notifications in Settings (optional)

## Support

- Check logs in terminal
- Browser console: F12 → Console tab
- Review error messages in toasts

---

**You're ready to plan without procrastination! 🚀**
