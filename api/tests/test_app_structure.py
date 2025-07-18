"""Tests for FastAPI application structure without external dependencies."""

import pytest
from unittest.mock import patch, MagicMock
import os

# Set test environment before importing modules
os.environ.update({
    'DATABASE_URL': 'postgresql://test:test@localhost:5432/test_dipc',
    'REDIS_URL': 'redis://localhost:6379/0',
    'CELERY_BROKER_URL': 'redis://localhost:6379/0',
    'CELERY_RESULT_BACKEND': 'redis://localhost:6379/0',
    'S3_ENDPOINT_URL': 'http://localhost:9000',
    'S3_ACCESS_KEY_ID': 'test_access_key',
    'S3_SECRET_ACCESS_KEY': 'test_secret_key',
    'S3_BUCKET_NAME': 'test-dipc-storage',
    'SECRET_KEY': 'test_secret_key_for_testing_only',
    'JWT_SECRET_KEY': 'test_jwt_secret_key_for_testing_only',
    'ENVIRONMENT': 'development',
    'LOG_LEVEL': 'INFO',
    'CORS_ORIGINS': 'http://localhost:3000',
    'OPENAI_API_KEY': 'test_openai_key'
})


def test_config_loading():
    """Test that configuration loads correctly."""
    from src.config import settings
    
    assert settings.database_url == 'postgresql://test:test@localhost:5432/test_dipc'
    assert settings.environment == 'development'
    assert settings.log_level == 'INFO'
    assert 'http://localhost:3000' in settings.cors_origins


def test_pydantic_models():
    """Test that Pydantic models are properly defined."""
    from src.api.models import (
        TaskCreateRequest, TaskResponse, TaskOptions, 
        PresignedUrlRequest, HealthResponse
    )
    
    # Test TaskOptions model
    options = TaskOptions()
    assert options.enable_vectorization is True
    assert options.storage_policy == "temporary"
    
    # Test PresignedUrlRequest validation
    with pytest.raises(ValueError):
        PresignedUrlRequest(
            filename="",
            content_type="application/pdf",
            file_size=1000
        )
    
    # Test valid PresignedUrlRequest
    request = PresignedUrlRequest(
        filename="test.pdf",
        content_type="application/pdf",
        file_size=1000
    )
    assert request.filename == "test.pdf"
    assert request.content_type == "application/pdf"


def test_app_creation():
    """Test that FastAPI app can be created."""
    # Import the create_app function to test basic structure
    from src.main import create_app
    
    # Test that the function exists and can be called
    # (We'll skip actual app creation due to dependency requirements)
    assert callable(create_app)
    
    # Test that the main module has the expected structure
    import src.main
    assert hasattr(src.main, 'create_app')
    assert hasattr(src.main, 'setup_middleware')
    assert hasattr(src.main, 'setup_exception_handlers')


def test_api_router_structure():
    """Test that API router structure is properly configured."""
    from src.api.v1 import api_router
    
    # Check that router has the expected routes
    route_paths = [route.path for route in api_router.routes]
    
    # Should have task-related routes
    assert any("tasks" in path for path in route_paths)
    assert any("upload" in path for path in route_paths)
    assert any("health" in path for path in route_paths)


def test_error_response_model():
    """Test error response model structure."""
    from src.api.models import ErrorResponse
    
    error = ErrorResponse(
        error_code="TEST_ERROR",
        error_message="Test error message",
        request_id="test-request-id",
        timestamp=1234567890.0
    )
    
    assert error.error_code == "TEST_ERROR"
    assert error.error_message == "Test error message"
    assert error.request_id == "test-request-id"
    assert error.timestamp == 1234567890.0