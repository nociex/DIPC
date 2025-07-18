"""Cleanup tasks for storage management."""

from typing import Dict, Any, Optional
import structlog
from datetime import datetime
from collections import namedtuple

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from celery_app import celery_app
from tasks.base import BaseTask, TaskStatus, create_task_result, validate_task_input

logger = structlog.get_logger(__name__)

# Mock cleanup result for testing/development
CleanupResult = namedtuple('CleanupResult', ['files_processed', 'files_deleted', 'bytes_freed', 'duration_seconds', 'errors'])

class MockStorageCleanupService:
    """Mock storage cleanup service for development/testing."""
    
    def cleanup_expired_files(self, batch_size=100, dry_run=False):
        """Mock cleanup expired files."""
        logger.info("Mock cleanup expired files", batch_size=batch_size, dry_run=dry_run)
        return CleanupResult(0, 0, 0, 0.1, [])
    
    def cleanup_orphaned_files(self, dry_run=False):
        """Mock cleanup orphaned files."""
        logger.info("Mock cleanup orphaned files", dry_run=dry_run)
        return CleanupResult(0, 0, 0, 0.1, [])


@celery_app.task(bind=True, base=BaseTask, name='workers.tasks.cleanup.cleanup_temporary_files_task')
def cleanup_temporary_files_task(self, cleanup_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean up temporary files based on TTL policies.
    
    Args:
        cleanup_data: Dictionary containing cleanup information
            - task_id: UUID of the cleanup task
            - batch_size: Number of files to process (optional, default 100)
            - dry_run: Whether to simulate cleanup (optional, default False)
    
    Returns:
        Dict containing cleanup results
    """
    # Validate input
    validate_task_input(cleanup_data, ['task_id'])
    
    task_id = cleanup_data['task_id']
    batch_size = cleanup_data.get('batch_size', 100)
    dry_run = cleanup_data.get('dry_run', False)
    
    logger.info(
        "Starting cleanup task",
        task_id=task_id,
        batch_size=batch_size,
        dry_run=dry_run
    )
    
    try:
        # Use mock service for development/testing
        # In production, this would import the actual StorageCleanupService
        cleanup_service = MockStorageCleanupService()
        
        # Perform cleanup
        cleanup_result = cleanup_service.cleanup_expired_files(
            batch_size=batch_size,
            dry_run=dry_run
        )
        
        # Create task result
        result = create_task_result(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            result={
                "files_processed": cleanup_result.files_processed,
                "files_deleted": cleanup_result.files_deleted,
                "bytes_freed": cleanup_result.bytes_freed,
                "duration_seconds": cleanup_result.duration_seconds,
                "errors": cleanup_result.errors,
                "dry_run": dry_run
            }
        )
        
        logger.info(
            "Cleanup task completed successfully",
            task_id=task_id,
            files_deleted=cleanup_result.files_deleted,
            bytes_freed=cleanup_result.bytes_freed
        )
        
        return result.dict()
        
    except Exception as e:
        logger.error(
            "Cleanup task failed",
            task_id=task_id,
            error=str(e)
        )
        
        result = create_task_result(
            task_id=task_id,
            status=TaskStatus.FAILED,
            error_message=str(e),
            result={
                "files_processed": 0,
                "files_deleted": 0,
                "bytes_freed": 0,
                "errors": [str(e)]
            }
        )
        
        return result.dict()


@celery_app.task(bind=True, base=BaseTask, name='workers.tasks.cleanup.cleanup_orphaned_files_task')
def cleanup_orphaned_files_task(self, cleanup_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean up orphaned files in S3 that have no database records.
    
    Args:
        cleanup_data: Dictionary containing cleanup information
            - task_id: UUID of the cleanup task
            - dry_run: Whether to simulate cleanup (optional, default False)
    
    Returns:
        Dict containing cleanup results
    """
    # Validate input
    validate_task_input(cleanup_data, ['task_id'])
    
    task_id = cleanup_data['task_id']
    dry_run = cleanup_data.get('dry_run', False)
    
    logger.info(
        "Starting orphaned files cleanup task",
        task_id=task_id,
        dry_run=dry_run
    )
    
    try:
        # Use mock service for development/testing
        cleanup_service = MockStorageCleanupService()
        
        # Perform orphaned files cleanup
        cleanup_result = cleanup_service.cleanup_orphaned_files(dry_run=dry_run)
        
        # Create task result
        result = create_task_result(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            result={
                "files_processed": cleanup_result.files_processed,
                "files_deleted": cleanup_result.files_deleted,
                "bytes_freed": cleanup_result.bytes_freed,
                "duration_seconds": cleanup_result.duration_seconds,
                "errors": cleanup_result.errors,
                "dry_run": dry_run
            }
        )
        
        logger.info(
            "Orphaned files cleanup task completed successfully",
            task_id=task_id,
            files_deleted=cleanup_result.files_deleted,
            bytes_freed=cleanup_result.bytes_freed
        )
        
        return result.dict()
        
    except Exception as e:
        logger.error(
            "Orphaned files cleanup task failed",
            task_id=task_id,
            error=str(e)
        )
        
        result = create_task_result(
            task_id=task_id,
            status=TaskStatus.FAILED,
            error_message=str(e),
            result={
                "files_processed": 0,
                "files_deleted": 0,
                "bytes_freed": 0,
                "errors": [str(e)]
            }
        )
        
        return result.dict()


@celery_app.task(bind=True, base=BaseTask, name='workers.tasks.cleanup.scheduled_cleanup_task')
def scheduled_cleanup_task(self, cleanup_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Scheduled cleanup task that runs periodically to clean up expired files.
    
    Args:
        cleanup_data: Dictionary containing cleanup information
            - task_id: UUID of the cleanup task
            - batch_size: Number of files to process (optional, default 500)
            - include_orphaned: Whether to also clean orphaned files (optional, default False)
    
    Returns:
        Dict containing cleanup results
    """
    # Validate input
    validate_task_input(cleanup_data, ['task_id'])
    
    task_id = cleanup_data['task_id']
    batch_size = cleanup_data.get('batch_size', 500)
    include_orphaned = cleanup_data.get('include_orphaned', False)
    
    logger.info(
        "Starting scheduled cleanup task",
        task_id=task_id,
        batch_size=batch_size,
        include_orphaned=include_orphaned
    )
    
    try:
        # Use mock service for development/testing
        cleanup_service = MockStorageCleanupService()
        
        # Perform expired files cleanup
        expired_result = cleanup_service.cleanup_expired_files(
            batch_size=batch_size,
            dry_run=False
        )
        
        total_result = {
            "expired_files_processed": expired_result.files_processed,
            "expired_files_deleted": expired_result.files_deleted,
            "expired_bytes_freed": expired_result.bytes_freed,
            "expired_duration": expired_result.duration_seconds,
            "expired_errors": expired_result.errors,
            "orphaned_files_processed": 0,
            "orphaned_files_deleted": 0,
            "orphaned_bytes_freed": 0,
            "orphaned_duration": 0.0,
            "orphaned_errors": []
        }
        
        # Optionally clean orphaned files
        if include_orphaned:
            orphaned_result = cleanup_service.cleanup_orphaned_files(dry_run=False)
            total_result.update({
                "orphaned_files_processed": orphaned_result.files_processed,
                "orphaned_files_deleted": orphaned_result.files_deleted,
                "orphaned_bytes_freed": orphaned_result.bytes_freed,
                "orphaned_duration": orphaned_result.duration_seconds,
                "orphaned_errors": orphaned_result.errors
            })
        
        # Calculate totals
        total_result["total_files_deleted"] = (
            total_result["expired_files_deleted"] + 
            total_result["orphaned_files_deleted"]
        )
        total_result["total_bytes_freed"] = (
            total_result["expired_bytes_freed"] + 
            total_result["orphaned_bytes_freed"]
        )
        
        # Create task result
        result = create_task_result(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            result=total_result
        )
        
        logger.info(
            "Scheduled cleanup task completed successfully",
            task_id=task_id,
            total_files_deleted=total_result["total_files_deleted"],
            total_bytes_freed=total_result["total_bytes_freed"]
        )
        
        return result.dict()
        
    except Exception as e:
        logger.error(
            "Scheduled cleanup task failed",
            task_id=task_id,
            error=str(e)
        )
        
        result = create_task_result(
            task_id=task_id,
            status=TaskStatus.FAILED,
            error_message=str(e),
            result={
                "total_files_deleted": 0,
                "total_bytes_freed": 0,
                "errors": [str(e)]
            }
        )
        
        return result.dict()