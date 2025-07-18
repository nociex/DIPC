"""Simple tests for cleanup Celery tasks."""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4

from src.tasks.cleanup import (
    cleanup_temporary_files_task,
    cleanup_orphaned_files_task,
    scheduled_cleanup_task
)
from src.tasks.base import TaskStatus


class TestCleanupTasksSimple:
    """Simple tests for cleanup Celery tasks."""
    
    def test_cleanup_temporary_files_task_basic(self):
        """Test basic cleanup task functionality."""
        task_id = str(uuid4())
        cleanup_data = {
            'task_id': task_id,
            'batch_size': 50,
            'dry_run': True  # Use dry run to avoid actual cleanup
        }
        
        # Mock the StorageCleanupService import
        with patch('src.tasks.cleanup.StorageCleanupService', create=True) as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock cleanup result
            mock_cleanup_result = Mock()
            mock_cleanup_result.files_processed = 10
            mock_cleanup_result.files_deleted = 8
            mock_cleanup_result.bytes_freed = 1024000
            mock_cleanup_result.duration_seconds = 5.5
            mock_cleanup_result.errors = []
            
            mock_service.cleanup_expired_files.return_value = mock_cleanup_result
            
            # Execute task
            result = cleanup_temporary_files_task(cleanup_data)
            
            # Verify result structure
            assert 'status' in result
            assert 'result' in result
            assert result['status'] == TaskStatus.COMPLETED.value
            assert result['result']['files_processed'] == 10
            assert result['result']['files_deleted'] == 8
            assert result['result']['bytes_freed'] == 1024000
            assert result['result']['dry_run'] is True
    
    def test_cleanup_orphaned_files_task_basic(self):
        """Test basic orphaned files cleanup task."""
        task_id = str(uuid4())
        cleanup_data = {
            'task_id': task_id,
            'dry_run': True
        }
        
        with patch('src.tasks.cleanup.StorageCleanupService', create=True) as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            mock_cleanup_result = Mock()
            mock_cleanup_result.files_processed = 20
            mock_cleanup_result.files_deleted = 3
            mock_cleanup_result.bytes_freed = 2048000
            mock_cleanup_result.duration_seconds = 10.5
            mock_cleanup_result.errors = []
            
            mock_service.cleanup_orphaned_files.return_value = mock_cleanup_result
            
            result = cleanup_orphaned_files_task(cleanup_data)
            
            assert result['status'] == TaskStatus.COMPLETED.value
            assert result['result']['files_processed'] == 20
            assert result['result']['files_deleted'] == 3
            assert result['result']['bytes_freed'] == 2048000
            assert result['result']['dry_run'] is True
    
    def test_scheduled_cleanup_task_basic(self):
        """Test basic scheduled cleanup task."""
        task_id = str(uuid4())
        cleanup_data = {
            'task_id': task_id,
            'batch_size': 200,
            'include_orphaned': False
        }
        
        with patch('src.tasks.cleanup.StorageCleanupService', create=True) as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock expired files cleanup result
            mock_expired_result = Mock()
            mock_expired_result.files_processed = 50
            mock_expired_result.files_deleted = 45
            mock_expired_result.bytes_freed = 5120000
            mock_expired_result.duration_seconds = 15.5
            mock_expired_result.errors = []
            
            mock_service.cleanup_expired_files.return_value = mock_expired_result
            
            result = scheduled_cleanup_task(cleanup_data)
            
            assert result['status'] == TaskStatus.COMPLETED.value
            assert result['result']['expired_files_processed'] == 50
            assert result['result']['expired_files_deleted'] == 45
            assert result['result']['expired_bytes_freed'] == 5120000
            assert result['result']['total_files_deleted'] == 45
            assert result['result']['total_bytes_freed'] == 5120000
    
    def test_cleanup_task_missing_task_id(self):
        """Test cleanup task with missing task_id."""
        cleanup_data = {
            'batch_size': 50
        }
        
        with pytest.raises(ValueError, match="Missing required field"):
            cleanup_temporary_files_task(cleanup_data)
    
    def test_cleanup_task_with_defaults(self):
        """Test cleanup task with default parameters."""
        task_id = str(uuid4())
        cleanup_data = {
            'task_id': task_id
        }
        
        with patch('src.tasks.cleanup.StorageCleanupService', create=True) as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            mock_cleanup_result = Mock()
            mock_cleanup_result.files_processed = 0
            mock_cleanup_result.files_deleted = 0
            mock_cleanup_result.bytes_freed = 0
            mock_cleanup_result.duration_seconds = 0.1
            mock_cleanup_result.errors = []
            
            mock_service.cleanup_expired_files.return_value = mock_cleanup_result
            
            result = cleanup_temporary_files_task(cleanup_data)
            
            # Verify default parameters were used
            mock_service.cleanup_expired_files.assert_called_once_with(
                batch_size=100,  # Default
                dry_run=False    # Default
            )
            
            assert result['status'] == TaskStatus.COMPLETED.value


if __name__ == "__main__":
    pytest.main([__file__])