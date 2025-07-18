"""Centralized logging configuration and utilities."""

import logging
import sys
import time
import uuid
from typing import Dict, Any, Optional
from contextvars import ContextVar
import structlog
from structlog.types import EventDict, Processor
import json

from ..config import settings

# Context variables for request tracing
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
task_id_var: ContextVar[Optional[str]] = ContextVar('task_id', default=None)


def add_request_context(logger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add request context to log entries."""
    request_id = request_id_var.get()
    user_id = user_id_var.get()
    task_id = task_id_var.get()
    
    if request_id:
        event_dict['request_id'] = request_id
    if user_id:
        event_dict['user_id'] = user_id
    if task_id:
        event_dict['task_id'] = task_id
    
    return event_dict


def add_service_context(logger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add service context to log entries."""
    event_dict['service'] = 'dipc-api'
    event_dict['version'] = '1.3.0'
    event_dict['environment'] = settings.environment
    return event_dict


def add_performance_metrics(logger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add performance metrics to log entries."""
    # Add timestamp if not present
    if 'timestamp' not in event_dict:
        event_dict['timestamp'] = time.time()
    
    return event_dict


def filter_sensitive_data(logger, method_name: str, event_dict: EventDict) -> EventDict:
    """Filter sensitive data from log entries."""
    sensitive_keys = [
        'password', 'token', 'api_key', 'secret', 'authorization',
        'cookie', 'session', 'csrf_token', 'private_key'
    ]
    
    def _filter_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively filter sensitive data from dictionaries."""
        filtered = {}
        for key, value in data.items():
            if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
                filtered[key] = '[REDACTED]'
            elif isinstance(value, dict):
                filtered[key] = _filter_dict(value)
            elif isinstance(value, list):
                filtered[key] = [_filter_dict(item) if isinstance(item, dict) else item for item in value]
            else:
                filtered[key] = value
        return filtered
    
    # Filter the entire event dict
    for key, value in list(event_dict.items()):
        if isinstance(value, dict):
            event_dict[key] = _filter_dict(value)
        elif any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
            event_dict[key] = '[REDACTED]'
    
    return event_dict


def configure_logging():
    """Configure structured logging for the application."""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper())
    )
    
    # Configure processors based on environment
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        add_service_context,
        add_request_context,
        add_performance_metrics,
        filter_sensitive_data,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Add appropriate renderer based on environment
    if settings.environment == "development":
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


class RequestTracker:
    """Context manager for tracking requests with correlation IDs."""
    
    def __init__(self, request_id: Optional[str] = None, user_id: Optional[str] = None, task_id: Optional[str] = None):
        self.request_id = request_id or str(uuid.uuid4())
        self.user_id = user_id
        self.task_id = task_id
        self.start_time = time.time()
        
        # Store previous context values
        self.prev_request_id = None
        self.prev_user_id = None
        self.prev_task_id = None
    
    def __enter__(self):
        """Enter request tracking context."""
        # Store previous values
        self.prev_request_id = request_id_var.get()
        self.prev_user_id = user_id_var.get()
        self.prev_task_id = task_id_var.get()
        
        # Set new values
        request_id_var.set(self.request_id)
        if self.user_id:
            user_id_var.set(self.user_id)
        if self.task_id:
            task_id_var.set(self.task_id)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit request tracking context."""
        # Restore previous values
        request_id_var.set(self.prev_request_id)
        user_id_var.set(self.prev_user_id)
        task_id_var.set(self.prev_task_id)
        
        # Log request completion
        duration = time.time() - self.start_time
        logger = structlog.get_logger(__name__)
        
        if exc_type:
            logger.error(
                "Request completed with error",
                duration=duration,
                error_type=exc_type.__name__ if exc_type else None,
                error_message=str(exc_val) if exc_val else None
            )
        else:
            logger.info(
                "Request completed successfully",
                duration=duration
            )


class TaskTracker:
    """Context manager for tracking task execution."""
    
    def __init__(self, task_id: str, task_type: str, user_id: Optional[str] = None):
        self.task_id = task_id
        self.task_type = task_type
        self.user_id = user_id
        self.start_time = time.time()
        self.logger = structlog.get_logger(__name__)
        
        # Store previous context values
        self.prev_task_id = None
        self.prev_user_id = None
    
    def __enter__(self):
        """Enter task tracking context."""
        # Store previous values
        self.prev_task_id = task_id_var.get()
        self.prev_user_id = user_id_var.get()
        
        # Set new values
        task_id_var.set(self.task_id)
        if self.user_id:
            user_id_var.set(self.user_id)
        
        self.logger.info(
            "Task started",
            task_type=self.task_type
        )
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit task tracking context."""
        # Restore previous values
        task_id_var.set(self.prev_task_id)
        user_id_var.set(self.prev_user_id)
        
        # Log task completion
        duration = time.time() - self.start_time
        
        if exc_type:
            self.logger.error(
                "Task failed",
                task_type=self.task_type,
                duration=duration,
                error_type=exc_type.__name__ if exc_type else None,
                error_message=str(exc_val) if exc_val else None
            )
        else:
            self.logger.info(
                "Task completed successfully",
                task_type=self.task_type,
                duration=duration
            )


