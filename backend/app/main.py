"""SeedArr - Intelligent Seeding Manager."""
import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger

from app.config import settings
from app.database import init_db, close_db, async_session_maker
from app.api import api_router
from app.services.scheduler import scheduler
from app.models.settings import DEFAULT_SETTINGS
from app.models import Settings

# Determine log directory
LOG_DIR = Path("/app/data") if Path("/app/data").exists() else Path("data")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configure loguru
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG" if settings.debug else "INFO",
)
logger.add(
    LOG_DIR / "seedarr.log",
    rotation="10 MB",
    retention="7 days",
    level="DEBUG" if settings.debug else "INFO",
)


async def init_default_settings():
    """Initialize default settings if not present."""
    async with async_session_maker() as db:
        from sqlalchemy import select

        for key, value in DEFAULT_SETTINGS.items():
            result = await db.execute(select(Settings).where(Settings.key == key))
            if not result.scalar_one_or_none():
                db.add(Settings(key=key, value=value))
        await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Initialize default settings
    await init_default_settings()
    logger.info("Default settings initialized")

    # Set up scheduler database session factory
    scheduler.set_db_session_factory(async_session_maker)

    # Start scheduler
    async with async_session_maker() as db:
        from sqlalchemy import select

        result = await db.execute(select(Settings).where(Settings.key == "scan_interval_minutes"))
        setting = result.scalar_one_or_none()
        interval = setting.value if setting else DEFAULT_SETTINGS["scan_interval_minutes"]

    await scheduler.start(interval_minutes=interval)
    logger.info(f"Scheduler started with {interval} minute interval")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await scheduler.stop()
    await close_db()
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Intelligent Seeding Manager for qBittorrent",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")

# Check for static files directory (Docker single-container build)
STATIC_DIR = Path("/app/static")
if STATIC_DIR.exists():
    # Serve static files
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the SPA for all non-API routes."""
        # Check if file exists in static directory
        file_path = STATIC_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        # Return index.html for SPA routing
        return FileResponse(STATIC_DIR / "index.html")
else:
    @app.get("/")
    async def root():
        """Root endpoint - redirect to frontend or return API info."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "api_docs": "/docs",
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
