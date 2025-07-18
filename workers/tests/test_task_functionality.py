"""Tests for task functionality and integration."""

import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestTaskIntegration:
    """Test task integration and functionality."""
    
    def test_task_creation_and_execution(self):
        """Test that tasks can be created and have proper structure."""
        try:
            from tasks.archive import process_archive_task
            from tasks.parsing import parse_document_task
            from tasks.vectorization import vectorize_content_task
            from tasks.cleanup import cleanup_temporary_files_task
            
            # Test that tasks are properly registered
            assert hasattr(process_archive_task, 'name')
            assert hasattr(parse_document_task, 'name')
            assert hasattr(vectorize_content_task, 'name')
            assert hasattr(cleanup_temporary_files_task, 'name')
            
            # Test task names
            assert process_archive_task.name == 'workers.tasks.archive.process_archive_task'
            assert parse_document_task.name == 'workers.tasks.parsing.parse_document_task'
            assert vectorize_content_task.name == 'workers.tasks.vectorization.vectorize_content_task'
            assert cleanup_temporary_files_task.name == 'workers.tasks.cleanup.cleanup_temporary_files_task'
            
        except ImportError as e:
            pytest.skip(f"Could not import tasks: {e}")
    
    def test_archive_task_execution(self):
        """Test archive task execution with mock data."""
        try:
            from tasks.archive import process_archive_task
            
            task_data = {
                'task_id': str(uuid4()),
                'file_url': 'https://example.com/archive.zip',
                'user_id': 'test_user'
            }
            
            # Mock the task execution
            with patch.object(process_archive_task, 'update_task_status'):
                result = process_archive_task.run(task_data)
            
            # Verify result structure
            assert 'task_id' in result
            assert 'status' in result
            assert result['status'] == 'completed'
            assert 'result' in result
            
        except ImportError as e:
            pytest.skip(f"Could not import archive task: {e}")
    
    def test_parsing_task_execution(self):
        """Test parsing task execution with mock data."""
        try:
            from tasks.parsing import parse_document_task
            
            task_data = {
                'task_id': str(uuid4()),
                'file_url': 'https://example.com/document.pdf',
                'user_id': 'test_user'
            }
            
            # Mock the task execution
            with patch.object(parse_document_task, 'update_task_status'):
                result = parse_document_task.run(task_data)
            
            # Verify result structure
            assert 'task_id' in result
            assert 'status' in result
            assert result['status'] == 'completed'
            assert 'result' in result
            assert 'extracted_content' in result['result']
            assert 'token_usage' in result['result']
            
        except ImportError as e:
            pytest.skip(f"Could not import parsing task: {e}")
    
    def test_vectorization_task_execution(self):
        """Test vectorization task execution with mock data."""
        try:
            from tasks.vectorization import vectorize_content_task
            
            task_data = {
                'task_id': str(uuid4()),
                'content': {'text': 'Sample content to vectorize'},
                'user_id': 'test_user'
            }
            
            # Mock the task execution
            with patch.object(vectorize_content_task, 'update_task_status'):
                result = vectorize_content_task.run(task_data)
            
            # Verify result structure
            assert 'task_id' in result
            assert 'status' in result
            assert result['status'] == 'completed'
            assert 'result' in result
            assert 'vectors_stored' in result['result']
            
        except ImportError as e:
            pytest.skip(f"Could not import vectorization task: {e}")
    
    def test_cleanup_task_execution(self):
        """Test cleanup task execution with mock data."""
        try:
            from tasks.cleanup import cleanup_temporary_files_task
            
            cleanup_data = {
                'task_id': str(uuid4()),
                'file_paths': ['/tmp/file1.txt', '/tmp/file2.txt'],
                'storage_policy': 'temporary'
            }
            
            # Mock the task execution
            with patch.object(cleanup_temporary_files_task, 'update_task_status'):
                result = cleanup_temporary_files_task.run(cleanup_data)
            
            # Verify result structure
            assert 'task_id' in result
            assert 'status' in result
            assert result['status'] == 'completed'
            assert 'result' in result
            assert 'files_cleaned' in result['result']
            
        except ImportError as e:
            pytest.skip(f"Could not import cleanup task: {e}")


