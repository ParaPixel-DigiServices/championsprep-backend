"""
Logging configuration for the application.
Supports both JSON and text formats with file and console handlers.
"""

import logging
import sys
from pathlib import Path
from typing import Any
import json
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    Outputs logs in JSON format for easy parsing and analysis.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "ip_address"):
            log_data["ip_address"] = record.ip_address

        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """
    Colored console formatter for better readability in development.
    """

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            colored_levelname = (
                f"{self.COLORS[levelname]}{levelname:8}{self.RESET}"
            )
            record.levelname = colored_levelname

        # Format the message
        formatted = super().format(record)

        # Reset color at the end
        return formatted


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    log_file: str = "logs/app.log",
) -> None:
    """
    Setup application logging with file and console handlers.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ('json' or 'text')
        log_file: Path to log file
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler (always colored for readability)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))

    if log_format.lower() == "json":
        # Use colored formatter for console even in JSON mode
        console_formatter = ColoredFormatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        console_formatter = ColoredFormatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler (JSON format for production)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(getattr(logging, log_level.upper()))

    if log_format.lower() == "json":
        file_formatter = JSONFormatter()
    else:
        file_formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Set log levels for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# ============================================================================
# LOGGING UTILITIES
# ============================================================================

def log_request(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: str = None,
    ip_address: str = None,
) -> None:
    """
    Log HTTP request with structured data.

    Args:
        logger: Logger instance
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        user_id: Optional user ID
        ip_address: Optional client IP address
    """
    extra = {
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": duration_ms,
    }

    if user_id:
        extra["user_id"] = user_id
    if ip_address:
        extra["ip_address"] = ip_address

    logger.info(
        f"{method} {path} - {status_code} - {duration_ms:.2f}ms",
        extra=extra,
    )


def log_error(
    logger: logging.Logger,
    error: Exception,
    context: dict = None,
) -> None:
    """
    Log error with additional context.

    Args:
        logger: Logger instance
        error: Exception instance
        context: Optional context dictionary
    """
    error_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
    }

    if context:
        error_data.update(context)

    logger.error(
        f"{type(error).__name__}: {str(error)}",
        exc_info=True,
        extra=error_data,
    )


def log_security_event(
    logger: logging.Logger,
    event_type: str,
    user_id: str = None,
    ip_address: str = None,
    details: dict = None,
) -> None:
    """
    Log security-related events.

    Args:
        logger: Logger instance
        event_type: Type of security event
        user_id: Optional user ID
        ip_address: Optional client IP address
        details: Optional additional details
    """
    event_data = {
        "event_type": event_type,
        "security_event": True,
    }

    if user_id:
        event_data["user_id"] = user_id
    if ip_address:
        event_data["ip_address"] = ip_address
    if details:
        event_data.update(details)

    logger.warning(
        f"Security Event: {event_type}",
        extra=event_data,
    )