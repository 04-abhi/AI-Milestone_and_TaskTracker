"""
Rule-Based AI Suggestion Engine.

Analyses user productivity patterns and task data to generate
actionable, context-aware suggestions without any external LLM calls.
All logic is deterministic and explainable.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_suggestion import AISuggestion, SuggestionStatus, SuggestionType
from app.models.productivity import ProductivityLog
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.subtask import Subtask, SubtaskStatus


# ─── Rule weights & thresholds ─────────────────────────────────────────────────

OVERDUE_THRESHOLD = 1               # tasks overdue to fire alert
DUE_SOON_HOURS = 24                 # hours before due to warn
HIGH_WORKLOAD_TASKS = 10            # active tasks to consider overloaded
LOW_COMPLETION_RATE = 0.40          # below this → suggest focus
IDEAL_BREAK_TASK_COUNT = 5          # tasks completed before break reminder
LARGE_TASK_SUBTASK_THRESHOLD = 0    # tasks with 0 subtasks & high complexity
STREAK_MILESTONES = {3, 7, 14, 30, 60, 90}


# ─── Engine ────────────────────────────────────────────────────────────────────

class AIEngine:
    """
    Rule-based engine that evaluates a set of heuristic rules against
    the user's current task state and productivity history, then
    persists the top-N non-duplicate suggestions.
    """

    MAX_PENDING_SUGGESTIONS = 10  # max unread suggestions to keep

    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id
        self._now = datetime.now(timezone.utc)

    # ── Public entry point ──────────────────────────────────────────────────

    async def generate_suggestions(self) -> List[AISuggestion]:
        """Run all rules and persist new suggestions."""
        logger.info(f"AIEngine: generating suggestions for user {self.user_id}")

        # Load data once
        ctx = await self._build_context()

        candidates: List[Dict[str, Any]] = []
        candidates += self._rule_overdue_alert(ctx)
        candidates += self._rule_deadline_warning(ctx)
        candidates += self._rule_prioritization(ctx)
        candidates += self._rule_workload_balance(ctx)
        candidates += self._rule_low_completion_rate(ctx)
        candidates += self._rule_break_reminder(ctx)
        candidates += self._rule_streak_motivation(ctx)
        candidates += self._rule_task_breakdown(ctx)
        candidates += self._rule_focus_mode(ctx)
        candidates += self._rule_productivity_boost(ctx)

        # Deduplicate by suggestion_type (keep highest priority)
        candidates = self._deduplicate(candidates)

        # Persist new ones (skip types that already have a PENDING suggestion)
        existing_types = await self._get_existing_pending_types()
        new_suggestions: List[AISuggestion] = []

        for c in candidates:
            if c["suggestion_type"] in existing_types:
                continue
            suggestion = AISuggestion(
                user_id=self.user_id,
                suggestion_type=c["suggestion_type"],
                title=c["title"],
                message=c["message"],
                action_label=c.get("action_label"),
                action_data=json.dumps(c.get("action_data")) if c.get("action_data") else None,
                confidence_score=c.get("confidence_score", 1.0),
                priority_score=c.get("priority_score", 50),
                trigger_context=json.dumps(c.get("trigger_context")) if c.get("trigger_context") else None,
                related_task_ids=json.dumps(c.get("related_task_ids")) if c.get("related_task_ids") else None,
            )
            self.db.add(suggestion)
            new_suggestions.append(suggestion)
            existing_types.add(c["suggestion_type"])

        if new_suggestions:
            await self.db.flush()
            logger.info(f"AIEngine: created {len(new_suggestions)} suggestions for user {self.user_id}")

        return new_suggestions

    # ── Context builder ─────────────────────────────────────────────────────

    async def _build_context(self) -> Dict[str, Any]:
        now = self._now

        # Active tasks
        active_tasks = (
            await self.db.scalars(
                select(Task).where(
                    Task.user_id == self.user_id,
                    Task.status.not_in([TaskStatus.COMPLETED, TaskStatus.CANCELLED]),
                    Task.deleted_at.is_(None),
                )
            )
        ).all()

        # Overdue tasks
        overdue_tasks = [t for t in active_tasks if t.due_date and t.due_date < now]

        # Due within 24 hours
        due_soon = [
            t for t in active_tasks
            if t.due_date and now <= t.due_date <= now + timedelta(hours=DUE_SOON_HOURS)
        ]

        # Completed today
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        completed_today = await self.db.scalar(
            select(func.count(Task.id)).where(
                Task.user_id == self.user_id,
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at >= today_start,
                Task.deleted_at.is_(None),
            )
        ) or 0

        # Productivity history (last 30 days)
        thirty_days_ago = (now - timedelta(days=30)).date()
        logs = (
            await self.db.scalars(
                select(ProductivityLog).where(
                    ProductivityLog.user_id == self.user_id,
                    ProductivityLog.log_date >= thirty_days_ago,
                ).order_by(ProductivityLog.log_date.desc())
            )
        ).all()

        avg_completion_rate = (
            sum(l.completion_rate for l in logs) / len(logs) if logs else 0.0
        )

        # Tasks without subtasks (potential breakdown candidates)
        tasks_without_subtasks = []
        for t in active_tasks:
            if t.priority in (TaskPriority.HIGH, TaskPriority.URGENT):
                count = await self.db.scalar(
                    select(func.count(Subtask.id)).where(
                        Subtask.task_id == t.id,
                        Subtask.deleted_at.is_(None),
                    )
                ) or 0
                if count == 0:
                    tasks_without_subtasks.append(t)

        # Streak
        from app.models.user import User
        user = await self.db.scalar(select(User).where(User.id == self.user_id))
        streak_days = user.streak_days if user else 0

        return {
            "active_tasks": list(active_tasks),
            "overdue_tasks": list(overdue_tasks),
            "due_soon_tasks": due_soon,
            "completed_today": completed_today,
            "productivity_logs": list(logs),
            "avg_completion_rate": avg_completion_rate,
            "tasks_without_subtasks": tasks_without_subtasks,
            "streak_days": streak_days,
        }

    # ── Rules ───────────────────────────────────────────────────────────────

    def _rule_overdue_alert(self, ctx: Dict) -> List[Dict]:
        overdue = ctx["overdue_tasks"]
        if len(overdue) < OVERDUE_THRESHOLD:
            return []
        titles = ", ".join(f'"{t.title}"' for t in overdue[:3])
        extra = f" and {len(overdue) - 3} more" if len(overdue) > 3 else ""
        return [
            {
                "suggestion_type": SuggestionType.OVERDUE_ALERT,
                "title": f"⚠️ {len(overdue)} Overdue Task{'s' if len(overdue) > 1 else ''}",
                "message": (
                    f"You have {len(overdue)} overdue task(s): {titles}{extra}. "
                    "Address them now to maintain your productivity momentum."
                ),
                "action_label": "View Overdue Tasks",
                "action_data": {"filter": "overdue"},
                "confidence_score": 1.0,
                "priority_score": 95,
                "related_task_ids": [t.id for t in overdue],
                "trigger_context": {"overdue_count": len(overdue)},
            }
        ]

    def _rule_deadline_warning(self, ctx: Dict) -> List[Dict]:
        due_soon = ctx["due_soon_tasks"]
        if not due_soon:
            return []
        urgent = sorted(due_soon, key=lambda t: t.due_date)
        task = urgent[0]
        hours_left = int((task.due_date - self._now).total_seconds() / 3600)
        return [
            {
                "suggestion_type": SuggestionType.DEADLINE_WARNING,
                "title": f"⏰ Deadline Approaching: {task.title[:40]}",
                "message": (
                    f'"{task.title}" is due in approximately {hours_left} hour(s). '
                    f"You have {len(due_soon)} task(s) due within 24 hours total."
                ),
                "action_label": "Open Task",
                "action_data": {"task_id": task.id},
                "confidence_score": 0.95,
                "priority_score": 90,
                "related_task_ids": [t.id for t in due_soon],
                "trigger_context": {"due_soon_count": len(due_soon)},
            }
        ]

    def _rule_prioritization(self, ctx: Dict) -> List[Dict]:
        active = ctx["active_tasks"]
        urgent = [t for t in active if t.priority == TaskPriority.URGENT]
        if not urgent:
            return []
        in_progress = [t for t in urgent if t.status == TaskStatus.IN_PROGRESS]
        if in_progress:
            return []  # Already working on urgent task
        task = urgent[0]
        return [
            {
                "suggestion_type": SuggestionType.PRIORITIZATION,
                "title": f"🔴 Urgent Task Needs Attention",
                "message": (
                    f'You have {len(urgent)} urgent task(s) not yet started. '
                    f'Consider starting "{task.title}" immediately.'
                ),
                "action_label": "Start Task",
                "action_data": {"task_id": task.id},
                "confidence_score": 0.9,
                "priority_score": 85,
                "related_task_ids": [t.id for t in urgent],
            }
        ]

    def _rule_workload_balance(self, ctx: Dict) -> List[Dict]:
        active = ctx["active_tasks"]
        if len(active) < HIGH_WORKLOAD_TASKS:
            return []
        high_priority = [t for t in active if t.priority in (TaskPriority.HIGH, TaskPriority.URGENT)]
        return [
            {
                "suggestion_type": SuggestionType.WORKLOAD_BALANCE,
                "title": "📊 High Workload Detected",
                "message": (
                    f"You have {len(active)} active tasks ({len(high_priority)} high/urgent priority). "
                    "Consider deferring or delegating lower-priority items to stay focused."
                ),
                "action_label": "Review Tasks",
                "action_data": {"filter": "active"},
                "confidence_score": 0.8,
                "priority_score": 70,
                "trigger_context": {"active_count": len(active), "high_priority_count": len(high_priority)},
            }
        ]

    def _rule_low_completion_rate(self, ctx: Dict) -> List[Dict]:
        rate = ctx["avg_completion_rate"]
        logs = ctx["productivity_logs"]
        if not logs or len(logs) < 3:
            return []
        if rate >= LOW_COMPLETION_RATE:
            return []
        return [
            {
                "suggestion_type": SuggestionType.PRODUCTIVITY_BOOST,
                "title": "📉 Completion Rate Could Be Better",
                "message": (
                    f"Your 30-day task completion rate is {rate:.0%}. "
                    "Try breaking tasks into smaller subtasks and tackling the easiest one first to build momentum."
                ),
                "action_label": "View Analytics",
                "action_data": {"tab": "analytics"},
                "confidence_score": 0.85,
                "priority_score": 65,
                "trigger_context": {"completion_rate": round(rate, 2)},
            }
        ]

    def _rule_break_reminder(self, ctx: Dict) -> List[Dict]:
        completed_today = ctx["completed_today"]
        if completed_today < IDEAL_BREAK_TASK_COUNT:
            return []
        return [
            {
                "suggestion_type": SuggestionType.BREAK_REMINDER,
                "title": "☕ Great Progress — Take a Break!",
                "message": (
                    f"You've completed {completed_today} tasks today! "
                    "Taking a short break (5–15 minutes) can help sustain your focus for the rest of the day."
                ),
                "action_label": "Start Timer",
                "action_data": {"minutes": 10},
                "confidence_score": 0.75,
                "priority_score": 40,
                "trigger_context": {"completed_today": completed_today},
            }
        ]

    def _rule_streak_motivation(self, ctx: Dict) -> List[Dict]:
        streak = ctx["streak_days"]
        if streak not in STREAK_MILESTONES:
            return []
        return [
            {
                "suggestion_type": SuggestionType.STREAK_MOTIVATION,
                "title": f"🔥 {streak}-Day Streak — Keep It Up!",
                "message": (
                    f"You've been productive for {streak} consecutive days. "
                    "Consistency is the key to achieving your goals. Don't break the chain!"
                ),
                "confidence_score": 1.0,
                "priority_score": 60,
                "trigger_context": {"streak_days": streak},
            }
        ]

    def _rule_task_breakdown(self, ctx: Dict) -> List[Dict]:
        candidates = ctx["tasks_without_subtasks"]
        if not candidates:
            return []
        task = candidates[0]
        return [
            {
                "suggestion_type": SuggestionType.TASK_BREAKDOWN,
                "title": f"📝 Break Down a Complex Task",
                "message": (
                    f'"{task.title}" is marked as {task.priority.value} priority but has no subtasks. '
                    "Breaking it into smaller steps makes it easier to track progress and stay motivated."
                ),
                "action_label": "Add Subtasks",
                "action_data": {"task_id": task.id},
                "confidence_score": 0.8,
                "priority_score": 55,
                "related_task_ids": [t.id for t in candidates],
            }
        ]

    def _rule_focus_mode(self, ctx: Dict) -> List[Dict]:
        active = ctx["active_tasks"]
        in_progress = [t for t in active if t.status == TaskStatus.IN_PROGRESS]
        if len(in_progress) <= 2:
            return []
        return [
            {
                "suggestion_type": SuggestionType.FOCUS_MODE,
                "title": f"🎯 Too Many Tasks In Progress",
                "message": (
                    f"You have {len(in_progress)} tasks in progress simultaneously. "
                    "Research shows single-tasking improves quality and speed. "
                    "Try completing or pausing some before starting new ones."
                ),
                "action_label": "View In Progress",
                "action_data": {"filter": "in_progress"},
                "confidence_score": 0.85,
                "priority_score": 72,
                "trigger_context": {"in_progress_count": len(in_progress)},
            }
        ]

    def _rule_productivity_boost(self, ctx: Dict) -> List[Dict]:
        logs = ctx["productivity_logs"]
        if not logs or len(logs) < 7:
            return []
        recent = logs[:7]
        avg_score = sum(l.productivity_score for l in recent) / len(recent)
        if avg_score >= 70:
            return []
        return [
            {
                "suggestion_type": SuggestionType.TIME_MANAGEMENT,
                "title": "⏱️ Improve Your Daily Routine",
                "message": (
                    f"Your 7-day average productivity score is {avg_score:.1f}/100. "
                    "Consider time-blocking: assign specific hours to specific task categories "
                    "to reduce context switching."
                ),
                "action_label": "View Productivity",
                "action_data": {"tab": "productivity"},
                "confidence_score": 0.78,
                "priority_score": 58,
                "trigger_context": {"avg_score_7d": round(avg_score, 1)},
            }
        ]

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _deduplicate(self, candidates: List[Dict]) -> List[Dict]:
        seen: set = set()
        result = []
        for c in sorted(candidates, key=lambda x: x.get("priority_score", 0), reverse=True):
            t = c["suggestion_type"]
            if t not in seen:
                seen.add(t)
                result.append(c)
        return result

    async def _get_existing_pending_types(self) -> set:
        existing = (
            await self.db.scalars(
                select(AISuggestion.suggestion_type).where(
                    AISuggestion.user_id == self.user_id,
                    AISuggestion.status == SuggestionStatus.PENDING,
                )
            )
        ).all()
        return set(existing)


# ─── Suggestion CRUD helpers ────────────────────────────────────────────────────

class AISuggestionService:

    @staticmethod
    async def generate_for_user(db: AsyncSession, user_id: int) -> List[AISuggestion]:
        engine = AIEngine(db, user_id)
        return await engine.generate_suggestions()

    @staticmethod
    async def list_for_user(
        db: AsyncSession,
        user_id: int,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 20,
    ):
        query = select(AISuggestion).where(
            AISuggestion.user_id == user_id,
            AISuggestion.status == SuggestionStatus.PENDING,
        )
        if unread_only:
            query = query.where(AISuggestion.is_read == False)  # noqa: E712

        total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
        suggestions = (
            await db.scalars(
                query.order_by(AISuggestion.priority_score.desc()).offset(skip).limit(limit)
            )
        ).all()
        return list(suggestions), total

    @staticmethod
    async def update_status(
        db: AsyncSession, suggestion_id: int, user_id: int, status: SuggestionStatus
    ) -> Optional[AISuggestion]:
        suggestion = await db.scalar(
            select(AISuggestion).where(
                AISuggestion.id == suggestion_id, AISuggestion.user_id == user_id
            )
        )
        if suggestion:
            suggestion.status = status
            suggestion.is_read = True
            await db.flush()
        return suggestion

    @staticmethod
    async def mark_read(db: AsyncSession, suggestion_id: int, user_id: int) -> bool:
        suggestion = await db.scalar(
            select(AISuggestion).where(
                AISuggestion.id == suggestion_id, AISuggestion.user_id == user_id
            )
        )
        if suggestion:
            suggestion.is_read = True
            await db.flush()
            return True
        return False
