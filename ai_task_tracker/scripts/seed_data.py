"""
Seed the database with realistic sample data for development / demo.

Usage:
    python scripts/seed_data.py
"""
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def seed():
    from app.db.session import AsyncSessionLocal, init_db
    from app.models.task import Task, TaskStatus, TaskPriority, TaskCategory
    from app.models.subtask import Subtask, SubtaskStatus
    from app.models.milestone import Milestone, MilestoneStatus
    from app.schemas.user import UserCreate
    from app.services.user_service import UserService
    from app.core.exceptions import ConflictError

    await init_db()

    async with AsyncSessionLocal() as db:
        # Create demo user
        try:
            user = await UserService.create(
                db,
                UserCreate(
                    username="demouser",
                    email="demo@aitasktracker.com",
                    password="Demo@123456",
                    full_name="Demo User",
                ),
            )
            user.is_verified = True
            print("✅  Demo user created: demo@aitasktracker.com / Demo@123456")
        except ConflictError:
            from sqlalchemy import select
            from app.models.user import User
            user = await db.scalar(select(User).where(User.email == "demo@aitasktracker.com"))
            print("ℹ️   Demo user already exists")

        now = datetime.now(timezone.utc)

        # Create milestones
        milestone1 = Milestone(
            user_id=user.id,
            title="Q3 Product Launch",
            description="All tasks related to the Q3 product launch",
            color="#6366f1",
            icon="🚀",
            status=MilestoneStatus.IN_PROGRESS,
            start_date=now - timedelta(days=30),
            due_date=now + timedelta(days=30),
        )
        milestone2 = Milestone(
            user_id=user.id,
            title="Personal Fitness Goals",
            description="Health and fitness milestones for this quarter",
            color="#22c55e",
            icon="💪",
            status=MilestoneStatus.PLANNED,
            due_date=now + timedelta(days=90),
        )
        db.add(milestone1)
        db.add(milestone2)
        await db.flush()

        # Create tasks
        tasks_data = [
            dict(title="Design new landing page", priority=TaskPriority.HIGH, category=TaskCategory.WORK,
                 status=TaskStatus.IN_PROGRESS, due_date=now + timedelta(days=3), milestone_id=milestone1.id,
                 estimated_hours=8.0, progress_percentage=40),
            dict(title="Write unit tests for API", priority=TaskPriority.HIGH, category=TaskCategory.WORK,
                 status=TaskStatus.TODO, due_date=now + timedelta(days=5), milestone_id=milestone1.id,
                 estimated_hours=4.0),
            dict(title="Set up CI/CD pipeline", priority=TaskPriority.MEDIUM, category=TaskCategory.WORK,
                 status=TaskStatus.TODO, due_date=now + timedelta(days=7), milestone_id=milestone1.id,
                 estimated_hours=3.0),
            dict(title="Overdue report submission", priority=TaskPriority.URGENT, category=TaskCategory.WORK,
                 status=TaskStatus.TODO, due_date=now - timedelta(days=2)),
            dict(title="Daily 30-minute run", priority=TaskPriority.MEDIUM, category=TaskCategory.HEALTH,
                 status=TaskStatus.COMPLETED, milestone_id=milestone2.id,
                 completed_at=now - timedelta(hours=3), progress_percentage=100),
            dict(title="Read Python Clean Code book", priority=TaskPriority.LOW, category=TaskCategory.LEARNING,
                 status=TaskStatus.IN_PROGRESS, due_date=now + timedelta(days=14),
                 estimated_hours=10.0, progress_percentage=30),
            dict(title="Grocery shopping", priority=TaskPriority.MEDIUM, category=TaskCategory.PERSONAL,
                 status=TaskStatus.TODO, due_date=now + timedelta(days=1), is_pinned=True),
            dict(title="Review monthly budget", priority=TaskPriority.MEDIUM, category=TaskCategory.FINANCE,
                 status=TaskStatus.TODO, due_date=now + timedelta(days=10)),
            dict(title="Prepare sprint retrospective", priority=TaskPriority.HIGH, category=TaskCategory.WORK,
                 status=TaskStatus.COMPLETED, completed_at=now - timedelta(days=1), progress_percentage=100),
            dict(title="Update resume", priority=TaskPriority.LOW, category=TaskCategory.PERSONAL,
                 status=TaskStatus.ON_HOLD),
        ]

        created_tasks = []
        for td in tasks_data:
            task = Task(user_id=user.id, **td)
            db.add(task)
            created_tasks.append(task)
        await db.flush()

        # Add subtasks to first task
        subtask_data = [
            ("Create wireframes", SubtaskStatus.COMPLETED, 0),
            ("Get design feedback", SubtaskStatus.COMPLETED, 1),
            ("Implement HTML/CSS", SubtaskStatus.IN_PROGRESS, 2),
            ("Add animations", SubtaskStatus.TODO, 3),
            ("Cross-browser testing", SubtaskStatus.TODO, 4),
        ]
        for title, status, idx in subtask_data:
            st = Subtask(
                task_id=created_tasks[0].id,
                title=title,
                status=status,
                order_index=idx,
                completed_at=now - timedelta(hours=idx + 1) if status == SubtaskStatus.COMPLETED else None,
            )
            db.add(st)

        # Update user stats
        await UserService.update_task_stats(db, user.id)

        # Recalculate milestone progress
        from app.services.milestone_service import MilestoneService
        await MilestoneService.recalculate_progress(db, milestone1.id)

        await db.commit()
        print(f"✅  Seeded {len(tasks_data)} tasks, 5 subtasks, 2 milestones")
        print("\n🎉  Seed complete! Log in with: demo@aitasktracker.com / Demo@123456")


if __name__ == "__main__":
    asyncio.run(seed())
