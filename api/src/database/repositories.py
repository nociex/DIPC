"""Database repository layer for CRUD operations."""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_, desc, asc, func, text

from .models import Task, FileMetadata, TaskStatusEnum, StoragePolicyEnum
from .connection import get_db_session

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository class with common functionality."""
    
    def __init__(self, db: Session = None):
        """Initialize repository with optional database session."""
        self.db = db
    
    def _get_session(self) -> Session:
        """Get database session, either injected or create new one."""
        if self.db:
            return self.db
        return next(get_db())


class TaskRepository(BaseRepository):
    """Repository for Task model operations."""
    
    def create(self, task_data: Dict[str, Any]) -> Task:
        """
        Create a new task.
        
        Args:
            task_data: Dictionary containing task data
            
        Returns:
            Task: Created task instance
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            db = self._get_session()
            task = Task(**task_data)
            db.add(task)
            db.commit()
            db.refresh(task)
            logger.info(f"Created task {task.id} for user {task.user_id}")
            return task
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Failed to create task: {e}")
            raise
    
    def get_by_id(self, task_id: UUID) -> Optional[Task]:
        """
        Get task by ID.
        
        Args:
            task_id: Task UUID
            
        Returns:
            Task or None if not found
        """
        try:
            db = self._get_session()
            task = db.query(Task).options(
                joinedload(Task.subtasks),
                joinedload(Task.file_metadata)
            ).filter(Task.id == task_id).first()
            return task
        except SQLAlchemyError as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            raise
    
    def get_by_user_id(
        self, 
        user_id: str, 
        limit: int = 50, 
        offset: int = 0,
        status_filter: Optional[TaskStatusEnum] = None,
        task_type_filter: Optional[str] = None
    ) -> List[Task]:
        """
        Get tasks by user ID with optional filtering.
        
        Args:
            user_id: User identifier
            limit: Maximum number of tasks to return
            offset: Number of tasks to skip
            status_filter: Optional status filter
            task_type_filter: Optional task type filter
            
        Returns:
            List of tasks
        """
        try:
            db = self._get_session()
            query = db.query(Task).filter(Task.user_id == user_id)
            
            if status_filter:
                query = query.filter(Task.status == status_filter)
            
            if task_type_filter:
                query = query.filter(Task.task_type == task_type_filter)
            
            tasks = query.options(
                joinedload(Task.subtasks),
                joinedload(Task.file_metadata)
            ).order_by(desc(Task.created_at)).offset(offset).limit(limit).all()
            
            return tasks
        except SQLAlchemyError as e:
            logger.error(f"Failed to get tasks for user {user_id}: {e}")
            raise
    
    def get_subtasks(self, parent_task_id: UUID) -> List[Task]:
        """
        Get all subtasks for a parent task.
        
        Args:
            parent_task_id: Parent task UUID
            
        Returns:
            List of subtasks
        """
        try:
            db = self._get_session()
            subtasks = db.query(Task).filter(
                Task.parent_task_id == parent_task_id
            ).order_by(asc(Task.created_at)).all()
            return subtasks
        except SQLAlchemyError as e:
            logger.error(f"Failed to get subtasks for task {parent_task_id}: {e}")
            raise
    
    def update_status(
        self, 
        task_id: UUID, 
        status: TaskStatusEnum, 
        error_message: Optional[str] = None,
        results: Optional[Dict[str, Any]] = None,
        actual_cost: Optional[float] = None
    ) -> Optional[Task]:
        """
        Update task status and related fields.
        
        Args:
            task_id: Task UUID
            status: New status
            error_message: Optional error message
            results: Optional results data
            actual_cost: Optional actual cost
            
        Returns:
            Updated task or None if not found
        """
        try:
            db = self._get_session()
            task = db.query(Task).filter(Task.id == task_id).first()
            
            if not task:
                logger.warning(f"Task {task_id} not found for status update")
                return None
            
            task.update_status(status, error_message)
            
            if results is not None:
                task.results = results
            
            if actual_cost is not None:
                task.actual_cost = actual_cost
            
            db.commit()
            db.refresh(task)
            logger.info(f"Updated task {task_id} status to {status.value}")
            return task
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Failed to update task {task_id} status: {e}")
            raise
    
    def get_pending_tasks(self, limit: int = 100) -> List[Task]:
        """
        Get pending tasks for processing.
        
        Args:
            limit: Maximum number of tasks to return
            
        Returns:
            List of pending tasks
        """
        try:
            db = self._get_session()
            tasks = db.query(Task).filter(
                Task.status == TaskStatusEnum.PENDING
            ).order_by(asc(Task.created_at)).limit(limit).all()
            return tasks
        except SQLAlchemyError as e:
            logger.error(f"Failed to get pending tasks: {e}")
            raise
    
    def get_processing_tasks(self, older_than_minutes: int = 30) -> List[Task]:
        """
        Get tasks that have been processing for too long.
        
        Args:
            older_than_minutes: Consider tasks stuck if processing longer than this
            
        Returns:
            List of potentially stuck tasks
        """
        try:
            db = self._get_session()
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=older_than_minutes)
            
            tasks = db.query(Task).filter(
                and_(
                    Task.status == TaskStatusEnum.PROCESSING,
                    Task.updated_at < cutoff_time
                )
            ).all()
            return tasks
        except SQLAlchemyError as e:
            logger.error(f"Failed to get stuck processing tasks: {e}")
            raise
    
    def delete(self, task_id: UUID) -> bool:
        """
        Delete a task and its related data.
        
        Args:
            task_id: Task UUID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            db = self._get_session()
            task = db.query(Task).filter(Task.id == task_id).first()
            
            if not task:
                return False
            
            db.delete(task)
            db.commit()
            logger.info(f"Deleted task {task_id}")
            return True
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Failed to delete task {task_id}: {e}")
            raise
    
    def get_task_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get task statistics.
        
        Args:
            user_id: Optional user filter
            
        Returns:
            Dictionary with task statistics
        """
        try:
            db = self._get_session()
            query = db.query(Task)
            
            if user_id:
                query = query.filter(Task.user_id == user_id)
            
            # Get status counts
            status_counts = {}
            for status in TaskStatusEnum:
                count = query.filter(Task.status == status).count()
                status_counts[status.value] = count
            
            # Get total tasks
            total_tasks = query.count()
            
            # Get average processing time for completed tasks
            completed_tasks = query.filter(
                and_(
                    Task.status == TaskStatusEnum.COMPLETED,
                    Task.completed_at.isnot(None)
                )
            ).all()
            
            avg_processing_time = 0
            if completed_tasks:
                processing_times = [
                    (task.completed_at - task.created_at).total_seconds()
                    for task in completed_tasks
                ]
                avg_processing_time = sum(processing_times) / len(processing_times)
            
            # Get cost statistics
            cost_stats = db.query(
                func.sum(Task.actual_cost).label('total_cost'),
                func.avg(Task.actual_cost).label('avg_cost'),
                func.count(Task.actual_cost).label('tasks_with_cost')
            ).filter(Task.actual_cost.isnot(None))
            
            if user_id:
                cost_stats = cost_stats.filter(Task.user_id == user_id)
            
            cost_result = cost_stats.first()
            
            return {
                'total_tasks': total_tasks,
                'status_counts': status_counts,
                'avg_processing_time_seconds': avg_processing_time,
                'total_cost': float(cost_result.total_cost) if cost_result.total_cost else 0,
                'avg_cost': float(cost_result.avg_cost) if cost_result.avg_cost else 0,
                'tasks_with_cost': cost_result.tasks_with_cost or 0
            }
        except SQLAlchemyError as e:
            logger.error(f"Failed to get task statistics: {e}")
            raise


