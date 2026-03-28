"""
Pytest configuration and shared fixtures.
"""
import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from main import app

# Use a separate test database
TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    "/ai_task_tracker", "/ai_task_tracker_test"
)

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Create all tables at the start of the test session and drop them at the end."""
    import app.models  # noqa: F401
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional test session that rolls back after each test."""
    async with test_engine.begin() as conn:
        async with TestSessionLocal(bind=conn) as session:
            yield session
            await session.rollback()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client with the test DB injected."""
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ── Data factories ─────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_user(db: AsyncSession):
    from app.models.user import User
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("TestPass123"),
        full_name="Test User",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession):
    from app.models.user import User
    user = User(
        username="adminuser",
        email="admin@example.com",
        hashed_password=get_password_hash("AdminPass123"),
        full_name="Admin User",
        is_active=True,
        is_admin=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, test_user):
    """Return Authorization headers for the test user."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "TestPass123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, admin_user):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_task(db: AsyncSession, test_user):
    from app.models.task import Task, TaskStatus, TaskPriority, TaskCategory
    task = Task(
        user_id=test_user.id,
        title="Test Task",
        description="A task for testing",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        category=TaskCategory.WORK,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task


@pytest_asyncio.fixture
async def test_milestone(db: AsyncSession, test_user):
    from app.models.milestone import Milestone, MilestoneStatus
    milestone = Milestone(
        user_id=test_user.id,
        title="Test Milestone",
        description="A milestone for testing",
        status=MilestoneStatus.PLANNED,
        color="#6366f1",
    )
    db.add(milestone)
    await db.flush()
    await db.refresh(milestone)
    return milestone
