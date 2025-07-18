"""Main FastAPI application with middleware and routing configuration."""

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Any

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings, validate_required_settings
from .database.connection import get_database_health
from .api.v1 import api_router
from .monitoring.logging import (
    configure_logging, RequestTracker, error_tracker, metrics_collector,
    request_id_var, user_id_var
)
from .monitoring.observability import start_monitoring, stop_monitoring, performance_monitor

# Configure logging first
configure_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("Starting Document Intelligence & Parsing Center API")
    
    try:
        # Validate configuration
        validate_required_settings()
        logger.info("Configuration validation passed")
        
        # Check database connectivity
        db_health = await get_database_health()
        if not db_health["healthy"]:
            logger.error("Database health check failed", error=db_health["error"])
            raise RuntimeError("Database connection failed")
        
        logger.info("Database connection established")
        
        # Start monitoring services
        start_monitoring()
        logger.info("Monitoring services started")
        
    except Exception as e:
        logger.error("Startup failed", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Document Intelligence & Parsing Center API")
    
    # Stop monitoring services
    stop_monitoring()
    logger.info("Monitoring services stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="Document Intelligence & Parsing Center",
        description="A comprehensive document processing system leveraging multi-modal LLMs",
        version="1.3.0",
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        lifespan=lifespan
    )
    
    # Add middleware
    setup_middleware(app)
    
    # Add exception handlers
    setup_exception_handlers(app)
    
    # Include API routes
    app.include_router(api_router, prefix="/v1")
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Basic health check endpoint."""
        return {
            "status": "healthy",
            "service": "dipc-api",
            "version": "1.3.0",
            "timestamp": time.time()
        }
    
    return app


def setup_middleware(app: FastAPI) -> None:
    """Configure application middleware."""
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Trusted host middleware for production
    if settings.environment == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"]  # Configure with actual allowed hosts in production
        )
    
    # Request logging and observability middleware
    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):
        """Log all HTTP requests with structured logging and observability."""
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Extract user ID from headers if available
        user_id = request.headers.get("X-User-ID")
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Use request tracker for correlation
        with RequestTracker(request_id=request_id, user_id=user_id):
            # Log request start
            logger.info(
                "Request started",
                method=request.method,
                url=str(request.url),
                client_ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
            
            try:
                response = await call_next(request)
                
                # Calculate processing time
                process_time = time.time() - start_time
                
                # Record metrics
                performance_monitor.record_api_request(
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    duration=process_time
                )
                
                # Log successful response
                logger.info(
                    "Request completed",
                    method=request.method,
                    url=str(request.url),
                    status_code=response.status_code,
                    process_time=process_time,
                )
                
                # Add request ID to response headers
                response.headers["X-Request-ID"] = request_id
                
                return response
                
            except Exception as e:
                process_time = time.time() - start_time
                
                # Record error metrics
                performance_monitor.record_api_request(
                    method=request.method,
                    path=request.url.path,
                    status_code=500,
                    duration=process_time
                )
                
                # Log error with context
                error_tracker.log_error(
                    e,
                    context={
                        "method": request.method,
                        "url": str(request.url),
                        "process_time": process_time
                    },
                    category="api_request"
                )
                
                raise


def setup_exception_handlers(app: FastAPI) -> None:
    """Configure global exception handlers."""
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions with structured error responses."""
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        
        logger.warning(
            "HTTP exception",
            request_id=request_id,
            status_code=exc.status_code,
            detail=exc.detail,
            url=str(request.url),
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": f"HTTP_{exc.status_code}",
                "error_message": exc.detail,
                "request_id": request_id,
                "timestamp": time.time(),
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors."""
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        
        logger.warning(
            "Validation error",
            request_id=request_id,
            errors=exc.errors(),
            url=str(request.url),
        )
        
        return JSONResponse(
            status_code=422,
            content={
                "error_code": "VALIDATION_ERROR",
                "error_message": "Request validation failed",
                "details": exc.errors(),
                "request_id": request_id,
                "timestamp": time.time(),
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        
        logger.error(
            "Unexpected error",
            request_id=request_id,
            error=str(exc),
            error_type=type(exc).__name__,
            url=str(request.url),
            exc_info=True,
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_SERVER_ERROR",
                "error_message": "An unexpected error occurred",
                "request_id": request_id,
                "timestamp": time.time(),
            }
        )


# Create the application instance
app = create_app()