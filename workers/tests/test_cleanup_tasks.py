"""Tests for cleanup Celery tasks."""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4

from src.tasks.cleanup import (
    cleanup_temporary_files_task,
    cleanup_orphaned_files_task,
    scheduled_cleanup_task
)
from src.tasks.base import TaskStatus


class TestCleanupTasks:
    """Test cleanup Celery tasks."""
    
    def test_cleanup_temporary_files_task_success(self):
        """Test successful temporary files cleanup task."""
        task_id = str(uuid4())
        cleanup_data = {
            'task_id': task_id,
            'batch_size': 50,
            'dry_run': False
        }
        
        # Mock cleanup service and result
        mock_cleanup_result = Mock()
        mock_cleanup_result.files_processed = 10
        mock_cleanup_result.files_deleted = 8
        mock_cleanup_result.bytes_freed = 1024000
        mock_cleanup_result.duration_seconds = 5.5
        mock_cleanup_result.errors = []
        
        with patch('src.tasks.cleanup.StorageCleanupService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.cleanup_expired_files.return_value = mock_cleanup_result
            
            # Execute task
            result = cleanup_temporary_files_task(cleanup_data)
            
            # Verify service was called correctly
            mock_service.cleanup_expired_files.assert_called_once_with(
                batch_size=50,
                dry_run=False
            )
            
            # Verify result
            assert result['status'] == TaskStatus.COMPLETED.value
            assert result['result']['files_processed'] == 10
            assert result['result']['files_deleted'] == 8
            assert result['result']['bytes_freed'] == 1024000
            assert result['result']['duration_seconds'] == 5.5
            assert result['result']['errors'] == []
            assert result['result']['dry_run'] is False
    
    def test_cleanup_temporary_files_task_dry_run(self):
        """Test temporary files cleanup task in dry run mode."""
        task_id = str(uuid4())
        cleanup_data = {
            'task_id': task_id,
            'batch_size': 100,
            'dry_run': True
        }
        
        mock_cleanup_result = Mock()
        mock_cleanup_result.files_processed = 5
        mock_cleanup_result.files_deleted = 5
        mock_cleanup_result.bytes_freed = 512000
        mock_cleanup_result.duration_seconds = 1.2
        mock_cleanup_result.errors = []
        
        with patch('src.tasks.cleanup.StorageCleanupService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.cleanup_expired_files.return_value = mock_cleanup_result
            
            result = cleanup_temporary_files_task(cleanup_data)
            
            mock_service.cleanup_expired_files.assert_called_once_with(
                batch_size=100,
                dry_run=True
            )
            
            assert result['status'] == TaskStatus.COMPLETED.value
            assert result['result']['dry_run'] is True
    
    def test_cleanup_temporary_files_task_with_defaults(self):
        """Test temporary files cleanup task with default parameters."""
        task_id = str(uuid4())
        cleanup_data = {
            'task_id': task_id
        }
        
        mock_cleanup_result = Mock()
        mock_cleanup_result.files_processed = 0
        mock_cleanup_result.files_deleted = 0
        mock_cleanup_result.bytes_freed = 0
        mock_cleanup_result.duration_seconds = 0.1
        mock_cleanup_result.errors = []
        
        with patch('src.tasks.cleanup.StorageCleanupService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.cleanup_expired_files.return_value = mock_cleanup_result
            
            result = cleanup_temporary_files_task(cleanup_data)
            
            # Verify default parameters were used
            mock_service.cleanup_expired_files.assert_called_once_with(
                batch_size=100,  # Default
                dry_run=False    # Default
            )
            
            assert result['status'] == TaskStatus.COMPLETED.value
    
    def test_cleanup_temporary_files_task_failure(self):
        """Test temporary files cleanup task failure."""
        task_id = str(uuid4())
        cleanup_data = {
            'task_id': task_id,
            'batch_size': 50
        }
        
        with patch('src.tasks.cleanup.StorageCleanupService') as mock_service_class:
            mock_service_class.side_effect = Exception("Storage service error")
            
            result = cleanup_temporary_files_task(cleanup_data)
            
            assert result['status'] == TaskStatus.FAILED.value
            assert 'Storage service error' in result['error']
            assert result['result']['files_processed'] == 0
            assert result['result']['files_deleted'] == 0
            assert result['result']['bytes_freed'] == 0
            assert 'Storage service error' in result['result']['errors']
    
    def test_cleanup_orphaned_files_task_success(self):
        """Test successful orphaned files cleanup task."""
        task_id = str(uuid4())
        cleanup_data = {
            'task_id': task_id,
            'dry_run': False
        }
        
        mock_cleanup_result = Mock()
        mock_cleanup_result.files_processed = 20
        mock_cleanup_result.files_deleted = 3
        mock_cleanup_result.bytes_freed = 2048000
        mock_cleanup_result.duration_seconds = 10.5
        mock_cleanup_result.errors = []
        
        with patch('src.tasks.cleanup.StorageCleanupService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.cleanup_orphaned_files.return_value = mock_cleanup_result
            
            result = cleanup_orphaned_files_task(cleanup_data)
            
            mock_service.cleanup_orphaned_files.assert_called_once_with(dry_run=False)
            
            assert result['status'] == TaskStatus.COMPLETED.value
            assert result['result']['files_processed'] == 20
            assert result['result']['files_deleted'] == 3
            assert result['result']['bytes_freed'] == 2048000
            assert result['result']['duration_seconds'] == 10.5
            assert result['result']['errors'] == []
            assert result['result']['dry_run'] is False
    
    def test_cleanup_orphaned_files_task_dry_run(self):
        """Test orphaned files cleanup task in dry run mode."""
        task_id = str(uuid4())
        cleanup_data = {
            'task_id': task_id,
            'dry_run': True
        }
        
        mock_cleanup_result = Mock()
        mock_cleanup_result.files_processed = 15
        mock_cleanup_result.files_deleted = 2
        mock_cleanup_result.bytes_freed = 1536000
        mock_cleanup_result.duration_seconds = 3.2
        mock_cleanup_result.errors = []
        
        with patch('src.tasks.cleanup.StorageCleanupService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.cleanup_orphaned_files.return_value = mock_cleanup_result
            
            result = cleanup_orphaned_files_task(cleanup_data)
            
            mock_service.cleanup_orphaned_files.assert_called_once_with(dry_run=True)
            
            assert result['status'] == TaskStatus.COMPLETED.value
            assert result['result']['dry_run'] is True
    
    def test_cleanup_orphaned_files_task_failure(self):
        """Test orphaned files cleanup task failure."""
        task_id = str(uuid4())
        cleanup_data = {
            'task_id': task_id
        }
        
        with patch('src.tasks.cleanup.StorageCleanupService') as mock_service_class:
            mock_service_class.side_effect = Exception("S3 connection error")
            
            result = cleanup_orphaned_files_task(cleanup_data)
            
            assert result['status'] == TaskStatus.FAILED.value
            assert 'S3 connection error' in result['error']
            assert result['result']['files_processed'] == 0
            assert result['result']['files_deleted'] == 0
            assert result['result']['bytes_freed'] == 0
    
    def test_scheduled_cleanup_task_expired_only(self):
        """Test scheduled cleanup task with expired files only."""
        task_id = str(uuid4())
        cleanup_data = {
            'task_id': task_id,
            'batch_size': 200,
            'include_orphaned': False
        }
        
        # Mock expired files cleanup result
        mock_expired_result = Mock()
        mock_expired_result.files_processed = 50
        mock_expired_result.files_deleted = 45
        mock_expired_result.bytes_freed = 5120000
        mock_expired_result.duration_seconds = 15.5
        mock_expired_result.errors = []
        
        with patch('src.tasks.cleanup.StorageCleanupService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.cleanup_expired_files.return_value = mock_expired_result
            
            result = scheduled_cleanup_task(cleanup_data)
            
            mock_service.cleanup_expired_files.assert_called_once_with(
                batch_size=200,
                dry_run=False
            )
            mock_service.cleanup_orphaned_files.assert_not_called()
            
            assert result['status'] == TaskStatus.COMPLETED.value
            assert result['result']['expired_files_processed'] == 50
            assert result['result']['expired_files_deleted'] == 45
            assert result['result']['expired_bytes_freed'] == 5120000
            assert result['result']['orphaned_files_processed'] == 0
            assert result['result']['orphaned_files_deleted'] == 0
            assert result['result']['orphaned_bytes_freed'] == 0
            assert result['result']['total_files_deleted'] == 45
            assert result['result']['total_bytes_freed'] == 5120000
    
    def test_scheduled_cleanup_task_with_orphaned(self):
        """Test scheduled cleanup task including orphaned files."""
        task_id = str(uuid4())
        cleanup_data = {
            'task_id': task_id,
            'batch_size': 300,
            'include_orphaned': True
        }
        
        # Mock expired files cleanup result
        mock_expired_result = Mock()
        mock_expired_result.files_processed = 30
        mock_expired_result.files_deleted = 25
        mock_expired_result.bytes_freed = 3072000
        mock_expired_result.duration_seconds = 8.5
        mock_expired_result.errors = []
        
        # Mock orphaned files cleanup result
        mock_orphaned_result = Mock()
        mock_orphaned_result.files_processed = 100
        mock_orphaned_result.files_deleted = 5
        mock_orphaned_result.bytes_freed = 1024000
        mock_orphaned_result.duration_seconds = 12.3
        mock_orphaned_result.errors = []
        
        with patch('src.tasks.cleanup.StorageCleanupService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.cleanup_expired_files.return_value = mock_expired_result
            mock_service.cleanup_orphaned_files.return_value = mock_orphaned_result
            
            result = scheduled_cleanup_task(cleanup_data)
            
            mock_service.cleanup_expired_files.assert_called_once_with(
                batch_size=300,
                dry_run=False
            )
            mock_service.cleanup_orphaned_files.assert_called_once_with(dry_run=False)
            
            assert result['status'] == TaskStatus.COMPLETED.value
            assert result['result']['expired_files_deleted'] == 25
            assert result['result']['expired_bytes_freed'] == 3072000
            assert result['result']['orphaned_files_deleted'] == 5
            assert result['result']['orphaned_bytes_freed'] == 1024000
            assert result['result']['total_files_deleted'] == 30  # 25 + 5
            assert result['result']['total_bytes_freed'] == 4096000  # 3072000 + 1024000
    
    def test_scheduled_cleanup_task_with_defaults(self):
        """Test scheduled cleanup task with default parameters."""
        task_id = str(uuid4())
        cleanup_data = {
            'task_id': task_id
        }
        
        mock_expired_result = Mock()
        mock_expired_result.files_processed = 0
        mock_expired_result.files_deleted = 0
        mock_expired_result.bytes_freed = 0
        mock_expired_result.duration_seconds = 0.1
        mock_expired_result.errors = []
        
        with patch('src.tasks.cleanup.StorageCleanupService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.cleanup_expired_files.return_value = mock_expired_result
            
            result = scheduled_cleanup_task(cleanup_data)
            
            # Verify default parameters
            mock_service.cleanup_expired_files.assert_called_once_with(
                batch_size=500,  # Default
                dry_run=False
            )
            mock_service.cleanup_orphaned_files.assert_not_called()  # Default include_orphaned=False
            
            assert result['status'] == TaskStatus.COMPLETED.value
    
    def test_scheduled_cleanup_task_failure(self):
        """Test scheduled cleanup task failure."""
        task_id = str(uuid4())
        cleanup_data = {
            'task_id': task_id,
            'batch_size': 100
        }
        
        with patch('src.tasks.cleanup.StorageCleanupService') as mock_service_class:
            mock_service_class.side_effect = Exception("Database connection error")
            
            result = scheduled_cleanup_task(cleanup_data)
            
            assert result['status'] == TaskStatus.FAILED.value
            assert 'Database connection error' in result['error']
            assert result['result']['total_files_deleted'] == 0
            assert result['result']['total_bytes_freed'] == 0
    
    def test_cleanup_temporary_files_task_missing_task_id(self):
        """Test cleanup task with missing task_id."""
        cleanup_data = {
            'batch_size': 50
        }
        
        with pytest.raises(ValueError, match="Missing required field"):
            cleanup_temporary_files_task(cleanup_data)
    
    def test_cleanup_orphaned_files_task_missing_task_id(self):
        """Test orphaned cleanup task with missing task_id."""
        cleanup_data = {
            'dry_run': True
        }
        
        with pytest.raises(ValueError, match="Missing required field"):
            cleanup_orphaned_files_task(cleanup_data)
    
    def test_scheduled_cleanup_task_missing_task_id(self):
        """Test scheduled cleanup task with missing task_id."""
        cleanup_data = {
            'batch_size': 200
        }
        
        with pytest.raises(ValueError, match="Missing required field"):
            scheduled_cleanup_task(cleanup_data)


if __name__ == "__main__":
    pytest.main([__file__])