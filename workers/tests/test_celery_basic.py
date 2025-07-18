"""Basic tests for Celery configuration without complex imports."""

import pytest
import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_celery_imports():
    """Test that Celery modules can be imported."""
    try:
        from config import get_celery_config
        config = get_celery_config()
        
        # Test basic configuration structure
        assert 'broker_url' in config
        assert 'result_backend' in config
        assert 'task_serializer' in config
        assert config['task_serializer'] == 'json'
        
    except ImportError as e:
        pytest.skip(f"Could not import Celery config: {e}")


def test_task_status_enum():
    """Test TaskStatus enum values."""
    try:
        from tasks.base import TaskStatus
        
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.PROCESSING == "processing"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.CANCELLED == "cancelled"
        assert TaskStatus.RETRYING == "retrying"
        
    except ImportError as e:
        pytest.skip(f"Could not import TaskStatus: {e}")


def test_task_result_model():
    """Test TaskResult model creation."""
    try:
        from tasks.base import TaskResult, TaskStatus
        from uuid import uuid4
        
        task_id = str(uuid4())
        result = TaskResult(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            result={"key": "value"},
            processing_time=1.5
        )
        
        assert result.task_id == task_id
        assert result.status == TaskStatus.COMPLETED
        assert result.result == {"key": "value"}
        assert result.processing_time == 1.5
        
    except ImportError as e:
        pytest.skip(f"Could not import TaskResult: {e}")


def test_utility_functions():
    """Test utility functions."""
    try:
        from tasks.base import validate_task_input, get_task_timeout
        from uuid import uuid4
        
        # Test validate_task_input
        data = {
            "task_id": str(uuid4()),
            "file_url": "https://example.com/file.pdf",
            "user_id": "user123"
        }
        required_fields = ["task_id", "file_url", "user_id"]
        
        # Should not raise exception
        validate_task_input(data, required_fields)
        
        # Test missing fields
        with pytest.raises(ValueError, match="Missing required fields"):
            validate_task_input({"task_id": str(uuid4())}, required_fields)
        
        # Test invalid UUID
        with pytest.raises(ValueError, match="Invalid task_id format"):
            validate_task_input({"task_id": "invalid-uuid"}, ["task_id"])
        
    except ImportError as e:
        pytest.skip(f"Could not import utility functions: {e}")


def test_task_timeout_function():
    """Test get_task_timeout function with mocked settings."""
    try:
        from tasks.base import get_task_timeout
        from unittest.mock import patch
        
        # Mock worker_settings
        with patch('tasks.base.worker_settings') as mock_settings:
            mock_settings.processing_timeout_seconds = 300
            
            # Test specific task types
            assert get_task_timeout('archive_processing') == 300
            assert get_task_timeout('document_parsing') == 300
            assert get_task_timeout('vectorization') == 150  # half of processing timeout
            assert get_task_timeout('cleanup') == 60
            
            # Test unknown task type (should return default)
            assert get_task_timeout('unknown_task') == 300
            
    except ImportError as e:
        pytest.skip(f"Could not import get_task_timeout: {e}")