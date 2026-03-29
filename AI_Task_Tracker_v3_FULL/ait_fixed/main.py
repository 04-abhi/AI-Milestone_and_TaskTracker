"""
AI Task Tracker v3 — Main Entry Point
Run: python main.py
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.scheduler import start_scheduler, stop_scheduler
from app.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    print(f"\n{'='*55}")
    print(f"  {settings.APP_NAME}  v3.0")
    print(f"  Running at  http://{settings.HOST}:{settings.PORT}")
    print(f"  API Docs:   http://{settings.HOST}:{settings.PORT}/api/docs")
    print(f"{'='*55}\n")

    await init_db()
    print("✓ Database ready")

    await _seed_admin()

    start_scheduler()
    print("✓ Scheduler started\n")

    yield

    stop_scheduler()
    print("Goodbye!")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="3.0.0",
        docs_url="/api/docs",
        redoc_url=None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes first
    app.include_router(api_router)

    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")

    if os.path.exists(frontend_dir):
        # Static assets
        css_dir = os.path.join(frontend_dir, "css")
        js_dir  = os.path.join(frontend_dir, "js")
        img_dir = os.path.join(frontend_dir, "img")

        if os.path.exists(css_dir):
            app.mount("/css", StaticFiles(directory=css_dir), name="css")
        if os.path.exists(js_dir):
            app.mount("/js",  StaticFiles(directory=js_dir),  name="js")
        if os.path.exists(img_dir):
            app.mount("/img", StaticFiles(directory=img_dir), name="img")

        index = os.path.join(frontend_dir, "index.html")

        # Service worker — must be served from root scope
        @app.get("/sw.js", include_in_schema=False)
        async def service_worker():
            return FileResponse(
                os.path.join(frontend_dir, "sw.js"),
                media_type="application/javascript",
                headers={"Service-Worker-Allowed": "/"},
            )

        # Health check (before SPA catch-all)
        @app.get("/health", include_in_schema=False)
        async def health():
            return {"status": "ok", "version": "3.0.0"}

        # Root → always serve index.html (SPA)
        @app.get("/", include_in_schema=False)
        async def root():
            return FileResponse(index)

        # ── SPA catch-all ────────────────────────────────────────────
        # Any path that isn't /api/... or a static asset → index.html
        # This lets the browser handle hash-based routing (#dashboard etc.)
        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa(full_path: str):
            # Let API requests fall through to 404
            if full_path.startswith("api/"):
                from fastapi import HTTPException
                raise HTTPException(status_code=404)
            # Static assets that don't exist → 404
            for prefix in ("css/", "js/", "img/"):
                if full_path.startswith(prefix):
                    from fastapi import HTTPException
                    raise HTTPException(status_code=404)
            # Everything else → SPA index
            return FileResponse(index)

    return app


app = create_app()


async def _seed_admin():
    from app.db.session import AsyncSessionLocal
    from app.services.user_service import create_user
    from app.schemas.user import UserRegister
    from sqlalchemy import select
    from app.models.user import User

    async with AsyncSessionLocal() as db:
        existing = await db.scalar(
            select(User).where(User.email == settings.FIRST_ADMIN_EMAIL)
        )
        if existing:
            return
        try:
            user = await create_user(db, UserRegister(
                username=settings.FIRST_ADMIN_USERNAME,
                email=settings.FIRST_ADMIN_EMAIL,
                password=settings.FIRST_ADMIN_PASSWORD,
                full_name="Administrator",
            ))
            user.is_admin = True
            await db.commit()
            print(f"✓ Admin created: {settings.FIRST_ADMIN_EMAIL}")
        except Exception as e:
            print(f"  Admin already exists: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.is_dev,
    )
