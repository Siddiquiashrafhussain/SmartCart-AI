"""
SmartCart AI - FastAPI Application Gateway
Main entry point for REST APIs, middleware, and database lifecycle.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from backend.app.core.config import settings
from backend.app.core.database import engine, SessionLocal
from backend.app.core.logging import logger
from backend.app.models import Base
from backend.app.schemas.common import HealthResponse, ErrorResponse
from backend.app.api.v1.router import api_v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown events.
    Initializes database tables on startup.
    """
    logger.info("Initializing SmartCart AI database schema...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")
        raise e

    logger.info(f"SmartCart AI backend started on port {settings.APP_PORT} (env={settings.APP_ENV})")
    yield
    logger.info("Shutting down SmartCart AI backend...")


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Multimodal Retail Intelligence & Loss Prevention Platform",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handlers
@app.exception_handler(Exception)
async def global_unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected server error occurred. Please contact system support.",
            "details": str(exc) if settings.DEBUG else None
        }
    )


# Health & Liveness Probe
@app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """
    Service liveness and database connectivity verification probe.
    """
    db_status = "connected"
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = f"unhealthy: {str(e)}"

    return HealthResponse(
        status="ok" if "unhealthy" not in db_status else "degraded",
        app_name=settings.APP_NAME,
        environment=settings.APP_ENV,
        database_status=db_status,
        timestamp=datetime.now(timezone.utc)
    )


# Register API v1 Routes
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


@app.get("/", include_in_schema=False)
def root():
    return {
        "project": "SmartCart AI",
        "tagline": "Shop Smarter. Verify Instantly. Restock Proactively.",
        "documentation": "/docs",
        "health": "/api/v1/health"
    }
