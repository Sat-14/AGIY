"""
Centralized Logging Configuration
Provides structured logging with context propagation across services
"""

import logging
import json
import sys
from datetime import datetime
from pythonjsonlogger import jsonlogger
import os


class StructuredLogger:
    """Manages structured JSON logging"""

    def __init__(self, service_name, log_level=None):
        """
        Initialize structured logger

        Args:
            service_name: Name of the microservice
            log_level: Logging level (default: INFO)
        """
        self.service_name = service_name
        self.log_level = log_level or os.getenv("LOG_LEVEL", "INFO")
        self.logger = None
        self._setup_logging()

    def _setup_logging(self):
        """Configure structured JSON logging"""

        # Create logger
        self.logger = logging.getLogger(self.service_name)
        self.logger.setLevel(getattr(logging, self.log_level.upper()))

        # Clear existing handlers
        self.logger.handlers.clear()

        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, self.log_level.upper()))

        # Use JSON formatter for structured logs
        log_format = '%(timestamp)s %(level)s %(service)s %(trace_id)s %(span_id)s %(message)s'

        formatter = CustomJsonFormatter(log_format)
        formatter.service_name = self.service_name
        console_handler.setFormatter(formatter)

        self.logger.addHandler(console_handler)

        # Optional: File handler for persistent logs
        if os.getenv("LOG_TO_FILE", "false").lower() == "true":
            log_dir = os.getenv("LOG_DIR", "logs")
            os.makedirs(log_dir, exist_ok=True)

            file_handler = logging.FileHandler(
                f"{log_dir}/{self.service_name}.log"
            )
            file_handler.setLevel(getattr(logging, self.log_level.upper()))
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def get_logger(self):
        """Get configured logger instance"""
        return self.logger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional context"""

    service_name = "unknown"

    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)

        # Add timestamp
        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'

        # Add service name
        log_record['service'] = self.service_name

        # Add log level
        log_record['level'] = record.levelname

        # Add trace context (from OpenTelemetry if available)
        try:
            from opentelemetry import trace
            span = trace.get_current_span()
            if span:
                span_context = span.get_span_context()
                log_record['trace_id'] = format(span_context.trace_id, '032x')
                log_record['span_id'] = format(span_context.span_id, '016x')
            else:
                log_record['trace_id'] = None
                log_record['span_id'] = None
        except ImportError:
            log_record['trace_id'] = None
            log_record['span_id'] = None

        # Add source location
        log_record['filename'] = record.filename
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno

        # Environment
        log_record['environment'] = os.getenv('ENVIRONMENT', 'development')


def log_api_request(logger, method, endpoint, params=None, headers=None):
    """
    Log API request details

    Args:
        logger: Logger instance
        method: HTTP method
        endpoint: API endpoint
        params: Request parameters
        headers: Request headers (sensitive data filtered)
    """
    logger.info(
        "API Request",
        extra={
            'event': 'api_request',
            'method': method,
            'endpoint': endpoint,
            'params': params or {},
            'headers': _filter_sensitive_headers(headers or {})
        }
    )


def log_api_response(logger, method, endpoint, status_code, duration):
    """
    Log API response details

    Args:
        logger: Logger instance
        method: HTTP method
        endpoint: API endpoint
        status_code: HTTP status code
        duration: Request duration in seconds
    """
    logger.info(
        "API Response",
        extra={
            'event': 'api_response',
            'method': method,
            'endpoint': endpoint,
            'status_code': status_code,
            'duration_seconds': duration
        }
    )


def log_agent_call(logger, source_agent, target_agent, endpoint, payload=None):
    """
    Log inter-agent communication

    Args:
        logger: Logger instance
        source_agent: Source agent name
        target_agent: Target agent name
        endpoint: API endpoint
        payload: Request payload (sensitive data filtered)
    """
    logger.info(
        "Agent Call",
        extra={
            'event': 'agent_call',
            'source_agent': source_agent,
            'target_agent': target_agent,
            'endpoint': endpoint,
            'payload': _filter_sensitive_data(payload or {})
        }
    )


def log_db_operation(logger, collection, operation, document_id=None, duration=None):
    """
    Log database operations

    Args:
        logger: Logger instance
        collection: Collection name
        operation: Operation type (insert, update, delete, find)
        document_id: Document identifier
        duration: Operation duration
    """
    logger.info(
        "Database Operation",
        extra={
            'event': 'db_operation',
            'collection': collection,
            'operation': operation,
            'document_id': str(document_id) if document_id else None,
            'duration_seconds': duration
        }
    )


def log_business_event(logger, event_type, user_id=None, details=None):
    """
    Log business events

    Args:
        logger: Logger instance
        event_type: Type of business event
        user_id: User identifier
        details: Event details
    """
    logger.info(
        "Business Event",
        extra={
            'event': 'business_event',
            'event_type': event_type,
            'user_id': user_id,
            'details': details or {}
        }
    )


def log_error(logger, error, context=None):
    """
    Log errors with context

    Args:
        logger: Logger instance
        error: Exception object
        context: Additional context
    """
    logger.error(
        f"Error: {str(error)}",
        extra={
            'event': 'error',
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {}
        },
        exc_info=True
    )


def _filter_sensitive_headers(headers):
    """Filter sensitive information from headers"""
    sensitive_keys = ['authorization', 'api-key', 'x-api-key', 'cookie']
    filtered = {}
    for key, value in headers.items():
        if key.lower() in sensitive_keys:
            filtered[key] = '***REDACTED***'
        else:
            filtered[key] = value
    return filtered


def _filter_sensitive_data(data):
    """Filter sensitive information from payload"""
    if not isinstance(data, dict):
        return data

    sensitive_keys = ['password', 'api_key', 'secret', 'token', 'credit_card']
    filtered = {}

    for key, value in data.items():
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            filtered[key] = '***REDACTED***'
        elif isinstance(value, dict):
            filtered[key] = _filter_sensitive_data(value)
        else:
            filtered[key] = value

    return filtered
