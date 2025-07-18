"""Archive processing tasks."""

import os
import tempfile
import shutil
from typing import Dict, Any, List
from uuid import UUID, uuid4
import structlog
import requests
from urllib.parse import urlparse

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from celery_app import celery_app
from tasks.base import BaseTask, TaskStatus, create_task_result, validate_task_input
from utils.zip_security import SecureZipExtractor, ZipSecurityError

# Import database models and repositories
try:
    # Try to import from the API directory
    api_src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'api', 'src')
    if api_src_path not in sys.path:
        sys.path.insert(0, api_src_path)
    from database.models import TaskStatusEnum, TaskTypeEnum
    from database.repositories import TaskRepository, FileMetadataRepository
    from database.connection import get_db_session
except ImportError:
    # Fallback for testing - create mock enums
    from enum import Enum
    
    class TaskStatusEnum(Enum):
        PENDING = "pending"
        PROCESSING = "processing"
        COMPLETED = "completed"
        FAILED = "failed"
        CANCELLED = "cancelled"
    
    class TaskTypeEnum(Enum):
        DOCUMENT_PARSING = "document_parsing"
        ARCHIVE_PROCESSING = "archive_processing"
        VECTORIZATION = "vectorization"
        CLEANUP = "cleanup"
    
    # Mock classes for testing
    class TaskRepository:
        def __init__(self, db=None):
            self.db = db
        def update_status(self, *args, **kwargs):
            pass
        def create(self, *args, **kwargs):
            mock_task = type('MockTask', (), {'id': 'mock-id'})()
            return mock_task
        def get_by_id(self, *args, **kwargs):
            return None
    
    class FileMetadataRepository:
        def __init__(self, db=None):
            self.db = db
        def create(self, *args, **kwargs):
            pass
    
    def get_db_session():
        class MockSession:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
        return MockSession()

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, base=BaseTask, name='workers.tasks.archive.process_archive_task')
def process_archive_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process archive files (ZIP) and create subtasks for individual files.
    
    Args:
        task_data: Dictionary containing task information
            - task_id: UUID of the task
            - file_url: URL of the archive file
            - user_id: ID of the user who submitted the task
            - options: Processing options
    
    Returns:
        Dict containing processing results
    """
    # Validate input
    validate_task_input(task_data, ['task_id', 'file_url', 'user_id'])
    
    task_id = task_data['task_id']
    file_url = task_data['file_url']
    user_id = task_data['user_id']
    options = task_data.get('options', {})
    
    logger.info(
        "Starting archive processing task",
        task_id=task_id,
        file_url=file_url,
        user_id=user_id
    )
    
    # Update task status to processing
    try:
        with get_db_session() as db:
            task_repo = TaskRepository(db)
            task_repo.update_status(UUID(task_id), TaskStatusEnum.PROCESSING)
    except Exception as e:
        logger.error("Failed to update task status to processing", task_id=task_id, error=str(e))
        return create_task_result(
            task_id=task_id,
            status=TaskStatus.FAILED,
            error=f"Database error: {str(e)}"
        ).dict()
    
    temp_dir = None
    try:
        # Download the archive file
        archive_path = _download_archive_file(file_url, task_id)
        
        # Create secure ZIP extractor
        extractor = SecureZipExtractor()
        
        # Extract archive safely
        temp_dir, extracted_files = extractor.extract_zip_safely(archive_path)
        
        # Filter valid files
        valid_files = [f for f in extracted_files if f.is_valid]
        
        if not valid_files:
            raise ValueError("No valid files found in archive after extraction")
        
        logger.info(
            "Archive extraction completed",
            task_id=task_id,
            total_files=len(extracted_files),
            valid_files=len(valid_files),
            invalid_files=len(extracted_files) - len(valid_files)
        )
        
        # Create subtasks for each valid file
        subtask_ids = _create_subtasks_for_files(
            parent_task_id=task_id,
            user_id=user_id,
            extracted_files=valid_files,
            options=options,
            temp_dir=temp_dir
        )
        
        # Update parent task with results
        results = {
            "archive_processed": True,
            "total_files_in_archive": len(extracted_files),
            "valid_files_extracted": len(valid_files),
            "invalid_files_skipped": len(extracted_files) - len(valid_files),
            "subtasks_created": len(subtask_ids),
            "subtask_ids": [str(sid) for sid in subtask_ids],
            "extraction_directory": temp_dir,
            "invalid_files": [
                {
                    "filename": f.original_path,
                    "error": f.error_message
                }
                for f in extracted_files if not f.is_valid
            ]
        }
        
        with get_db_session() as db:
            task_repo = TaskRepository(db)
            task_repo.update_status(
                UUID(task_id), 
                TaskStatusEnum.COMPLETED,
                results=results
            )
        
        logger.info(
            "Archive processing task completed successfully",
            task_id=task_id,
            subtasks_created=len(subtask_ids)
        )
        
        return create_task_result(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            result=results
        ).dict()
        
    except ZipSecurityError as e:
        error_msg = f"Archive security validation failed: {str(e)}"
        logger.error("Archive security error", task_id=task_id, error=error_msg)
        
        try:
            with get_db_session() as db:
                task_repo = TaskRepository(db)
                task_repo.update_status(
                    UUID(task_id), 
                    TaskStatusEnum.FAILED,
                    error_message=error_msg
                )
        except Exception as db_error:
            logger.error("Failed to update task status after security error", 
                        task_id=task_id, error=str(db_error))
        
        return create_task_result(
            task_id=task_id,
            status=TaskStatus.FAILED,
            error=error_msg
        ).dict()
        
    except Exception as e:
        error_msg = f"Archive processing failed: {str(e)}"
        logger.error("Archive processing error", task_id=task_id, error=error_msg, exc_info=True)
        
        try:
            with get_db_session() as db:
                task_repo = TaskRepository(db)
                task_repo.update_status(
                    UUID(task_id), 
                    TaskStatusEnum.FAILED,
                    error_message=error_msg
                )
        except Exception as db_error:
            logger.error("Failed to update task status after processing error", 
                        task_id=task_id, error=str(db_error))
        
        return create_task_result(
            task_id=task_id,
            status=TaskStatus.FAILED,
            error=error_msg
        ).dict()
        
    finally:
        # Cleanup temporary files (but keep extraction directory for subtasks)
        if 'archive_path' in locals():
            try:
                os.unlink(archive_path)
                logger.debug("Cleaned up downloaded archive file", path=archive_path)
            except Exception as e:
                logger.warning("Failed to cleanup archive file", path=archive_path, error=str(e))


def _download_archive_file(file_url: str, task_id: str) -> str:
    """
    Download archive file from URL to temporary location.
    
    Args:
        file_url: URL of the archive file
        task_id: Task ID for logging
        
    Returns:
        Path to downloaded file
        
    Raises:
        Exception: If download fails
    """
    try:
        logger.info("Downloading archive file", task_id=task_id, url=file_url)
        
        # Parse URL to get filename
        parsed_url = urlparse(file_url)
        filename = os.path.basename(parsed_url.path) or f"archive_{task_id}.zip"
        
        # Create temporary file
        temp_fd, temp_path = tempfile.mkstemp(suffix=".zip", prefix=f"archive_{task_id}_")
        
        try:
            # Download file with streaming
            response = requests.get(file_url, stream=True, timeout=300)  # 5 minute timeout
            response.raise_for_status()
            
            # Check content length if available
            content_length = response.headers.get('content-length')
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > 500:  # 500MB limit
                    raise ValueError(f"Archive file too large: {size_mb:.1f}MB > 500MB")
            
            # Write file in chunks
            downloaded_size = 0
            max_size = 500 * 1024 * 1024  # 500MB
            
            with os.fdopen(temp_fd, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        downloaded_size += len(chunk)
                        if downloaded_size > max_size:
                            raise ValueError(f"Archive file too large during download: {downloaded_size} bytes")
                        f.write(chunk)
            
            logger.info(
                "Archive file downloaded successfully",
                task_id=task_id,
                path=temp_path,
                size_bytes=downloaded_size
            )
            
            return temp_path
            
        except Exception:
            # Cleanup on failure
            try:
                os.unlink(temp_path)
            except:
                pass
            raise
            
    except Exception as e:
        logger.error("Failed to download archive file", task_id=task_id, url=file_url, error=str(e))
        raise


def _create_subtasks_for_files(
    parent_task_id: str,
    user_id: str,
    extracted_files: List,
    options: Dict[str, Any],
    temp_dir: str
) -> List[UUID]:
    """
    Create subtasks for each extracted file.
    
    Args:
        parent_task_id: Parent task UUID
        user_id: User ID
        extracted_files: List of ExtractedFile objects
        options: Processing options
        temp_dir: Temporary directory containing extracted files
        
    Returns:
        List of created subtask UUIDs
    """
    subtask_ids = []
    
    try:
        with get_db_session() as db:
            task_repo = TaskRepository(db)
            file_repo = FileMetadataRepository(db)
            
            for extracted_file in extracted_files:
                # Create subtask
                subtask_data = {
                    'user_id': user_id,
                    'parent_task_id': UUID(parent_task_id),
                    'status': TaskStatusEnum.PENDING,
                    'task_type': TaskTypeEnum.DOCUMENT_PARSING.value,
                    'file_url': f"file://{extracted_file.safe_path}",  # Local file path
                    'original_filename': extracted_file.original_path,
                    'options': options
                }
                
                subtask = task_repo.create(subtask_data)
                subtask_ids.append(subtask.id)
                
                # Create file metadata
                file_metadata_data = {
                    'task_id': subtask.id,
                    'original_filename': extracted_file.original_path,
                    'file_type': extracted_file.file_type,
                    'file_size': extracted_file.file_size,
                    'storage_path': extracted_file.safe_path,
                    'storage_policy': options.get('storage_policy', 'temporary')
                }
                
                file_repo.create(file_metadata_data)
                
                logger.debug(
                    "Created subtask for extracted file",
                    parent_task_id=parent_task_id,
                    subtask_id=str(subtask.id),
                    filename=extracted_file.original_path
                )
            
            # Queue subtasks for processing
            _queue_subtasks_for_processing(subtask_ids)
            
        logger.info(
            "Created subtasks for archive processing",
            parent_task_id=parent_task_id,
            subtasks_created=len(subtask_ids)
        )
        
        return subtask_ids
        
    except Exception as e:
        logger.error(
            "Failed to create subtasks",
            parent_task_id=parent_task_id,
            error=str(e),
            exc_info=True
        )
        raise


def _queue_subtasks_for_processing(subtask_ids: List[UUID]) -> None:
    """
    Queue subtasks for document processing.
    
    Args:
        subtask_ids: List of subtask UUIDs to queue
    """
    try:
        # Import here to avoid circular imports
        from tasks.parsing import parse_document_task
        
        for subtask_id in subtask_ids:
            # Queue each subtask for document parsing
            parse_document_task.delay({
                'task_id': str(subtask_id),
                'source': 'archive_extraction'
            })
            
        logger.info(
            "Queued subtasks for document processing",
            subtask_count=len(subtask_ids)
        )
        
    except Exception as e:
        logger.error(
            "Failed to queue subtasks for processing",
            subtask_ids=[str(sid) for sid in subtask_ids],
            error=str(e)
        )
        # Don't raise here - subtasks are created and can be processed later


@celery_app.task(bind=True, base=BaseTask, name='workers.tasks.archive.cleanup_extraction_directory')
def cleanup_extraction_directory(self, extraction_dir: str, parent_task_id: str) -> Dict[str, Any]:
    """
    Clean up extraction directory after all subtasks are completed.
    
    Args:
        extraction_dir: Directory to clean up
        parent_task_id: Parent task ID for logging
        
    Returns:
        Dict containing cleanup results
    """
    logger.info(
        "Starting extraction directory cleanup",
        extraction_dir=extraction_dir,
        parent_task_id=parent_task_id
    )
    
    try:
        # Check if all subtasks are completed
        with get_db_session() as db:
            task_repo = TaskRepository(db)
            parent_task = task_repo.get_by_id(UUID(parent_task_id))
            
            if not parent_task:
                raise ValueError(f"Parent task {parent_task_id} not found")
            
            # Check subtask completion
            incomplete_subtasks = [
                subtask for subtask in parent_task.subtasks 
                if not subtask.is_completed()
            ]
            
            if incomplete_subtasks:
                logger.info(
                    "Subtasks still processing, deferring cleanup",
                    parent_task_id=parent_task_id,
                    incomplete_count=len(incomplete_subtasks)
                )
                
                # Reschedule cleanup for later
                cleanup_extraction_directory.apply_async(
                    args=[extraction_dir, parent_task_id],
                    countdown=300  # Try again in 5 minutes
                )
                
                return create_task_result(
                    task_id=parent_task_id,
                    status=TaskStatus.PENDING,
                    result={"message": "Cleanup deferred - subtasks still processing"}
                ).dict()
        
        # All subtasks completed, safe to cleanup
        if os.path.exists(extraction_dir):
            shutil.rmtree(extraction_dir)
            logger.info(
                "Extraction directory cleaned up successfully",
                extraction_dir=extraction_dir,
                parent_task_id=parent_task_id
            )
        else:
            logger.warning(
                "Extraction directory not found for cleanup",
                extraction_dir=extraction_dir,
                parent_task_id=parent_task_id
            )
        
        return create_task_result(
            task_id=parent_task_id,
            status=TaskStatus.COMPLETED,
            result={
                "cleanup_completed": True,
                "extraction_dir": extraction_dir
            }
        ).dict()
        
    except Exception as e:
        error_msg = f"Cleanup failed: {str(e)}"
        logger.error(
            "Failed to cleanup extraction directory",
            extraction_dir=extraction_dir,
            parent_task_id=parent_task_id,
            error=error_msg
        )
        
        return create_task_result(
            task_id=parent_task_id,
            status=TaskStatus.FAILED,
            error=error_msg
        ).dict()