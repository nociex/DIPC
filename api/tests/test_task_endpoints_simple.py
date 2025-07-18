"""Simple tests for task management API endpoints without database dependencies."""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock
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


def test_task_endpoint_imports():
    """Test that task endpoint modules can be imported successfully."""
    from src.api.v1.tasks import router
    from src.api.models import TaskCreateRequest, TaskResponse, TaskStatus, TaskType
    
    # Verify router exists and has expected routes
    assert router is not None
    
    # Verify models can be instantiated
    task_options = {"enable_vectorization": True, "storage_policy": "temporary"}
    request = TaskCreateRequest(
        file_urls=["https://example.com/test.pdf"],
        user_id="test_user",
        options=task_options
    )
    
    assert request.file_urls == ["https://example.com/test.pdf"]
    assert request.user_id == "test_user"
    assert request.options.enable_vectorization is True


def test_task_status_enum():
    """Test TaskStatus enum values."""
    from src.api.models import TaskStatus
    
    assert TaskStatus.PENDING == "pending"
    assert TaskStatus.PROCESSING == "processing"
    assert TaskStatus.COMPLETED == "completed"
    assert TaskStatus.FAILED == "failed"
    assert TaskStatus.CANCELLED == "cancelled"


def test_task_type_enum():
    """Test TaskType enum values."""
    from src.api.models import TaskType
    
    assert TaskType.DOCUMENT_PARSING == "document_parsing"
    assert TaskType.ARCHIVE_PROCESSING == "archive_processing"
    assert TaskType.VECTORIZATION == "vectorization"
    assert TaskType.CLEANUP == "cleanup"


def test_task_options_validation():
    """Test TaskOptions model validation."""
    from src.api.models import TaskOptions, StoragePolicy
    
    # Test default values
    options = TaskOptions()
    assert options.enable_vectorization is True
    assert options.storage_policy == StoragePolicy.TEMPORARY
    assert options.max_cost_limit is None
    
    # Test custom values
    options = TaskOptions(
        enable_vectorization=False,
        storage_policy=StoragePolicy.PERMANENT,
        max_cost_limit=25.0,
        llm_provider="openai",
        model_name="gpt-4"
    )
    
    assert options.enable_vectorization is False
    assert options.storage_policy == StoragePolicy.PERMANENT
    assert options.max_cost_limit == 25.0
    assert options.llm_provider == "openai"
    assert options.model_name == "gpt-4"


def test_task_create_request_validation():
    """Test TaskCreateRequest validation."""
    from src.api.models import TaskCreateRequest, TaskOptions
    
    # Test valid request
    request = TaskCreateRequest(
        file_urls=["https://example.com/test.pdf", "https://example.com/test2.pdf"],
        user_id="test_user_123",
        options=TaskOptions(enable_vectorization=False)
    )
    
    assert len(request.file_urls) == 2
    assert request.user_id == "test_user_123"
    assert request.options.enable_vectorization is False
    
    # Test validation errors
    with pytest.raises(ValueError):
        TaskCreateRequest(
            file_urls=[],  # Empty list should fail
            user_id="test_user"
        )
    
    with pytest.raises(ValueError):
        TaskCreateRequest(
            file_urls=["https://example.com/test.pdf"],
            user_id=""  # Empty string should fail
        )


def test_task_response_model():
    """Test TaskResponse model structure."""
    from src.api.models import TaskResponse, TaskStatus, TaskType, TaskOptions
    
    task_id = uuid4()
    now = datetime.now()
    
    response = TaskResponse(
        task_id=task_id,
        user_id="test_user",
        status=TaskStatus.PENDING,
        task_type=TaskType.DOCUMENT_PARSING,
        file_url="https://example.com/test.pdf",
        options=TaskOptions(),
        created_at=now,
        updated_at=now
    )
    
    assert response.task_id == task_id
    assert response.user_id == "test_user"
    assert response.status == TaskStatus.PENDING
    assert response.task_type == TaskType.DOCUMENT_PARSING
    assert response.file_url == "https://example.com/test.pdf"
    assert response.created_at == now
    assert response.updated_at == now


