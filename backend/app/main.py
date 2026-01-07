import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError, TimeoutError as SQLAlchemyTimeoutError

from app.core.config import get_settings
from app.core.rate_limit import RateLimitMiddleware
from app.api.router import api_router
from app.cache.redis_client import init_redis, close_redis
from app.db.session import AsyncSessionLocal

settings = get_settings()
logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Initialize Sentry for error tracking (if configured)
if settings.sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=0.1 if settings.environment == "production" else 1.0,
            send_default_pii=False,
        )
        logger.info("Sentry error tracking initialized")
    except ImportError:
        logger.warning("sentry-sdk not installed, error tracking disabled")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events with validation."""
    # Startup validation
    logger.info(f"Starting {settings.app_name} in {settings.environment} mode...")

    # Validate critical configuration in production
    if settings.environment == "production":
        if not settings.redis_url:
            logger.warning("Redis URL not configured - caching disabled")
        if not settings.apns_key_id:
            logger.warning("APNs not configured - push notifications disabled")

    # Initialize Redis
    await init_redis()

    # Test database connectivity
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        if settings.environment == "production":
            raise RuntimeError(f"Cannot start without database: {e}")

    yield

    # Shutdown
    await close_redis()
    logger.info(f"Shutting down {settings.app_name}...")


app = FastAPI(
    title=settings.app_name,
    description="API for Orest's Journal pet health tracking app",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Database-specific error handlers
@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Handle database constraint violations."""
    logger.error(f"Database constraint violation: {exc}", extra={
        "path": request.url.path,
        "method": request.method,
    })
    return JSONResponse(
        status_code=409,
        content={"detail": "Resource conflict - item may already exist or violates constraints"}
    )


@app.exception_handler(OperationalError)
async def operational_error_handler(request: Request, exc: OperationalError):
    """Handle database operational errors (connection issues, etc.)."""
    logger.error(f"Database operational error: {exc}", extra={
        "path": request.url.path,
        "method": request.method,
    })
    return JSONResponse(
        status_code=503,
        content={"detail": "Database temporarily unavailable, please retry"}
    )


@app.exception_handler(SQLAlchemyTimeoutError)
async def timeout_error_handler(request: Request, exc: SQLAlchemyTimeoutError):
    """Handle database timeout errors."""
    logger.error(f"Database timeout: {exc}", extra={
        "path": request.url.path,
        "method": request.method,
    })
    return JSONResponse(
        status_code=504,
        content={"detail": "Request timed out, please retry"}
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unexpected exceptions."""
    logger.error(
        f"Unhandled exception: {exc}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
    )
    # Report to Sentry if configured
    if settings.sentry_dsn:
        try:
            import sentry_sdk
            sentry_sdk.capture_exception(exc)
        except Exception:
            pass

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware (60 requests/minute per IP)
app.add_middleware(RateLimitMiddleware, requests_per_minute=60, burst_limit=10)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Railway/load balancers."""
    return {"status": "healthy"}
