"""
Main FastAPI application entry point.
Configures and initializes the application with all middleware, routers, and settings.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import logging

from app.core.config import settings, print_settings_summary
from app.core.logging import setup_logging
from app.core.errors import register_error_handlers
from app.core.middleware import register_middleware

# Initialize logging
setup_logging(
    log_level=settings.LOG_LEVEL,
    log_format=settings.LOG_FORMAT,
    log_file=settings.LOG_FILE,
)

logger = logging.getLogger(__name__)


# ============================================================================
# LIFESPAN EVENT HANDLERS
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for startup and shutdown events.
    Replaces deprecated @app.on_event decorators.
    """
    # ========================================================================
    # STARTUP
    # ========================================================================
    logger.info("Starting application...")

    # Print settings summary
    print_settings_summary()

    # Initialize Sentry if enabled
    if settings.SENTRY_ENABLED and settings.SENTRY_DSN:
        try:
            import sentry_sdk
            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                environment=settings.SENTRY_ENVIRONMENT,
                traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
                integrations=[],
            )
            logger.info("Sentry initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {str(e)}")

    # Initialize database connections
    try:
        from app.db.supabase import initialize_database
        initialize_database()
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

    # Initialize Redis
    try:
        from app.db.redis import initialize_redis
        await initialize_redis()
    except Exception as e:
        logger.warning(f"Redis initialization failed: {str(e)}")
        # Redis is not critical, continue without it

    logger.info("Application startup complete")

    yield

    # ========================================================================
    # SHUTDOWN
    # ========================================================================
    logger.info("Shutting down application...")

    # Close database connections
    try:
        from app.db.supabase import close_database_connections
        await close_database_connections()
    except Exception as e:
        logger.error(f"Error closing database: {str(e)}")

    # Close Redis connections
    try:
        from app.db.redis import close_redis
        await close_redis()
    except Exception as e:
        logger.error(f"Error closing Redis: {str(e)}")

    logger.info("Application shutdown complete")


# ============================================================================
# CREATE FASTAPI APPLICATION
# ============================================================================

def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Production-grade FastAPI backend for StudyZen educational platform",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # Register error handlers
    register_error_handlers(app)

    # Register middleware
    register_middleware(app)

    # TODO: Register API routers
    # from app.api.router import api_router
    # app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


# ============================================================================
# APPLICATION INSTANCE
# ============================================================================

app = create_application()


# ============================================================================
# ROOT ENDPOINTS
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint - API health check.

    Returns:
        JSON response with API status
    """
    return JSONResponse(
        content={
            "success": True,
            "message": "StudyZen API is running",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "docs": f"{settings.API_V1_PREFIX}/docs" if settings.DEBUG else None,
        }
    )


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.

    Returns:
        JSON response with health status
    """
    return JSONResponse(
        content={
            "status": "healthy",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        }
    )


@app.get("/ping", tags=["Health"])
async def ping():
    """
    Simple ping endpoint for quick health checks.

    Returns:
        Plain text "pong"
    """
    return "pong"


# ============================================================================
# DEVELOPMENT INFO
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting development server...")

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=settings.DEBUG,
    )