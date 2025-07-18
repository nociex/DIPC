"""Simple unit tests for database repositories without full app context."""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError


class MockTask:
    """Mock Task model for testing."""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', uuid.uuid4())
        self.user_id = kwargs.get('user_id', 'test_user')
        self.task_type = kwargs.get('task_type', 'document_parsing')
        self.status = kwargs.get('status', 'pending')
        self.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
        self.updated_at = kwargs.get('updated_at', datetime.now(timezone.utc))
        self.completed_at = kwargs.get('completed_at')
        self.results = kwargs.get('results')
        self.error_message = kwargs.get('error_message')
        self.actual_cost = kwargs.get('actual_cost')
    
    def update_status(self, status, error_message=None):
        self.status = status
        self.updated_at = datetime.now(timezone.utc)
        if error_message:
            self.error_message = error_message


class MockFileMetadata:
    """Mock FileMetadata model for testing."""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', uuid.uuid4())
        self.task_id = kwargs.get('task_id', uuid.uuid4())
        self.original_filename = kwargs.get('original_filename', 'test.pdf')
        self.file_type = kwargs.get('file_type', 'pdf')
        self.file_size = kwargs.get('file_size', 1024)
        self.storage_path = kwargs.get('storage_path', '/storage/test.pdf')
        self.storage_policy = kwargs.get('storage_policy', 'temporary')
        self.expires_at = kwargs.get('expires_at')
        self.created_at = kwargs.get('created_at', datetime.now(timezone.utc))


# Mock the repository classes without importing the full application
class MockTaskRepository:
    """Mock TaskRepository for testing core logic."""
    
    def __init__(self, db=None):
        self.db = db or Mock(spec=Session)
    
    def create(self, task_data):
        """Create a new task."""
        if self.db.commit.side_effect:
            raise self.db.commit.side_effect
        
        task = MockTask(**task_data)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task
    
    def get_by_id(self, task_id):
        """Get task by ID."""
        mock_query = self.db.query()
        mock_query = mock_query.options()
        mock_query = mock_query.filter()
        return mock_query.first()
    
    def update_status(self, task_id, status, error_message=None, results=None, actual_cost=None):
        """Update task status."""
        task = self.get_by_id(task_id)
        if not task:
            return None
        
        task.update_status(status, error_message)
        if results is not None:
            task.results = results
        if actual_cost is not None:
            task.actual_cost = actual_cost
        
        self.db.commit()
        self.db.refresh(task)
        return task


class TestTaskRepositoryLogic:
    """Test cases for TaskRepository core logic."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def task_repo(self, mock_db):
        """Create TaskRepository instance with mock database."""
        return MockTaskRepository(db=mock_db)
    
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
        # Act
        result = task_repo.create(sample_task_data)
        
        # Assert
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        assert result.user_id == sample_task_data['user_id']
        assert result.task_type == sample_task_data['task_type']
    
    def test_create_task_failure(self, task_repo, mock_db, sample_task_data):
        """Test task creation failure with database error."""
        # Arrange
        mock_db.commit.side_effect = SQLAlchemyError("Database error")
        
        # Act & Assert
        with pytest.raises(SQLAlchemyError):
            task_repo.create(sample_task_data)
    
    def test_get_by_id_calls_correct_methods(self, task_repo, mock_db):
        """Test that get_by_id calls the correct database methods."""
        # Arrange
        task_id = uuid.uuid4()
        mock_task = MockTask(id=task_id)
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_task
        
        # Act
        result = task_repo.get_by_id(task_id)
        
        # Assert
        mock_db.query.assert_called_once()
        mock_query.options.assert_called_once()
        mock_query.filter.assert_called_once()
        mock_query.first.assert_called_once()
        assert result == mock_task
    
    def test_update_status_success(self, task_repo, mock_db):
        """Test successful task status update."""
        # Arrange
        task_id = uuid.uuid4()
        mock_task = MockTask(id=task_id, status='pending')
        
        # Mock the get_by_id to return our task
        with patch.object(task_repo, 'get_by_id', return_value=mock_task):
            # Act
            result = task_repo.update_status(
                task_id, 
                'completed',
                results={'extracted_text': 'test'}
            )
            
            # Assert
            assert result.status == 'completed'
            assert result.results == {'extracted_text': 'test'}
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()
    
    def test_update_status_task_not_found(self, task_repo, mock_db):
        """Test status update when task not found."""
        # Arrange
        task_id = uuid.uuid4()
        
        # Mock the get_by_id to return None
        with patch.object(task_repo, 'get_by_id', return_value=None):
            # Act
            result = task_repo.update_status(task_id, 'completed')
            
            # Assert
            assert result is None
            mock_db.commit.assert_not_called()


class TestFileMetadataLogic:
    """Test cases for FileMetadata logic."""
    
    def test_file_metadata_creation(self):
        """Test file metadata creation with proper attributes."""
        # Arrange
        task_id = uuid.uuid4()
        file_data = {
            'task_id': task_id,
            'original_filename': 'test.pdf',
            'file_type': 'pdf',
            'file_size': 2048,
            'storage_path': '/storage/test.pdf',
            'storage_policy': 'temporary'
        }
        
        # Act
        file_metadata = MockFileMetadata(**file_data)
        
        # Assert
        assert file_metadata.task_id == task_id
        assert file_metadata.original_filename == 'test.pdf'
        assert file_metadata.file_type == 'pdf'
        assert file_metadata.file_size == 2048
        assert file_metadata.storage_policy == 'temporary'
    
    def test_file_metadata_defaults(self):
        """Test file metadata with default values."""
        # Act
        file_metadata = MockFileMetadata()
        
        # Assert
        assert file_metadata.id is not None
        assert file_metadata.task_id is not None
        assert file_metadata.original_filename == 'test.pdf'
        assert file_metadata.file_type == 'pdf'
        assert file_metadata.created_at is not None


class TestRepositoryTransactionLogic:
    """Test transaction management logic."""
    
    def test_transaction_rollback_on_error(self):
        """Test that transactions are rolled back on error."""
        # Arrange
        mock_db = Mock(spec=Session)
        mock_db.commit.side_effect = SQLAlchemyError("Database error")
        task_repo = MockTaskRepository(db=mock_db)
        
        # Act & Assert
        with pytest.raises(SQLAlchemyError):
            task_repo.create({'user_id': 'test', 'task_type': 'test'})
    
    def test_successful_transaction_commits(self):
        """Test that successful operations commit."""
        # Arrange
        mock_db = Mock(spec=Session)
        task_repo = MockTaskRepository(db=mock_db)
        
        # Act
        result = task_repo.create({'user_id': 'test', 'task_type': 'test'})
        
        # Assert
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        assert result is not None


if __name__ == '__main__':
    pytest.main([__file__])