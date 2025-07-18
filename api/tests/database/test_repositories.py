"""Unit tests for database repositories."""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

# Mock the settings to avoid configuration validation errors
with patch('src.config.Settings') as mock_settings_class:
    mock_settings = Mock()
    mock_settings.database_url = "postgresql://test:test@localhost/test"
    mock_settings.redis_url = "redis://localhost:6379"
    mock_settings.celery_broker_url = "redis://localhost:6379"
    mock_settings.celery_result_backend = "redis://localhost:6379"
    mock_settings.s3_endpoint_url = "http://localhost:9000"
    mock_settings.s3_access_key_id = "test"
    mock_settings.s3_secret_access_key = "test"
    mock_settings.s3_bucket_name = "test"
    mock_settings.secret_key = "test"
    mock_settings.jwt_secret_key = "test"
    mock_settings.environment = "development"
    mock_settings_class.return_value = mock_settings
    
    from src.database.models import Task, FileMetadata, TaskStatusEnum, StoragePolicyEnum
    from src.database.repositories import TaskRepository, FileMetadataRepository, bulk_create_tasks


class TestTaskRepository:
    """Test cases for TaskRepository."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def task_repo(self, mock_db):
        """Create TaskRepository instance with mock database."""
        return TaskRepository(db=mock_db)
    
    @pytest.fixture
    def sample_task_data(self):
        """Sample task data for testing."""
        return {
            'user_id': 'test_user',
            'task_type': 'document_parsing',
            'file_url': 'https://example.com/file.pdf',
            'original_filename': 'test.pdf',
            'options': {'enable_vectorization': True},
            'estimated_cost': 1.50
        }
    
    def test_create_task_success(self, task_repo, mock_db, sample_task_data):
        """Test successful task creation."""
        # Arrange
        mock_task = Mock(spec=Task)
        mock_task.id = uuid.uuid4()
        mock_task.user_id = sample_task_data['user_id']
        
        with patch('src.database.repositories.Task') as mock_task_class:
            mock_task_class.return_value = mock_task
            
            # Act
            result = task_repo.create(sample_task_data)
            
            # Assert
            mock_task_class.assert_called_once_with(**sample_task_data)
            mock_db.add.assert_called_once_with(mock_task)
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(mock_task)
            assert result == mock_task
    
    def test_create_task_failure(self, task_repo, mock_db, sample_task_data):
        """Test task creation failure with database error."""
        # Arrange
        mock_db.commit.side_effect = SQLAlchemyError("Database error")
        
        with patch('src.database.repositories.Task'):
            # Act & Assert
            with pytest.raises(SQLAlchemyError):
                task_repo.create(sample_task_data)
            
            mock_db.rollback.assert_called_once()
    
    def test_get_by_id_success(self, task_repo, mock_db):
        """Test successful task retrieval by ID."""
        # Arrange
        task_id = uuid.uuid4()
        mock_task = Mock(spec=Task)
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_task
        
        # Act
        result = task_repo.get_by_id(task_id)
        
        # Assert
        mock_db.query.assert_called_once_with(Task)
        assert result == mock_task
    
    def test_get_by_id_not_found(self, task_repo, mock_db):
        """Test task retrieval when task not found."""
        # Arrange
        task_id = uuid.uuid4()
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        # Act
        result = task_repo.get_by_id(task_id)
        
        # Assert
        assert result is None
    
    def test_get_by_user_id_with_filters(self, task_repo, mock_db):
        """Test getting tasks by user ID with filters."""
        # Arrange
        user_id = 'test_user'
        mock_tasks = [Mock(spec=Task), Mock(spec=Task)]
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_tasks
        
        # Act
        result = task_repo.get_by_user_id(
            user_id, 
            limit=10, 
            offset=0,
            status_filter=TaskStatusEnum.PENDING
        )
        
        # Assert
        assert result == mock_tasks
        assert mock_query.filter.call_count >= 2  # user_id and status filters
    
    def test_update_status_success(self, task_repo, mock_db):
        """Test successful task status update."""
        # Arrange
        task_id = uuid.uuid4()
        mock_task = Mock(spec=Task)
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_task
        
        # Act
        result = task_repo.update_status(
            task_id, 
            TaskStatusEnum.COMPLETED,
            results={'extracted_text': 'test'}
        )
        
        # Assert
        mock_task.update_status.assert_called_once_with(TaskStatusEnum.COMPLETED, None)
        assert mock_task.results == {'extracted_text': 'test'}
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_task)
        assert result == mock_task
    
    def test_update_status_task_not_found(self, task_repo, mock_db):
        """Test status update when task not found."""
        # Arrange
        task_id = uuid.uuid4()
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        # Act
        result = task_repo.update_status(task_id, TaskStatusEnum.COMPLETED)
        
        # Assert
        assert result is None
        mock_db.commit.assert_not_called()
    
    def test_get_pending_tasks(self, task_repo, mock_db):
        """Test getting pending tasks."""
        # Arrange
        mock_tasks = [Mock(spec=Task), Mock(spec=Task)]
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_tasks
        
        # Act
        result = task_repo.get_pending_tasks(limit=50)
        
        # Assert
        assert result == mock_tasks
        mock_query.filter.assert_called_once()
    
    def test_get_processing_tasks(self, task_repo, mock_db):
        """Test getting stuck processing tasks."""
        # Arrange
        mock_tasks = [Mock(spec=Task)]
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = mock_tasks
        
        # Act
        result = task_repo.get_processing_tasks(older_than_minutes=30)
        
        # Assert
        assert result == mock_tasks
    
    def test_delete_task_success(self, task_repo, mock_db):
        """Test successful task deletion."""
        # Arrange
        task_id = uuid.uuid4()
        mock_task = Mock(spec=Task)
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_task
        
        # Act
        result = task_repo.delete(task_id)
        
        # Assert
        mock_db.delete.assert_called_once_with(mock_task)
        mock_db.commit.assert_called_once()
        assert result is True
    
    def test_delete_task_not_found(self, task_repo, mock_db):
        """Test task deletion when task not found."""
        # Arrange
        task_id = uuid.uuid4()
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        # Act
        result = task_repo.delete(task_id)
        
        # Assert
        mock_db.delete.assert_not_called()
        assert result is False
    
    def test_get_task_statistics(self, task_repo, mock_db):
        """Test getting task statistics."""
        # Arrange
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 10
        
        # Mock completed tasks for processing time calculation
        mock_completed_task = Mock()
        mock_completed_task.completed_at = datetime.now(timezone.utc)
        mock_completed_task.created_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        mock_query.all.return_value = [mock_completed_task]
        
        # Mock cost statistics
        mock_cost_result = Mock()
        mock_cost_result.total_cost = 100.0
        mock_cost_result.avg_cost = 10.0
        mock_cost_result.tasks_with_cost = 10
        mock_query.first.return_value = mock_cost_result
        
        # Act
        result = task_repo.get_task_statistics()
        
        # Assert
        assert 'total_tasks' in result
        assert 'status_counts' in result
        assert 'avg_processing_time_seconds' in result
        assert 'total_cost' in result
        assert 'avg_cost' in result


class TestFileMetadataRepository:
    """Test cases for FileMetadataRepository."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def file_repo(self, mock_db):
        """Create FileMetadataRepository instance with mock database."""
        return FileMetadataRepository(db=mock_db)
    
    @pytest.fixture
    def sample_file_data(self):
        """Sample file metadata for testing."""
        return {
            'task_id': uuid.uuid4(),
            'original_filename': 'test.pdf',
            'file_type': 'pdf',
            'file_size': 1024000,
            'storage_path': '/storage/test.pdf',
            'storage_policy': StoragePolicyEnum.TEMPORARY,
            'expires_at': datetime.now(timezone.utc) + timedelta(hours=24)
        }
    
    def test_create_file_metadata_success(self, file_repo, mock_db, sample_file_data):
        """Test successful file metadata creation."""
        # Arrange
        mock_file = Mock(spec=FileMetadata)
        mock_file.id = uuid.uuid4()
        mock_file.task_id = sample_file_data['task_id']
        
        with patch('src.database.repositories.FileMetadata') as mock_file_class:
            mock_file_class.return_value = mock_file
            
            # Act
            result = file_repo.create(sample_file_data)
            
            # Assert
            mock_file_class.assert_called_once_with(**sample_file_data)
            mock_db.add.assert_called_once_with(mock_file)
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(mock_file)
            assert result == mock_file
    
    def test_get_by_task_id(self, file_repo, mock_db):
        """Test getting file metadata by task ID."""
        # Arrange
        task_id = uuid.uuid4()
        mock_files = [Mock(spec=FileMetadata), Mock(spec=FileMetadata)]
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_files
        
        # Act
        result = file_repo.get_by_task_id(task_id)
        
        # Assert
        assert result == mock_files
        mock_db.query.assert_called_once_with(FileMetadata)
    
    def test_get_expired_files(self, file_repo, mock_db):
        """Test getting expired files."""
        # Arrange
        mock_files = [Mock(spec=FileMetadata)]
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_files
        
        # Act
        result = file_repo.get_expired_files(batch_size=50)
        
        # Assert
        assert result == mock_files
    
    def test_update_expiry_success(self, file_repo, mock_db):
        """Test successful expiry update."""
        # Arrange
        file_id = uuid.uuid4()
        new_expiry = datetime.now(timezone.utc) + timedelta(hours=48)
        mock_file = Mock(spec=FileMetadata)
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_file
        
        # Act
        result = file_repo.update_expiry(file_id, new_expiry)
        
        # Assert
        assert mock_file.expires_at == new_expiry
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_file)
        assert result == mock_file
    
    def test_delete_file_metadata_success(self, file_repo, mock_db):
        """Test successful file metadata deletion."""
        # Arrange
        file_id = uuid.uuid4()
        mock_file = Mock(spec=FileMetadata)
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_file
        
        # Act
        result = file_repo.delete(file_id)
        
        # Assert
        mock_db.delete.assert_called_once_with(mock_file)
        mock_db.commit.assert_called_once()
        assert result is True
    
    def test_get_storage_statistics(self, file_repo, mock_db):
        """Test getting storage statistics."""
        # Arrange
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        
        # Mock storage policy stats
        mock_result = Mock()
        mock_result.file_count = 10
        mock_result.total_size = 1024000
        mock_query.first.return_value = mock_result
        
        # Mock expired files count
        mock_query.count.return_value = 5
        
        # Mock file types
        mock_query.all.return_value = [('pdf', 5), ('docx', 3), ('txt', 2)]
        
        # Act
        result = file_repo.get_storage_statistics()
        
        # Assert
        assert 'permanent' in result
        assert 'temporary' in result
        assert 'expired_files' in result
        assert 'file_types' in result


