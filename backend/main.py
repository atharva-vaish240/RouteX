"""NER-LINK FastAPI application entrypoint."""

import asyncio
import contextlib
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.health import router as health_router
from backend.api.v1.router import api_v1_router
from backend.config import get_settings
from backend.database import check_database_connection, check_redis_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("nerlink.main")

settings = get_settings()

# Keep-alive configuration to prevent Render free-tier spin-down
KEEP_ALIVE_ENABLED = os.getenv("KEEP_ALIVE_ENABLED", "true").lower() in ("1", "true", "yes")
KEEP_ALIVE_INTERVAL_SECONDS = int(os.getenv("KEEP_ALIVE_INTERVAL_SECONDS", str(13 * 60)))  # 13 minutes
KEEP_ALIVE_URL = os.getenv(
    "KEEP_ALIVE_URL",
    os.getenv("RENDER_EXTERNAL_URL", "https://routex-l2wr.onrender.com").rstrip("/") + "/health/live",
)


async def keep_alive_ping_loop(
    url: str = KEEP_ALIVE_URL,
    interval_seconds: int = KEEP_ALIVE_INTERVAL_SECONDS,
    initial_delay_seconds: int = 45,
) -> None:
    """Background task that periodically sends an HTTP GET request to Render's public URL.

    Render free-tier instances spin down after 15 minutes of inactivity. Pinging
    the external URL every 13 minutes routes traffic through Render's public load
    balancer, resetting the idle countdown and keeping the service warm.
    """
    logger.info(
        f"Keep-alive job started. Target: {url} (interval: {interval_seconds // 60}m, initial delay: {initial_delay_seconds}s)"
    )
    try:
        # Allow the application to finish binding and serving before the first external request
        await asyncio.sleep(initial_delay_seconds)
        async with httpx.AsyncClient(timeout=15.0) as client:
            while True:
                try:
                    response = await client.get(url)
                    logger.info(f"Keep-alive ping to {url} succeeded: HTTP {response.status_code}")
                except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                    logger.warning(f"Keep-alive ping to {url} failed: {exc}")
                except Exception as exc:
                    logger.warning(f"Unexpected keep-alive error: {exc}")

                await asyncio.sleep(interval_seconds)
    except asyncio.CancelledError:
        logger.info("Keep-alive task cancelled during shutdown.")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown procedures."""
    logger.info(f"Starting {settings.APP_NAME} in '{settings.APP_ENV}' mode...")
    logger.info(f"Corridor configured: {settings.CORRIDOR_NAME} {settings.corridor_bbox}")

    # Inspect initial connectivity
    db_health = await check_database_connection()
    logger.info(f"PostgreSQL status: {db_health.get('status')}, PostGIS: {db_health.get('has_postgis')}")
    redis_health = await check_redis_connection()
    logger.info(f"Redis status: {redis_health.get('status')}")

    # Ensure administrator account exists if credentials are provided in environment (.env)
    admin_password = settings.ADMIN_PASSWORD or settings.ADMIN_BOOTSTRAP_PASSWORD
    if settings.ADMIN_EMAIL and admin_password:
        try:
            from backend.scripts.bootstrap_admin import bootstrap_admin
            result = await bootstrap_admin(
                email=settings.ADMIN_EMAIL,
                full_name=settings.ADMIN_NAME,
                password=admin_password,
                reset_password=False,
                is_interactive=False,
            )
            logger.info(f"Administrator account '{settings.ADMIN_EMAIL}' status: {result['action']}")
        except Exception as exc:
            logger.warning(f"Administrator environment bootstrap check skipped: {exc}")

    # Start real-time event broadcaster and Redis Streams consumer
    from backend.services.sse_broadcaster import get_sse_broadcaster
    broadcaster = get_sse_broadcaster()
    await broadcaster.start()

    # Launch keep-alive background task
    keep_alive_task: asyncio.Task | None = None
    if KEEP_ALIVE_ENABLED and KEEP_ALIVE_URL:
        keep_alive_task = asyncio.create_task(keep_alive_ping_loop())

    yield

    # Gracefully shut down keep-alive task
    if keep_alive_task and not keep_alive_task.done():
        keep_alive_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await keep_alive_task

    await broadcaster.stop()
    logger.info(f"Shutting down {settings.APP_NAME}...")


def create_app() -> FastAPI:
    """Creates and configures the FastAPI application."""
    app = FastAPI(
        title="NER-LINK API",
        description=(
            "Logistics Accessibility Intelligence Platform for the North Eastern Region. "
            "Provides road accessibility intelligence, disruption management, and routable road graph APIs."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Cross-Origin Resource Sharing
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoints at root level
    app.include_router(health_router)

    # Versioned API routes
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": "0.1.0",
            "environment": settings.APP_ENV,
            "docs": "/docs",
            "corridor": {
                "name": settings.CORRIDOR_NAME,
                "bbox": {
                    "south": settings.CORRIDOR_MIN_LAT,
                    "west": settings.CORRIDOR_MIN_LON,
                    "north": settings.CORRIDOR_MAX_LAT,
                    "east": settings.CORRIDOR_MAX_LON,
                },
            },
            "attribution": "Road network data © OpenStreetMap contributors under ODbL",
        }

    return app


app = create_app()
