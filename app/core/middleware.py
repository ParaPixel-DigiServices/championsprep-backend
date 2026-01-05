"""
Middleware configuration for the FastAPI application.
Includes CORS, request ID tracking, timing, and security headers.
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# REQUEST ID MIDDLEWARE
# ============================================================================

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add unique request ID to each request.
    Useful for tracking and debugging.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Add request ID to request state
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


# ============================================================================
# TIMING MIDDLEWARE
# ============================================================================

class TimingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track request processing time.
    Adds X-Process-Time header to response.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate processing time
        process_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        # Add timing header
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

        # Log slow requests (> 1 second)
        if process_time > 1000:
            logger.warning(
                f"Slow request detected: {request.method} {request.url.path} - {process_time:.2f}ms",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "duration_ms": process_time,
                }
            )

        return response


# ============================================================================
# SECURITY HEADERS MIDDLEWARE
# ============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to responses.
    Helps protect against common web vulnerabilities.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Add security headers
        security_headers = {
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            # Enable XSS protection
            "X-XSS-Protection": "1; mode=block",
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            # Permissions policy (disable unnecessary features)
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }

        # Add Content Security Policy (CSP)
        if settings.is_production:
            security_headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' https://api.supabase.co;"
            )

        # Add headers to response
        for header, value in security_headers.items():
            response.headers[header] = value

        return response


# ============================================================================
# LOGGING MIDDLEWARE
# ============================================================================

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests and responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get request details
        request_id = getattr(request.state, "request_id", "unknown")
        start_time = time.time()

        # Log request
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_host": request.client.host if request.client else None,
            }
        )

        # Process request
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                }
            )

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            # Log error
            logger.error(
                f"Request failed: {request.method} {request.url.path} - {str(e)}",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                }
            )
            raise


# ============================================================================
# CORS MIDDLEWARE CONFIGURATION
# ============================================================================

def configure_cors(app) -> None:
    """
    Configure CORS middleware for the application.

    Args:
        app: FastAPI application instance
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=settings.ALLOW_CREDENTIALS,
        allow_methods=settings.ALLOWED_METHODS,
        allow_headers=settings.ALLOWED_HEADERS,
        expose_headers=["X-Request-ID", "X-Process-Time"],
        max_age=3600,  # Cache preflight requests for 1 hour
    )

    logger.info(
        f"CORS configured with origins: {', '.join(settings.ALLOWED_ORIGINS[:3])}{'...' if len(settings.ALLOWED_ORIGINS) > 3 else ''}"
    )


# ============================================================================
# TRUSTED HOST MIDDLEWARE
# ============================================================================

def configure_trusted_hosts(app) -> None:
    """
    Configure trusted host middleware for production.

    Args:
        app: FastAPI application instance
    """
    if settings.is_production:
        # Extract hosts from allowed origins
        allowed_hosts = []
        for origin in settings.ALLOWED_ORIGINS:
            # Extract host from URL
            if "://" in origin:
                host = origin.split("://")[1].split(":")[0]
                allowed_hosts.append(host)

        if allowed_hosts:
            app.add_middleware(
                TrustedHostMiddleware,
                allowed_hosts=allowed_hosts
            )
            logger.info(f"Trusted host middleware configured with: {', '.join(allowed_hosts)}")


# ============================================================================
# REGISTER ALL MIDDLEWARE
# ============================================================================

def register_middleware(app) -> None:
    """
    Register all middleware with the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    # Security headers (first for all responses)
    app.add_middleware(SecurityHeadersMiddleware)

    # Request ID tracking
    app.add_middleware(RequestIDMiddleware)

    # Timing tracking
    app.add_middleware(TimingMiddleware)

    # Logging (last to capture everything)
    if settings.DEBUG:
        app.add_middleware(LoggingMiddleware)

    # CORS configuration
    configure_cors(app)

    # Trusted hosts (production only)
    configure_trusted_hosts(app)

    logger.info("All middleware registered successfully")