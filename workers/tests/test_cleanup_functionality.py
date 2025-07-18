"""Functional tests for cleanup tasks."""

import pytest
from uuid import uuid4

from src.tasks.cleanup import (
    cleanup_temporary_files_task,
    cleanup_orphaned_files_task,
    scheduled_cleanup_task
)
from src.tasks.base import TaskStatus


class TestCleanupFunctionality:
    """Test cleanup task functionality."""
    
    def test_cleanup_temporary_files_task_structure(self):
        """Test that cleanup task returns proper structure."""
        task_id = str(uuid4())
        cleanup_data = {
            'task_id': task_id,
            'batch_size': 50,
            'dry_run': True
        }
        
        result = cleanup_temporary_files_task(cleanup_data)
        
        # Verify result structure
        assert isinstance(result, dict)
        assert 'status' in result
        assert 'result' in result
        assert 'task_id' in result
        assert result['status'] == TaskStatus.COMPLETED.value
        assert result['task_id'] == task_id
        
        # Verify result data structure
        result_data = result['result']
        assert 'files_processed' in result_data
        assert 'files_deleted' in result_data
        assert 'bytes_freed' in result_data
        assert 'duration_seconds' in result_data
        assert 'errors' in result_data
        assert 'dry_run' in result_data
        assert result_data['dry_run'] is True
    
    def test_cleanup_orphaned_files_task_structure(self):
        """Test that orphaned files cleanup task returns proper structure."""
        task_id = str(uuid4())
        cleanup_data = {
            'task_id': task_id,
            'dry_run': True
        }
        
        result = cleanup_orphaned_files_task(cleanup_data)
        
        # Verify result structure
        assert isinstance(result, dict)
        assert 'status' in result
        assert 'result' in result
        assert 'task_id' in result
        assert result['status'] == TaskStatus.COMPLETED.value
        assert result['task_id'] == task_id
        
        # Verify result data structure
        result_data = result['result']
        assert 'files_processed' in result_data
        assert 'files_deleted' in result_data
        assert 'bytes_freed' in result_data
        assert 'duration_seconds' in result_data
        assert 'errors' in result_data
        assert 'dry_run' in result_data
        assert result_data['dry_run'] is True
    
    def test_scheduled_cleanup_task_structure(self):
        """Test that scheduled cleanup task returns proper structure."""
        task_id = str(uuid4())
        cleanup_data = {
            'task_id': task_id,
            'batch_size': 200,
            'include_orphaned': False
        }
        
        result = scheduled_cleanup_task(cleanup_data)
        
        # Verify result structure
        assert isinstance(result, dict)
        assert 'status' in result
        assert 'result' in result
        assert 'task_id' in result
        assert result['status'] == TaskStatus.COMPLETED.value
        assert result['task_id'] == task_id
        
        # Verify result data structure
        result_data = result['result']
        assert 'expired_files_processed' in result_data
        assert 'expired_files_deleted' in result_data
        assert 'expired_bytes_freed' in result_data
        assert 'orphaned_files_processed' in result_data
        assert 'orphaned_files_deleted' in result_data
        assert 'orphaned_bytes_freed' in result_data
        assert 'total_files_deleted' in result_data
        assert 'total_bytes_freed' in result_data
    
    def test_scheduled_cleanup_task_with_orphaned(self):
        """Test scheduled cleanup task with orphaned files enabled."""
        task_id = str(uuid4())
        cleanup_data = {
            'task_id': task_id,
            'batch_size': 100,
            'include_orphaned': True
        }
        
        result = scheduled_cleanup_task(cleanup_data)
        
        assert result['status'] == TaskStatus.COMPLETED.value
        result_data = result['result']
        
        # Should have both expired and orphaned results
        assert 'expired_files_processed' in result_data
        assert 'orphaned_files_processed' in result_data
        assert 'total_files_deleted' in result_data
        assert 'total_bytes_freed' in result_data
    
    def test_cleanup_task_default_parameters(self):
        """Test cleanup task with default parameters."""
        task_id = str(uuid4())
        cleanup_data = {
            'task_id': task_id
        }
        
        result = cleanup_temporary_files_task(cleanup_data)
        
        assert result['status'] == TaskStatus.COMPLETED.value
        assert result['result']['dry_run'] is False  # Default
    
    def test_cleanup_task_missing_task_id(self):
        """Test cleanup task with missing task_id raises error."""
        cleanup_data = {
            'batch_size': 50
        }
        
        with pytest.raises(ValueError, match="Missing required fields"):
            cleanup_temporary_files_task(cleanup_data)
    
    def test_orphaned_cleanup_task_missing_task_id(self):
        """Test orphaned cleanup task with missing task_id raises error."""
        cleanup_data = {
            'dry_run': True
        }
        
        with pytest.raises(ValueError, match="Missing required fields"):
            cleanup_orphaned_files_task(cleanup_data)
    
    def test_scheduled_cleanup_task_missing_task_id(self):
        """Test scheduled cleanup task with missing task_id raises error."""
        cleanup_data = {
            'batch_size': 200
        }
        
        with pytest.raises(ValueError, match="Missing required fields"):
            scheduled_cleanup_task(cleanup_data)


if __name__ == "__main__":
    pytest.main([__file__])