class FileMetadataRepository(BaseRepository):
    """Repository for FileMetadata model operations."""
    
    def create(self, file_data: Dict[str, Any]) -> FileMetadata:
        """
        Create new file metadata record.
        
        Args:
            file_data: Dictionary containing file metadata
            
        Returns:
            FileMetadata: Created file metadata instance
        """
        try:
            db = self._get_session()
            file_metadata = FileMetadata(**file_data)
            db.add(file_metadata)
            db.commit()
            db.refresh(file_metadata)
            logger.info(f"Created file metadata {file_metadata.id} for task {file_metadata.task_id}")
            return file_metadata
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Failed to create file metadata: {e}")
            raise
    
    def get_by_id(self, file_id: UUID) -> Optional[FileMetadata]:
        """
        Get file metadata by ID.
        
        Args:
            file_id: File metadata UUID
            
        Returns:
            FileMetadata or None if not found
        """
        try:
            db = self._get_session()
            return db.query(FileMetadata).filter(FileMetadata.id == file_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get file metadata {file_id}: {e}")
            raise
    
    def get_by_task_id(self, task_id: UUID) -> List[FileMetadata]:
        """
        Get all file metadata for a task.
        
        Args:
            task_id: Task UUID
            
        Returns:
            List of file metadata records
        """
        try:
            db = self._get_session()
            return db.query(FileMetadata).filter(
                FileMetadata.task_id == task_id
            ).order_by(asc(FileMetadata.created_at)).all()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get file metadata for task {task_id}: {e}")
            raise
    
    def get_expired_files(self, batch_size: int = 100) -> List[FileMetadata]:
        """
        Get files that have expired and should be cleaned up.
        
        Args:
            batch_size: Maximum number of files to return
            
        Returns:
            List of expired file metadata records
        """
        try:
            db = self._get_session()
            now = datetime.now(timezone.utc)
            
            expired_files = db.query(FileMetadata).filter(
                and_(
                    FileMetadata.storage_policy == StoragePolicyEnum.TEMPORARY,
                    FileMetadata.expires_at < now
                )
            ).limit(batch_size).all()
            
            return expired_files
        except SQLAlchemyError as e:
            logger.error(f"Failed to get expired files: {e}")
            raise
    
    def get_files_by_storage_policy(
        self, 
        policy: StoragePolicyEnum, 
        limit: int = 100
    ) -> List[FileMetadata]:
        """
        Get files by storage policy.
        
        Args:
            policy: Storage policy to filter by
            limit: Maximum number of files to return
            
        Returns:
            List of file metadata records
        """
        try:
            db = self._get_session()
            return db.query(FileMetadata).filter(
                FileMetadata.storage_policy == policy
            ).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get files by storage policy {policy}: {e}")
            raise
    
    def update_expiry(self, file_id: UUID, expires_at: datetime) -> Optional[FileMetadata]:
        """
        Update file expiry time.
        
        Args:
            file_id: File metadata UUID
            expires_at: New expiry datetime
            
        Returns:
            Updated file metadata or None if not found
        """
        try:
            db = self._get_session()
            file_metadata = db.query(FileMetadata).filter(FileMetadata.id == file_id).first()
            
            if not file_metadata:
                return None
            
            file_metadata.expires_at = expires_at
            db.commit()
            db.refresh(file_metadata)
            logger.info(f"Updated expiry for file {file_id}")
            return file_metadata
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Failed to update file expiry {file_id}: {e}")
            raise
    
    def delete(self, file_id: UUID) -> bool:
        """
        Delete file metadata record.
        
        Args:
            file_id: File metadata UUID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            db = self._get_session()
            file_metadata = db.query(FileMetadata).filter(FileMetadata.id == file_id).first()
            
            if not file_metadata:
                return False
            
            db.delete(file_metadata)
            db.commit()
            logger.info(f"Deleted file metadata {file_id}")
            return True
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Failed to delete file metadata {file_id}: {e}")
            raise
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """
        Get storage usage statistics.
        
        Returns:
            Dictionary with storage statistics
        """
        try:
            db = self._get_session()
            
            # Get total file count and size by storage policy
            stats = {}
            for policy in StoragePolicyEnum:
                result = db.query(
                    func.count(FileMetadata.id).label('file_count'),
                    func.sum(FileMetadata.file_size).label('total_size')
                ).filter(FileMetadata.storage_policy == policy).first()
                
                stats[policy.value] = {
                    'file_count': result.file_count or 0,
                    'total_size_bytes': int(result.total_size) if result.total_size else 0
                }
            
            # Get expired file count
            now = datetime.now(timezone.utc)
            expired_count = db.query(FileMetadata).filter(
                and_(
                    FileMetadata.storage_policy == StoragePolicyEnum.TEMPORARY,
                    FileMetadata.expires_at < now
                )
            ).count()
            
            stats['expired_files'] = expired_count
            
            # Get file type distribution
            file_types = db.query(
                FileMetadata.file_type,
                func.count(FileMetadata.id).label('count')
            ).group_by(FileMetadata.file_type).all()
            
            stats['file_types'] = {
                file_type: count for file_type, count in file_types
            }
            
            return stats
        except SQLAlchemyError as e:
            logger.error(f"Failed to get storage statistics: {e}")
            raise


# Transaction management utilities

def with_transaction(func):
    """
    Decorator for repository methods that need transaction management.
    
    Args:
        func: Repository method to wrap
        
    Returns:
        Wrapped function with transaction management
    """
    def wrapper(*args, **kwargs):
        try:
            with get_db_session() as db:
                # Inject db session into repository if it doesn't have one
                if hasattr(args[0], 'db') and args[0].db is None:
                    args[0].db = db
                
                result = func(*args, **kwargs)
                return result
        except Exception as e:
            logger.error(f"Transaction failed in {func.__name__}: {e}")
            raise
    return wrapper


def bulk_create_tasks(task_data_list: List[Dict[str, Any]]) -> List[Task]:
    """
    Create multiple tasks in a single transaction.
    
    Args:
        task_data_list: List of task data dictionaries
        
    Returns:
        List of created tasks
    """
    try:
        with get_db_session() as db:
            tasks = [Task(**task_data) for task_data in task_data_list]
            db.add_all(tasks)
            db.commit()
            
            for task in tasks:
                db.refresh(task)
            
            logger.info(f"Bulk created {len(tasks)} tasks")
            return tasks
    except SQLAlchemyError as e:
        logger.error(f"Failed to bulk create tasks: {e}")
        raise


def bulk_update_task_status(
    task_ids: List[UUID], 
    status: TaskStatusEnum,
    error_message: Optional[str] = None
) -> int:
    """
    Update status for multiple tasks in a single transaction.
    
    Args:
        task_ids: List of task UUIDs
        status: New status for all tasks
        error_message: Optional error message
        
    Returns:
        Number of tasks updated
    """
    try:
        with get_db_session() as db:
            update_data = {
                'status': status,
                'updated_at': datetime.now(timezone.utc)
            }
            
            if status in [TaskStatusEnum.COMPLETED, TaskStatusEnum.FAILED, TaskStatusEnum.CANCELLED]:
                update_data['completed_at'] = datetime.now(timezone.utc)
            
            if error_message:
                update_data['error_message'] = error_message
            
            updated_count = db.query(Task).filter(
                Task.id.in_(task_ids)
            ).update(update_data, synchronize_session=False)
            
            db.commit()
            logger.info(f"Bulk updated {updated_count} tasks to status {status.value}")
            return updated_count
    except SQLAlchemyError as e:
        logger.error(f"Failed to bulk update task status: {e}")
        raise