class TestBulkOperations:
    """Test cases for bulk repository operations."""
    
    @patch('src.database.repositories.get_db_session')
    def test_bulk_create_tasks_success(self, mock_get_db_session):
        """Test successful bulk task creation."""
        # Arrange
        mock_db = Mock()
        mock_get_db_session.return_value.__enter__.return_value = mock_db
        
        task_data_list = [
            {'user_id': 'user1', 'task_type': 'document_parsing'},
            {'user_id': 'user2', 'task_type': 'archive_processing'}
        ]
        
        with patch('src.database.repositories.Task') as mock_task_class:
            mock_tasks = [Mock(spec=Task), Mock(spec=Task)]
            mock_task_class.side_effect = mock_tasks
            
            # Act
            result = bulk_create_tasks(task_data_list)
            
            # Assert
            mock_db.add_all.assert_called_once()
            mock_db.commit.assert_called_once()
            assert len(result) == 2
    
    @patch('src.database.repositories.get_db_session')
    def test_bulk_create_tasks_failure(self, mock_get_db_session):
        """Test bulk task creation failure."""
        # Arrange
        mock_db = Mock()
        mock_db.commit.side_effect = SQLAlchemyError("Database error")
        mock_get_db_session.return_value.__enter__.return_value = mock_db
        
        task_data_list = [{'user_id': 'user1', 'task_type': 'document_parsing'}]
        
        # Act & Assert
        with pytest.raises(SQLAlchemyError):
            bulk_create_tasks(task_data_list)


if __name__ == '__main__':
    pytest.main([__file__])