class TestBaseTaskFunctionality:
    """Test BaseTask functionality with mocked dependencies."""
    
    def setup_method(self):
        """Set up test fixtures."""
        try:
            from tasks.base import BaseTask
            self.task = BaseTask()
            self.task.name = "test_task"
            # Mock the request property using patch
            self.task_id = str(uuid4())
        except ImportError:
            pytest.skip("Could not import BaseTask")
    
    def test_task_retry_logic(self):
        """Test task retry logic."""
        # Test retryable exceptions
        retryable_exceptions = [
            ConnectionError("Network error"),
            TimeoutError("Request timeout"),
            OSError("System error")
        ]
        
        for exc in retryable_exceptions:
            assert self.task.should_retry(exc), f"Should retry {type(exc).__name__}"
        
        # Test non-retryable exceptions
        non_retryable_exceptions = [
            ValueError("Invalid input"),
            TypeError("Type error"),
            KeyError("Missing key")
        ]
        
        for exc in non_retryable_exceptions:
            assert not self.task.should_retry(exc), f"Should not retry {type(exc).__name__}"
    
    @patch('tasks.base.time.time')
    def test_task_timing(self, mock_time):
        """Test task timing functionality."""
        # Mock time progression
        mock_time.side_effect = [100.0, 101.5]  # start, end
        
        self.task.start_time = 100.0
        
        with patch.object(self.task, 'update_task_status') as mock_update:
            self.task.on_success({"result": "success"}, self.task_id, [], {})
        
        # Verify timing calculation
        call_args = mock_update.call_args
        assert call_args[1]['processing_time'] == 1.5
    
    def test_error_handling(self):
        """Test error handling in task execution."""
        exc = ValueError("Test error")
        einfo = Mock()
        einfo.traceback = "test traceback"
        
        # Mock the request property
        with patch.object(self.task, 'request', Mock()) as mock_request:
            mock_request.retries = 3
            self.task.retry_kwargs = {'max_retries': 3}
            
            with patch.object(self.task, 'update_task_status') as mock_update:
                self.task.on_failure(exc, self.task_id, [], {}, einfo)
            
            # Verify error details are captured
            call_args = mock_update.call_args
            assert call_args[1]['error_message'] == "Test error"
            assert 'error_details' in call_args[1]
            assert call_args[1]['error_details']['is_final_failure'] is True


class TestCeleryAppConfiguration:
    """Test Celery app configuration."""
    
    def test_celery_app_creation(self):
        """Test Celery app is properly configured."""
        try:
            from celery_app import celery_app
            
            # Test app configuration
            assert celery_app.main == 'document_intelligence_workers'
            
            # Test queue configuration
            queues = celery_app.conf.task_queues
            queue_names = [q.name for q in queues]
            
            expected_queues = [
                'archive_processing', 'document_parsing', 
                'vectorization', 'cleanup'
            ]
            
            for queue_name in expected_queues:
                assert queue_name in queue_names
            
            # Test task routing
            task_routes = celery_app.conf.task_routes
            assert 'workers.tasks.archive.process_archive_task' in task_routes
            assert 'workers.tasks.parsing.parse_document_task' in task_routes
            assert 'workers.tasks.vectorization.vectorize_content_task' in task_routes
            assert 'workers.tasks.cleanup.cleanup_temporary_files_task' in task_routes
            
        except ImportError as e:
            pytest.skip(f"Could not import celery_app: {e}")
    
    @patch('celery_app.celery_app.control.inspect')
    def test_health_check_functionality(self, mock_inspect):
        """Test health check functionality."""
        try:
            from celery_app import get_celery_health_status
            
            # Mock healthy system
            mock_inspect_instance = Mock()
            mock_inspect_instance.active.return_value = {'worker1': []}
            mock_inspect_instance.registered.return_value = {'worker1': ['task1']}
            mock_inspect.return_value = mock_inspect_instance
            
            with patch('redis.Redis.from_url') as mock_redis:
                mock_redis_instance = Mock()
                mock_redis_instance.llen.return_value = 5
                mock_redis.return_value = mock_redis_instance
                
                health_status = get_celery_health_status()
            
            assert health_status['status'] == 'healthy'
            assert health_status['active_workers'] == 1
            assert 'queue_stats' in health_status
            
        except ImportError as e:
            pytest.skip(f"Could not import health check: {e}")


def test_task_validation():
    """Test task input validation."""
    try:
        from tasks.base import validate_task_input
        
        # Test successful validation
        valid_data = {
            'task_id': str(uuid4()),
            'file_url': 'https://example.com/file.pdf',
            'user_id': 'test_user'
        }
        
        validate_task_input(valid_data, ['task_id', 'file_url', 'user_id'])
        
        # Test validation failure
        invalid_data = {'task_id': str(uuid4())}
        
        with pytest.raises(ValueError, match="Missing required fields"):
            validate_task_input(invalid_data, ['task_id', 'file_url', 'user_id'])
        
    except ImportError as e:
        pytest.skip(f"Could not import validation function: {e}")