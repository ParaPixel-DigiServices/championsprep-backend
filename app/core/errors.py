"""
Custom exceptions and error handlers for the application.
Provides consistent error responses across the API.
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class AppException(Exception):
    """Base exception class for application errors."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(AppException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTHENTICATION_ERROR",
            details=details,
        )


class AuthorizationError(AppException):
    """Raised when user doesn't have permission."""

    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="AUTHORIZATION_ERROR",
            details=details,
        )


class NotFoundError(AppException):
    """Raised when resource is not found."""

    def __init__(self, resource: str = "Resource", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"{resource} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            details=details,
        )


class ValidationError(AppException):
    """Raised when validation fails."""

    def __init__(self, message: str = "Validation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class ConflictError(AppException):
    """Raised when resource already exists."""

    def __init__(self, resource: str = "Resource", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"{resource} already exists",
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT",
            details=details,
        )


class RateLimitError(AppException):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details,
        )


class ServiceUnavailableError(AppException):
    """Raised when external service is unavailable."""

    def __init__(self, service: str = "Service", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"{service} is currently unavailable",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="SERVICE_UNAVAILABLE",
            details=details,
        )


class DatabaseError(AppException):
    """Raised when database operation fails."""

    def __init__(self, message: str = "Database operation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR",
            details=details,
        )


class CacheError(AppException):
    """Raised when cache operation fails."""

    def __init__(self, message: str = "Cache operation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="CACHE_ERROR",
            details=details,
        )


class AIServiceError(AppException):
    """Raised when AI service operation fails."""

    def __init__(self, message: str = "AI service error", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="AI_SERVICE_ERROR",
            details=details,
        )


class EmailServiceError(AppException):
    """Raised when email service operation fails."""

    def __init__(self, message: str = "Email service error", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="EMAIL_SERVICE_ERROR",
            details=details,
        )


# ============================================================================
# ERROR RESPONSE FORMATTER
# ============================================================================

def create_error_response(
    message: str,
    status_code: int,
    error_code: str = "ERROR",
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create standardized error response.

    Args:
        message: Error message
        status_code: HTTP status code
        error_code: Application error code
        details: Optional additional details
        request_id: Optional request ID for tracking

    Returns:
        Error response dictionary
    """
    response = {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
            "status_code": status_code,
        },
    }

    if details:
        response["error"]["details"] = details

    if request_id:
        response["request_id"] = request_id

    return response


# ============================================================================
# ERROR HANDLERS
# ============================================================================

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Handle custom AppException instances.

    Args:
        request: FastAPI request
        exc: AppException instance

    Returns:
        JSON response with error details
    """
    request_id = request.headers.get("X-Request-ID")

    # Log error
    logger.error(
        f"{exc.error_code}: {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details,
            "path": request.url.path,
            "request_id": request_id,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            message=exc.message,
            status_code=exc.status_code,
            error_code=exc.error_code,
            details=exc.details,
            request_id=request_id,
        ),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle FastAPI HTTPException instances.

    Args:
        request: FastAPI request
        exc: HTTPException instance

    Returns:
        JSON response with error details
    """
    request_id = request.headers.get("X-Request-ID")

    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            message=exc.detail,
            status_code=exc.status_code,
            error_code="HTTP_ERROR",
            request_id=request_id,
        ),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Args:
        request: FastAPI request
        exc: RequestValidationError instance

    Returns:
        JSON response with validation error details
    """
    request_id = request.headers.get("X-Request-ID")

    # Format validation errors
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })

    logger.warning(
        f"Validation error on {request.url.path}",
        extra={
            "errors": errors,
            "request_id": request_id,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=create_error_response(
            message="Validation failed",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details={"errors": errors},
            request_id=request_id,
        ),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions.

    Args:
        request: FastAPI request
        exc: Exception instance

    Returns:
        JSON response with generic error message
    """
    request_id = request.headers.get("X-Request-ID")

    # Log unexpected error
    logger.error(
        f"Unexpected error: {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "request_id": request_id,
        },
    )

    # Don't expose internal errors in production
    message = "An unexpected error occurred"

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_ERROR",
            request_id=request_id,
        ),
    )


# ============================================================================
# REGISTER ERROR HANDLERS
# ============================================================================

def register_error_handlers(app) -> None:
    """
    Register all error handlers with FastAPI app.

    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Error handlers registered successfully")