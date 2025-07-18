"""Tests for base task classes and utilities."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from uuid import uuid4, UUID

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tasks.base import (
    BaseTask, TaskStatus, TaskResult, create_task_result,
    validate_task_input, get_task_timeout
)


class TestTaskStatus:
    """Test TaskStatus enumeration."""
    
    def test_task_status_values(self):
        """Test TaskStatus enum values."""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.PROCESSING == "processing"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.CANCELLED == "cancelled"
        assert TaskStatus.RETRYING == "retrying"


class TestTaskResult:
    """Test TaskResult model."""
    
    def test_task_result_creation(self):
        """Test TaskResult model creation."""
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
        assert isinstance(result.created_at, datetime)
        assert isinstance(result.updated_at, datetime)
    
    def test_task_result_defaults(self):
        """Test TaskResult model with default values."""
        task_id = str(uuid4())
        result = TaskResult(task_id=task_id, status=TaskStatus.PENDING)
        
        assert result.result is None
        assert result.error_message is None
        assert result.error_details is None
        assert result.processing_time is None
        assert result.retry_count == 0
        assert result.completed_at is None


class TestBaseTask:
    """Test BaseTask class functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.task = BaseTask()
        self.task.name = "test_task"
        self.task.request = Mock()
        self.task.request.retries = 0
        self.task_id = str(uuid4())
    
    def test_base_task_initialization(self):
        """Test BaseTask initialization."""
        task = BaseTask()
        assert task.start_time is None
        assert task.task_logger is None
        assert task.autoretry_for == (Exception,)
        assert task.retry_kwargs['max_retries'] == 3
        assert task.retry_kwargs['countdown'] == 60
    
    @patch('tasks.base.logger')
    def test_before_start(self, mock_logger):
        """Test before_start method."""
        mock_logger.bind.return_value = mock_logger
        
        args = ("arg1", "arg2")
        kwargs = {"key1": "value1", "key2": "value2"}
        
        with patch.object(self.task, 'update_task_status') as mock_update:
            self.task.before_start(self.task_id, args, kwargs)
        
        # Check that start time is set
        assert self.task.start_time is not None
        
        # Check that logger is bound
        mock_logger.bind.assert_called_once_with(
            task_id=self.task_id,
            task_name="test_task",
            args_count=2,
            kwargs_keys=["key1", "key2"]
        )
        
        # Check that status is updated
        mock_update.assert_called_once_with(self.task_id, TaskStatus.PROCESSING)
    
    @patch('time.time')
    def test_on_success(self, mock_time):
        """Test on_success method."""
        # Set up time mocking
        mock_time.side_effect = [100.0, 101.5]  # start_time, end_time
        self.task.start_time = 100.0
        
        retval = {"result": "success"}
        
        with patch.object(self.task, 'update_task_status') as mock_update:
            self.task.on_success(retval, self.task_id, [], {})
        
        # Check that status is updated with correct values
        mock_update.assert_called_once_with(
            self.task_id,
            TaskStatus.COMPLETED,
            result=retval,
            processing_time=1.5
        )
    
    def test_on_failure_final(self):
        """Test on_failure method for final failure."""
        self.task.request.retries = 3
        self.task.retry_kwargs = {'max_retries': 3}
        self.task.start_time = 100.0
        
        exc = ValueError("Test error")
        einfo = Mock()
        einfo.traceback = "traceback info"
        
        with patch.object(self.task, 'update_task_status') as mock_update:
            with patch('time.time', return_value=101.0):
                self.task.on_failure(exc, self.task_id, [], {}, einfo)
        
        # Check that status is updated as failed
        call_args = mock_update.call_args
        assert call_args[0][1] == TaskStatus.FAILED
        assert call_args[1]['error_message'] == "Test error"
        assert call_args[1]['processing_time'] == 1.0
    
    def test_on_failure_retry(self):
        """Test on_failure method for retry."""
        self.task.request.retries = 1
        self.task.retry_kwargs = {'max_retries': 3}
        
        exc = ConnectionError("Network error")
        einfo = Mock()
        einfo.traceback = "traceback info"
        
        with patch.object(self.task, 'update_task_status') as mock_update:
            self.task.on_failure(exc, self.task_id, [], {}, einfo)
        
        # Check that status is updated as retrying
        call_args = mock_update.call_args
        assert call_args[0][1] == TaskStatus.RETRYING
    
    def test_on_retry(self):
        """Test on_retry method."""
        self.task.request.retries = 1
        exc = ConnectionError("Network error")
        einfo = Mock()
        
        with patch.object(self.task, 'update_task_status') as mock_update:
            self.task.on_retry(exc, self.task_id, [], {}, einfo)
        
        # Check that status is updated as retrying
        mock_update.assert_called_once_with(
            self.task_id,
            TaskStatus.RETRYING,
            error_message="Retry 1: Network error"
        )
    
    @patch('tasks.base.TaskRepository')
    def test_update_task_status_success(self, mock_repo_class):
        """Test successful task status update."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        self.task.update_task_status(
            self.task_id,
            TaskStatus.COMPLETED,
            result={"key": "value"},
            processing_time=1.5
        )
        
        # Check that repository update is called
        mock_repo.update_task.assert_called_once()
        call_args = mock_repo.update_task.call_args
        
        # Check task ID
        assert call_args[0][0] == UUID(self.task_id)
        
        # Check update data
        update_data = call_args[0][1]
        assert update_data['status'] == 'completed'
        assert update_data['results'] == {"key": "value"}
        assert update_data['processing_time'] == 1.5
        assert 'updated_at' in update_data
        assert 'completed_at' in update_data
    
    @patch('tasks.base.TaskRepository')
    @patch('tasks.base.logger')
    def test_update_task_status_failure(self, mock_logger, mock_repo_class):
        """Test task status update failure handling."""
        mock_repo = Mock()
        mock_repo.update_task.side_effect = Exception("Database error")
        mock_repo_class.return_value = mock_repo
        
        # Should not raise exception
        self.task.update_task_status(self.task_id, TaskStatus.COMPLETED)
        
        # Check that error is logged
        mock_logger.error.assert_called_once()
    
    def test_should_retry_non_retryable(self):
        """Test should_retry with non-retryable exceptions."""
        non_retryable = [ValueError("Invalid input"), TypeError("Type error"), KeyError("Missing key")]
        
        for exc in non_retryable:
            assert not self.task.should_retry(exc)
    
    def test_should_retry_retryable(self):
        """Test should_retry with retryable exceptions."""
        retryable = [ConnectionError("Network error"), TimeoutError("Timeout"), OSError("OS error")]
        
        for exc in retryable:
            assert self.task.should_retry(exc)
    
    @patch('tasks.base.datetime')
    def test_apply_async_with_monitoring(self, mock_datetime):
        """Test apply_async_with_monitoring method."""
        mock_datetime.utcnow.return_value.isoformat.return_value = "2024-01-01T00:00:00"
        
        # Mock the apply_async method
        mock_result = Mock()
        mock_result.id = self.task_id
        
        with patch.object(self.task, 'apply_async', return_value=mock_result) as mock_apply:
            result = self.task.apply_async_with_monitoring(
                args=["arg1"], 
                kwargs={"key": "value"},
                queue="test_queue"
            )
        
        # Check that apply_async was called with enhanced options
        call_args = mock_apply.call_args
        assert 'headers' in call_args[1]
        assert 'correlation_id' in call_args[1]['headers']
        assert 'submitted_at' in call_args[1]['headers']
        
        assert result == mock_result


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_create_task_result(self):
        """Test create_task_result function."""
        task_id = str(uuid4())
        result = create_task_result(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            result={"key": "value"},
            processing_time=1.5,
            retry_count=2
        )
        
        assert isinstance(result, TaskResult)
        assert result.task_id == task_id
        assert result.status == TaskStatus.COMPLETED
        assert result.result == {"key": "value"}
        assert result.processing_time == 1.5
        assert result.retry_count == 2
        assert result.completed_at is not None
    
    def test_validate_task_input_success(self):
        """Test successful task input validation."""
        data = {
            "task_id": str(uuid4()),
            "file_url": "https://example.com/file.pdf",
            "user_id": "user123"
        }
        required_fields = ["task_id", "file_url", "user_id"]
        
        # Should not raise exception
        validate_task_input(data, required_fields)
    
    def test_validate_task_input_missing_fields(self):
        """Test task input validation with missing fields."""
        data = {"task_id": str(uuid4())}
        required_fields = ["task_id", "file_url", "user_id"]
        
        with pytest.raises(ValueError, match="Missing required fields"):
            validate_task_input(data, required_fields)
    
    def test_validate_task_input_invalid_uuid(self):
        """Test task input validation with invalid UUID."""
        data = {
            "task_id": "invalid-uuid",
            "file_url": "https://example.com/file.pdf"
        }
        required_fields = ["task_id", "file_url"]
        
        with pytest.raises(ValueError, match="Invalid task_id format"):
            validate_task_input(data, required_fields)
    
    @patch('tasks.base.worker_settings')
    def test_get_task_timeout(self, mock_settings):
        """Test get_task_timeout function."""
        mock_settings.processing_timeout_seconds = 300
        
        # Test specific task types
        assert get_task_timeout('archive_processing') == 300
        assert get_task_timeout('document_parsing') == 300
        assert get_task_timeout('vectorization') == 150  # half of processing timeout
        assert get_task_timeout('cleanup') == 60
        
        # Test unknown task type (should return default)
        assert get_task_timeout('unknown_task') == 300