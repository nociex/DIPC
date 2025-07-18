"""Tests for task management API endpoints."""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
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

from src.main import create_app
from src.api.models import TaskCreateRequest, TaskOptions, TaskStatus, TaskType


@pytest.fixture
def app():
    """Create test FastAPI app."""
    with patch('src.config.validate_required_settings'), \
         patch('src.database.connection.get_database_health'):
        return create_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_task_repo():
    """Mock task repository."""
    return AsyncMock()


@pytest.fixture
def sample_task_data():
    """Sample task data for testing."""
    task_id = uuid4()
    return {
        "id": task_id,
        "user_id": "test_user",
        "parent_task_id": None,
        "status": TaskStatus.PENDING.value,
        "task_type": TaskType.DOCUMENT_PARSING.value,
        "file_url": "https://example.com/test.pdf",
        "options": {"enable_vectorization": True, "storage_policy": "temporary"},
        "estimated_cost": None,
        "actual_cost": None,
        "results": None,
        "error_message": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "completed_at": None,
        "token_usage": None,
        "metadata": None
    }


class TestTaskCreation:
    """Test task creation endpoint."""
    
    @patch('src.api.v1.tasks.TaskRepository')
    def test_create_task_success(self, mock_repo_class, client, sample_task_data):
        """Test successful task creation."""
        # Setup mock
        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        
        # Create mock task object
        mock_task = type('Task', (), sample_task_data)
        mock_repo.create.return_value = mock_task
        
        # Test data
        request_data = {
            "file_urls": ["https://example.com/test.pdf"],
            "user_id": "test_user",
            "options": {
                "enable_vectorization": True,
                "storage_policy": "temporary"
            }
        }
        
        # Make request
        response = client.post("/v1/tasks", json=request_data)
        
        # Assertions
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == "test_user"
        assert data["status"] == "pending"
        assert data["task_type"] == "document_parsing"
    
    def test_create_task_validation_error(self, client):
        """Test task creation with validation errors."""
        # Invalid request data (missing required fields)
        request_data = {
            "file_urls": [],  # Empty list should fail validation
            "user_id": ""     # Empty string should fail validation
        }
        
        response = client.post("/v1/tasks", json=request_data)
        
        # Should return validation error
        assert response.status_code == 422
        data = response.json()
        assert data["error_code"] == "VALIDATION_ERROR"
    
    @patch('src.api.v1.tasks.TaskRepository')
    def test_create_task_archive_type(self, mock_repo_class, client, sample_task_data):
        """Test task creation with ZIP file (archive processing)."""
        # Setup mock
        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        
        # Update sample data for archive processing
        sample_task_data["task_type"] = TaskType.ARCHIVE_PROCESSING.value
        mock_task = type('Task', (), sample_task_data)
        mock_repo.create.return_value = mock_task
        
        # Test data with ZIP file
        request_data = {
            "file_urls": ["https://example.com/archive.zip"],
            "user_id": "test_user",
            "options": {
                "enable_vectorization": False,
                "storage_policy": "permanent"
            }
        }
        
        response = client.post("/v1/tasks", json=request_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["task_type"] == "archive_processing"


class TestTaskRetrieval:
    """Test task retrieval endpoints."""
    
    @patch('src.api.v1.tasks.TaskRepository')
    def test_get_task_success(self, mock_repo_class, client, sample_task_data):
        """Test successful task retrieval."""
        # Setup mock
        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        
        mock_task = type('Task', (), sample_task_data)
        mock_repo.get_by_id.return_value = mock_task
        
        task_id = sample_task_data["id"]
        response = client.get(f"/v1/tasks/{task_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == str(task_id)
        assert data["user_id"] == "test_user"
    
    @patch('src.api.v1.tasks.TaskRepository')
    def test_get_task_not_found(self, mock_repo_class, client):
        """Test task retrieval when task doesn't exist."""
        # Setup mock
        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_by_id.return_value = None
        
        task_id = uuid4()
        response = client.get(f"/v1/tasks/{task_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    @patch('src.api.v1.tasks.TaskRepository')
    def test_get_task_status_success(self, mock_repo_class, client, sample_task_data):
        """Test successful task status retrieval."""
        # Setup mock
        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        
        mock_task = type('Task', (), sample_task_data)
        mock_repo.get_by_id.return_value = mock_task
        
        task_id = sample_task_data["id"]
        response = client.get(f"/v1/tasks/{task_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == str(task_id)
        assert data["status"] == "pending"
        assert data["progress"] == 0.0
    
    @patch('src.api.v1.tasks.TaskRepository')
    def test_get_task_status_processing(self, mock_repo_class, client, sample_task_data):
        """Test task status retrieval for processing task."""
        # Setup mock
        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        
        # Update task to processing status
        sample_task_data["status"] = TaskStatus.PROCESSING.value
        mock_task = type('Task', (), sample_task_data)
        mock_repo.get_by_id.return_value = mock_task
        
        task_id = sample_task_data["id"]
        response = client.get(f"/v1/tasks/{task_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert data["progress"] == 50.0
        assert data["estimated_completion_time"] is not None


class TestTaskListing:
    """Test task listing endpoint."""
    
    @patch('src.api.v1.tasks.TaskRepository')
    def test_list_tasks_success(self, mock_repo_class, client, sample_task_data):
        """Test successful task listing."""
        # Setup mock
        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        
        # Create multiple mock tasks
        mock_tasks = [type('Task', (), sample_task_data) for _ in range(3)]
        mock_repo.list_with_pagination.return_value = (mock_tasks, 3)
        
        response = client.get("/v1/tasks")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 3
        assert data["total_count"] == 3
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["has_next"] is False
    
    @patch('src.api.v1.tasks.TaskRepository')
    def test_list_tasks_with_filters(self, mock_repo_class, client, sample_task_data):
        """Test task listing with filters."""
        # Setup mock
        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        
        mock_tasks = [type('Task', (), sample_task_data)]
        mock_repo.list_with_pagination.return_value = (mock_tasks, 1)
        
        response = client.get("/v1/tasks?user_id=test_user&status=pending&page=1&page_size=10")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 1
        assert data["page"] == 1
        assert data["page_size"] == 10
        
        # Verify repository was called with correct filters
        mock_repo.list_with_pagination.assert_called_once()
        call_args = mock_repo.list_with_pagination.call_args
        assert call_args[1]["filters"]["user_id"] == "test_user"
        assert call_args[1]["filters"]["status"] == "pending"
    
    def test_list_tasks_invalid_status(self, client):
        """Test task listing with invalid status filter."""
        response = client.get("/v1/tasks?status=invalid_status")
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid status" in data["detail"]
    
    @patch('src.api.v1.tasks.TaskRepository')
    def test_list_tasks_pagination(self, mock_repo_class, client, sample_task_data):
        """Test task listing pagination."""
        # Setup mock
        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        
        # Simulate 25 total tasks, requesting page 2 with page_size 10
        mock_tasks = [type('Task', (), sample_task_data) for _ in range(10)]
        mock_repo.list_with_pagination.return_value = (mock_tasks, 25)
        
        response = client.get("/v1/tasks?page=2&page_size=10")
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 10
        assert data["total_count"] == 25
        assert data["has_next"] is True  # Should have page 3


class TestErrorHandling:
    """Test error handling in task endpoints."""
    
    @patch('src.api.v1.tasks.TaskRepository')
    def test_create_task_database_error(self, mock_repo_class, client):
        """Test task creation with database error."""
        # Setup mock to raise exception
        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.create.side_effect = Exception("Database connection failed")
        
        request_data = {
            "file_urls": ["https://example.com/test.pdf"],
            "user_id": "test_user"
        }
        
        response = client.post("/v1/tasks", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to create task" in data["detail"]
    
    @patch('src.api.v1.tasks.TaskRepository')
    def test_get_task_database_error(self, mock_repo_class, client):
        """Test task retrieval with database error."""
        # Setup mock to raise exception
        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_by_id.side_effect = Exception("Database connection failed")
        
        task_id = uuid4()
        response = client.get(f"/v1/tasks/{task_id}")
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to retrieve task" in data["detail"]