"""
Advanced logging configuration with BetterStack (Logtail) integration.
Provides structured logging with context and automatic error tracking.
"""

import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict
from pythonjsonlogger.json import JsonFormatter
import requests
from functools import wraps

from .config import get_settings

settings = get_settings()


class BetterStackHandler(logging.Handler):
    """
    Custom logging handler that sends logs to BetterStack (Logtail).
    """

    def __init__(self, source_token: str, ingesting_host: str):
        super().__init__()
        self.source_token = source_token
        self.ingesting_host = ingesting_host
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {source_token}",
                "Content-Type": "application/json",
            }
        )

    def emit(self, record: logging.LogRecord) -> None:
        """Send log record to BetterStack."""
        try:
            log_entry = self.format(record)

            # Parse the JSON log entry
            if isinstance(log_entry, str):
                log_data = json.loads(log_entry)
            else:
                log_data = log_entry

            # BetterStack expects the log in a specific format
            # The message should be in the 'message' field, and other fields in 'dt' (data)
            payload = {
                "message": log_data.get("message", ""),
                "dt": log_data.get("timestamp", datetime.utcnow().isoformat() + "Z"),
                "level": log_data.get("level", "INFO").lower(),
                **log_data,  # Include all other fields
            }

            # Send to BetterStack - correct endpoint format
            url = f"https://{self.ingesting_host}/"
            response = self.session.post(url, json=payload, timeout=5)
            response.raise_for_status()

        except Exception as e:
            # Don't let logging errors break the application
            print(f"Failed to send log to BetterStack: {e}", file=sys.stderr)


class StructuredFormatter(JsonFormatter):
    """
    JSON formatter with additional context and metadata.
    """

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO format
        log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Add log level
        log_record["level"] = record.levelname

        # Add environment information
        log_record["environment"] = settings.environment
        log_record["api_version"] = settings.api_version

        # Add Vercel information if available
        if settings.is_vercel:
            log_record["platform"] = "vercel"

        # Add exception info if present
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        # Extract and flatten context data for better visibility in logs
        if hasattr(record, "context"):
            context = getattr(record, "context")
            if isinstance(context, dict):
                # Extract correlation_id to top level for better visibility
                if "correlation_id" in context:
                    log_record["correlation_id"] = context["correlation_id"]

                # Extract other important fields to top level
                important_fields = [
                    "invalid_value",
                    "param_name",
                    "error_type",
                    "query_params",
                    "validation_errors",
                    "status_code",
                    "path",
                    "method",
                    "data_inicial",
                    "data_final",
                ]

                for field in important_fields:
                    if field in context:
                        log_record[field] = context[field]

                # Keep full context for reference
                log_record["context"] = context

        # Format message to include correlation_id and key data if available
        original_message = log_record.get("message", "")
        correlation_id = log_record.get("correlation_id")

        if correlation_id:
            # Add correlation_id to message for easier searching
            log_record["message"] = f"[{correlation_id}] {original_message}"

        # Add invalid data to message if present
        if "invalid_value" in log_record and "param_name" in log_record:
            param_info = (
                f" | {log_record['param_name']}='{log_record['invalid_value']}'"
            )
            log_record["message"] = log_record["message"] + param_info


def setup_logging() -> logging.Logger:
    """
    Configure logging for the application.

    Returns:
        logging.Logger: Configured logger instance
    """
    # Get the configured log level from settings
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Get root logger
    logger = logging.getLogger("apikey_management")
    logger.setLevel(log_level)  # Use configured level from .env
    logger.propagate = False  # Don't propagate to root logger

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler with structured logging (always enabled)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)  # Use same level as logger

    # Use readable formatting for console (development style)
    class ContextFormatter(logging.Formatter):
        def format(self, record):
            # Extract correlation_id from context if available
            correlation_id = ""
            context = getattr(record, "context", None)
            if context and isinstance(context, dict):
                cid = context.get("correlation_id")
                if cid:
                    correlation_id = f"[{cid[:8]}] "

            # Add correlation_id to the message
            original_format = self._style._fmt
            if correlation_id:
                self._style._fmt = original_format.replace(
                    "%(message)s", f"{correlation_id}%(message)s"
                )

            result = super().format(record)
            self._style._fmt = original_format
            return result

    console_formatter = ContextFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Add BetterStack handler ONLY in production (not dev/development)
    if settings.betterstack_enabled and settings.environment.lower() not in ['dev', 'development']:
        try:
            # Ensure we have a valid token
            token = settings.betterstack_source_token
            if token is not None:
                betterstack_handler = BetterStackHandler(
                    source_token=token,
                    ingesting_host=settings.betterstack_ingesting_host,
                )
                betterstack_handler.setLevel(logging.DEBUG)
                betterstack_formatter = StructuredFormatter(
                    "%(timestamp)s %(level)s %(name)s %(message)s"
                )
                betterstack_handler.setFormatter(betterstack_formatter)
                logger.addHandler(betterstack_handler)
                
                # Log usando o formato legível do console
                logger.info(
                    "BetterStack logging enabled",
                    extra={"context": {"host": settings.betterstack_ingesting_host}},
                )
        except Exception as e:
            logger.warning(f"Failed to setup BetterStack handler: {e}")

    # File handler if log_file is specified
    if settings.log_file:
        file_handler = logging.FileHandler(settings.log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Logger name (usually __name__)

    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(f"apikey_management.{name}")


def log_with_context(
    logger: logging.Logger, level: str, message: str, **context
) -> None:
    """
    Log a message with additional context.

    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **context: Additional context key-value pairs
    """
    log_func = getattr(logger, level.lower())
    log_func(message, extra={"context": context})


def log_request(func):
    """
    Decorator to log API requests with timing and context.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)

        # Extract request info if available
        request_context = {"function": func.__name__, "module": func.__module__}

        # Check if first arg is a Request object
        if args and hasattr(args[0], "method"):
            request = args[0]
            request_context.update(
                {
                    "method": request.method,
                    "path": request.url.path,
                    "client": request.client.host if request.client else None,
                }
            )

        start_time = datetime.utcnow()

        try:
            result = await func(*args, **kwargs)

            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()
            request_context["duration_seconds"] = duration

            log_with_context(
                logger,
                "info",
                (
                    f"Request completed: "
                    f"{request_context.get('method', 'UNKNOWN')} "
                    f"{request_context.get('path', func.__name__)}"
                ),
                **request_context,
            )

            return result

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            request_context["duration_seconds"] = duration
            request_context["error"] = str(e)
            request_context["error_type"] = type(e).__name__

            log_with_context(
                logger,
                "error",
                (
                    f"Request failed: "
                    f"{request_context.get('method', 'UNKNOWN')} "
                    f"{request_context.get('path', func.__name__)}"
                ),
                **request_context,
            )

            raise

    return wrapper


# Initialize logging on module import
app_logger = setup_logging()