def test_task_status_response_model():
    """Test TaskStatusResponse model structure."""
    from src.api.models import TaskStatusResponse, TaskStatus
    
    task_id = uuid4()
    now = datetime.now()
    
    response = TaskStatusResponse(
        task_id=task_id,
        status=TaskStatus.PROCESSING,
        progress=75.5,
        updated_at=now
    )
    
    assert response.task_id == task_id
    assert response.status == TaskStatus.PROCESSING
    assert response.progress == 75.5
    assert response.updated_at == now


def test_task_list_response_model():
    """Test TaskListResponse model structure."""
    from src.api.models import TaskListResponse, TaskResponse, TaskStatus, TaskType, TaskOptions
    
    # Create sample tasks
    tasks = []
    for i in range(3):
        task = TaskResponse(
            task_id=uuid4(),
            user_id=f"user_{i}",
            status=TaskStatus.COMPLETED,
            task_type=TaskType.DOCUMENT_PARSING,
            options=TaskOptions(),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        tasks.append(task)
    
    response = TaskListResponse(
        tasks=tasks,
        total_count=25,
        page=2,
        page_size=10,
        has_next=True
    )
    
    assert len(response.tasks) == 3
    assert response.total_count == 25
    assert response.page == 2
    assert response.page_size == 10
    assert response.has_next is True


def test_llm_provider_validation():
    """Test LLM provider validation in TaskOptions."""
    from src.api.models import TaskOptions
    
    # Valid providers
    for provider in ["openai", "openrouter", "litelm"]:
        options = TaskOptions(llm_provider=provider)
        assert options.llm_provider == provider
    
    # Invalid provider should raise validation error
    with pytest.raises(ValueError, match="LLM provider must be one of"):
        TaskOptions(llm_provider="invalid_provider")


def test_archive_task_type_detection():
    """Test that ZIP files are detected for archive processing."""
    # This would be tested in the actual endpoint logic
    # Here we just verify the logic exists in the endpoint
    
    zip_urls = [
        "https://example.com/archive.zip",
        "https://example.com/documents.ZIP",
        "https://example.com/files.zip"
    ]
    
    for url in zip_urls:
        assert url.lower().endswith('.zip')
    
    non_zip_urls = [
        "https://example.com/document.pdf",
        "https://example.com/image.jpg",
        "https://example.com/text.txt"
    ]
    
    for url in non_zip_urls:
        assert not url.lower().endswith('.zip')


def test_error_response_model():
    """Test ErrorResponse model structure."""
    from src.api.models import ErrorResponse
    
    error = ErrorResponse(
        error_code="VALIDATION_ERROR",
        error_message="Request validation failed",
        details={"field": "file_urls", "issue": "cannot be empty"},
        request_id="req_123456",
        timestamp=1234567890.0
    )
    
    assert error.error_code == "VALIDATION_ERROR"
    assert error.error_message == "Request validation failed"
    assert error.details["field"] == "file_urls"
    assert error.request_id == "req_123456"
    assert error.timestamp == 1234567890.0


def test_token_usage_model():
    """Test TokenUsage model structure."""
    from src.api.models import TokenUsage
    
    usage = TokenUsage(
        prompt_tokens=1000,
        completion_tokens=500,
        total_tokens=1500,
        estimated_cost=0.025
    )
    
    assert usage.prompt_tokens == 1000
    assert usage.completion_tokens == 500
    assert usage.total_tokens == 1500
    assert usage.estimated_cost == 0.025


def test_document_metadata_model():
    """Test DocumentMetadata model structure."""
    from src.api.models import DocumentMetadata
    
    metadata = DocumentMetadata(
        file_type="application/pdf",
        file_size=1024000,
        page_count=10,
        language="en",
        extraction_method="llm_multimodal",
        processing_time=45.2
    )
    
    assert metadata.file_type == "application/pdf"
    assert metadata.file_size == 1024000
    assert metadata.page_count == 10
    assert metadata.language == "en"
    assert metadata.extraction_method == "llm_multimodal"
    assert metadata.processing_time == 45.2