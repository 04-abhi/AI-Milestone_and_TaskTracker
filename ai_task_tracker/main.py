"""
AI Task Tracker – FastAPI Application Entry Point
=================================================
Run with:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    generic_exception_handler,
    http_exception_handler,
)
from app.core.logging import setup_logging
from app.core.scheduler import start_scheduler, stop_scheduler
from app.db.session import init_db


# ── Logging ────────────────────────────────────────────────────────────────────
setup_logging()

# ── Sentry (optional) ──────────────────────────────────────────────────────────
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.1,
        environment=settings.APP_ENV,
    )
    logger.info("Sentry initialised")


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.APP_ENV}]")

    # Create DB tables (idempotent; use Alembic for production migrations)
    await init_db()
    logger.info("Database tables verified / created")

    # Seed first admin user if it doesn't exist
    await _seed_admin()

    # Start background scheduler
    start_scheduler()

    yield  # ← application is running

    # Shutdown
    stop_scheduler()
    logger.info(f"{settings.APP_NAME} shutdown complete")


# ── Application factory ────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "Production-grade FastAPI backend for the AI Task Tracker desktop application. "
            "Provides task, subtask, and milestone management with a rule-based AI suggestion engine."
        ),
        version=settings.APP_VERSION,
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url="/api/redoc" if not settings.is_production else None,
        openapi_url="/api/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Middleware ─────────────────────────────────────────────────────────────
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception handlers ─────────────────────────────────────────────────────
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # ── Routes ─────────────────────────────────────────────────────────────────
    app.include_router(api_router)
    
    # Serve frontend static files
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    if os.path.exists(frontend_dir):
        app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
        app.mount("/css", StaticFiles(directory=os.path.join(frontend_dir, "css")), name="css")
        app.mount("/js", StaticFiles(directory=os.path.join(frontend_dir, "js")), name="js")

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Don't intercept API routes
        if full_path.startswith("api/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404)
        index = os.path.join(frontend_dir, "index.html")
        return FileResponse(index)

    # Health-check (unauthenticated)
    @app.get("/health", tags=["Health"], include_in_schema=False)
    async def health():
        return {
            "status": "ok",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
        }

    @app.get("/", tags=["Root"], include_in_schema=False)
    async def root():
        return {
            "message": f"Welcome to {settings.APP_NAME} API",
            "docs": "/api/docs",
            "version": settings.APP_VERSION,
        }

    return app


app = create_app()


# ── Admin seeder ───────────────────────────────────────────────────────────────
async def _seed_admin():
    """Create the initial superadmin account if it doesn't exist."""
    from app.db.session import AsyncSessionLocal
    from app.schemas.user import UserCreate
    from app.services.user_service import UserService
    from app.core.exceptions import ConflictError

    async with AsyncSessionLocal() as db:
        try:
            existing = await UserService.get_by_email(db, settings.FIRST_ADMIN_EMAIL)
            if existing:
                logger.info("Admin user already exists")
                return

            user = await UserService.create(
                db,
                UserCreate(
                    username=settings.FIRST_ADMIN_USERNAME,
                    email=settings.FIRST_ADMIN_EMAIL,
                    password=settings.FIRST_ADMIN_PASSWORD,
                    full_name="System Administrator",
                ),
            )
            user.is_admin = True
            user.is_verified = True
            await db.commit()
            logger.info(f"Admin user created: {settings.FIRST_ADMIN_EMAIL}")
        except ConflictError:
            logger.info("Admin user already exists (conflict)")
        except Exception as e:
            logger.error(f"Failed to seed admin user: {e}")
            await db.rollback()


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.is_development,
        workers=1 if settings.is_development else settings.WORKERS,
        log_level="debug" if settings.DEBUG else "info",
    )