class PerformanceLogger:
    """Utility for logging performance metrics."""
    
    def __init__(self, operation_name: str, logger: Optional[structlog.BoundLogger] = None):
        self.operation_name = operation_name
        self.logger = logger or structlog.get_logger(__name__)
        self.start_time = None
        self.metrics = {}
    
    def start(self):
        """Start performance tracking."""
        self.start_time = time.time()
        self.logger.debug(
            "Operation started",
            operation=self.operation_name
        )
    
    def add_metric(self, name: str, value: Any):
        """Add a custom metric."""
        self.metrics[name] = value
    
    def finish(self, success: bool = True, error: Optional[str] = None):
        """Finish performance tracking and log results."""
        if self.start_time is None:
            self.logger.warning("Performance tracking not started", operation=self.operation_name)
            return
        
        duration = time.time() - self.start_time
        
        log_data = {
            "operation": self.operation_name,
            "duration": duration,
            "success": success,
            **self.metrics
        }
        
        if error:
            log_data["error"] = error
        
        if success:
            self.logger.info("Operation completed", **log_data)
        else:
            self.logger.error("Operation failed", **log_data)


class ErrorTracker:
    """Utility for tracking and categorizing errors."""
    
    def __init__(self, logger: Optional[structlog.BoundLogger] = None):
        self.logger = logger or structlog.get_logger(__name__)
    
    def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        severity: str = "error",
        category: Optional[str] = None
    ):
        """Log an error with context and categorization."""
        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "severity": severity,
        }
        
        if category:
            error_data["error_category"] = category
        
        if context:
            error_data["context"] = context
        
        # Add stack trace for debugging
        if settings.environment == "development":
            import traceback
            error_data["stack_trace"] = traceback.format_exc()
        
        self.logger.error("Error occurred", **error_data)
    
    def log_validation_error(self, error: Exception, field: str, value: Any):
        """Log validation errors."""
        self.log_error(
            error,
            context={"field": field, "value": str(value)},
            category="validation"
        )
    
    def log_external_service_error(self, error: Exception, service: str, operation: str):
        """Log external service errors."""
        self.log_error(
            error,
            context={"service": service, "operation": operation},
            category="external_service"
        )
    
    def log_database_error(self, error: Exception, query: Optional[str] = None):
        """Log database errors."""
        context = {}
        if query:
            context["query"] = query
        
        self.log_error(
            error,
            context=context,
            category="database"
        )


class MetricsCollector:
    """Utility for collecting application metrics."""
    
    def __init__(self, logger: Optional[structlog.BoundLogger] = None):
        self.logger = logger or structlog.get_logger(__name__)
    
    def log_api_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        user_id: Optional[str] = None
    ):
        """Log API request metrics."""
        self.logger.info(
            "API request",
            metric_type="api_request",
            method=method,
            path=path,
            status_code=status_code,
            duration=duration,
            user_id=user_id
        )
    
    def log_task_metrics(
        self,
        task_type: str,
        status: str,
        duration: float,
        file_size: Optional[int] = None,
        processing_cost: Optional[float] = None
    ):
        """Log task processing metrics."""
        metrics = {
            "metric_type": "task_processing",
            "task_type": task_type,
            "status": status,
            "duration": duration
        }
        
        if file_size:
            metrics["file_size"] = file_size
        if processing_cost:
            metrics["processing_cost"] = processing_cost
        
        self.logger.info("Task metrics", **metrics)
    
    def log_resource_usage(
        self,
        cpu_percent: float,
        memory_percent: float,
        disk_percent: float
    ):
        """Log system resource usage."""
        self.logger.info(
            "Resource usage",
            metric_type="resource_usage",
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_percent=disk_percent
        )


# Global instances
error_tracker = ErrorTracker()
metrics_collector = MetricsCollector()


def get_correlation_id() -> Optional[str]:
    """Get current request correlation ID."""
    return request_id_var.get()


def get_user_id() -> Optional[str]:
    """Get current user ID from context."""
    return user_id_var.get()


def get_task_id() -> Optional[str]:
    """Get current task ID from context."""
    return task_id_var.get()


def create_child_logger(name: str, **context) -> structlog.BoundLogger:
    """Create a child logger with additional context."""
    logger = structlog.get_logger(name)
    return logger.bind(**context)


# Initialize logging configuration
configure_logging()