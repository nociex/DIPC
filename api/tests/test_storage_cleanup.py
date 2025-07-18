"""Tests for storage cleanup functionality."""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

from src.storage.cleanup import StorageCleanupService, CleanupResult
from src.database.models import FileMetadata, StoragePolicyEnum, Task, TaskStatusEnum


class TestStorageCleanupService:
    """Test storage cleanup service functionality."""
    
    @pytest.fixture
    def mock_s3_client(self):
        """Mock S3 client."""
        return Mock()
    
    @pytest.fixture
    def cleanup_service(self, mock_s3_client):
        """Storage cleanup service with mocked S3."""
        return StorageCleanupService(s3_client=mock_s3_client)
    
    @pytest.fixture
    def sample_expired_files(self, db_session):
        """Create sample expired files for testing."""
        task = Task(
            user_id="test_user",
            task_type="document_parsing",
            status=TaskStatusEnum.COMPLETED
        )
        db_session.add(task)
        db_session.flush()
        
        # Expired file 1
        expired_file1 = FileMetadata(
            task_id=task.id,
            original_filename="expired1.pdf",
            file_type="pdf",
            file_size=1000000,
            storage_path="files/expired1.pdf",
            storage_policy=StoragePolicyEnum.TEMPORARY,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        
        # Expired file 2
        expired_file2 = FileMetadata(
            task_id=task.id,
            original_filename="expired2.pdf",
            file_type="pdf",
            file_size=500000,
            storage_path="files/expired2.pdf",
            storage_policy=StoragePolicyEnum.TEMPORARY,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=2)
        )
        
        # Non-expired file (should not be cleaned)
        active_file = FileMetadata(
            task_id=task.id,
            original_filename="active.pdf",
            file_type="pdf",
            file_size=300000,
            storage_path="files/active.pdf",
            storage_policy=StoragePolicyEnum.TEMPORARY,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=12)
        )
        
        # Permanent file (should not be cleaned)
        permanent_file = FileMetadata(
            task_id=task.id,
            original_filename="permanent.pdf",
            file_type="pdf",
            file_size=200000,
            storage_path="files/permanent.pdf",
            storage_policy=StoragePolicyEnum.PERMANENT
        )
        
        db_session.add_all([expired_file1, expired_file2, active_file, permanent_file])
        db_session.commit()
        
        return [expired_file1, expired_file2]
    
    def test_get_expired_files(self, cleanup_service, sample_expired_files):
        """Test getting expired files."""
        expired_files = cleanup_service.get_expired_files(limit=10)
        
        assert len(expired_files) == 2
        assert all(file.is_expired() for file in expired_files)
        assert all(file.storage_policy == StoragePolicyEnum.TEMPORARY for file in expired_files)
    
    def test_get_expired_files_with_limit(self, cleanup_service, sample_expired_files):
        """Test getting expired files with limit."""
        expired_files = cleanup_service.get_expired_files(limit=1)
        
        assert len(expired_files) == 1
        assert expired_files[0].is_expired()
    
    def test_delete_file_from_storage_success(self, cleanup_service):
        """Test successful file deletion from S3."""
        cleanup_service.s3_client.delete_object.return_value = {}
        
        result = cleanup_service.delete_file_from_storage("files/test.pdf")
        
        assert result is True
        cleanup_service.s3_client.delete_object.assert_called_once_with(
            Bucket=cleanup_service.bucket_name,
            Key="files/test.pdf"
        )
    
    def test_delete_file_from_storage_not_found(self, cleanup_service):
        """Test file deletion when file not found in S3."""
        cleanup_service.s3_client.delete_object.side_effect = ClientError(
            error_response={'Error': {'Code': 'NoSuchKey'}},
            operation_name='DeleteObject'
        )
        
        result = cleanup_service.delete_file_from_storage("files/nonexistent.pdf")
        
        assert result is True  # Missing file considered successfully "deleted"
    
    def test_delete_file_from_storage_error(self, cleanup_service):
        """Test file deletion with S3 error."""
        cleanup_service.s3_client.delete_object.side_effect = ClientError(
            error_response={'Error': {'Code': 'AccessDenied'}},
            operation_name='DeleteObject'
        )
        
        result = cleanup_service.delete_file_from_storage("files/test.pdf")
        
        assert result is False
    
    @patch('src.storage.cleanup.get_db_session')
    def test_delete_file_metadata_success(self, mock_get_db_session, cleanup_service):
        """Test successful file metadata deletion."""
        mock_db = Mock()
        mock_get_db_session.return_value.__enter__.return_value = mock_db
        
        mock_file = Mock()
        mock_file.id = uuid.uuid4()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_file
        
        file_metadata = Mock()
        file_metadata.id = mock_file.id
        
        result = cleanup_service.delete_file_metadata(file_metadata)
        
        assert result is True
        mock_db.delete.assert_called_once_with(mock_file)
        mock_db.commit.assert_called_once()
    
    @patch('src.storage.cleanup.get_db_session')
    def test_delete_file_metadata_not_found(self, mock_get_db_session, cleanup_service):
        """Test file metadata deletion when not found."""
        mock_db = Mock()
        mock_get_db_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        file_metadata = Mock()
        file_metadata.id = uuid.uuid4()
        
        result = cleanup_service.delete_file_metadata(file_metadata)
        
        assert result is True  # Missing metadata considered successfully "deleted"
    
    def test_cleanup_expired_files_dry_run(self, cleanup_service, sample_expired_files):
        """Test cleanup in dry run mode."""
        result = cleanup_service.cleanup_expired_files(batch_size=10, dry_run=True)
        
        assert isinstance(result, CleanupResult)
        assert result.files_processed == 2
        assert result.files_deleted == 2
        assert result.bytes_freed == 1500000  # 1MB + 500KB
        assert len(result.errors) == 0
        assert result.duration_seconds > 0
        
        # Verify no actual deletion calls were made
        cleanup_service.s3_client.delete_object.assert_not_called()
    
    @patch('src.storage.cleanup.get_db_session')
    def test_cleanup_expired_files_success(self, mock_get_db_session, cleanup_service, sample_expired_files):
        """Test successful cleanup of expired files."""
        # Mock database operations
        mock_db = Mock()
        mock_get_db_session.return_value.__enter__.return_value = mock_db
        
        # Mock file queries for deletion
        mock_db.query.return_value.filter.return_value.first.side_effect = sample_expired_files
        
        # Mock S3 operations
        cleanup_service.s3_client.delete_object.return_value = {}
        
        result = cleanup_service.cleanup_expired_files(batch_size=10, dry_run=False)
        
        assert result.files_processed == 2
        assert result.files_deleted == 2
        assert result.bytes_freed == 1500000
        assert len(result.errors) == 0
        
        # Verify S3 deletion calls
        assert cleanup_service.s3_client.delete_object.call_count == 2
        
        # Verify database deletion calls
        assert mock_db.delete.call_count == 2
        assert mock_db.commit.call_count == 2
    
    def test_cleanup_orphaned_files_dry_run(self, cleanup_service):
        """Test orphaned files cleanup in dry run mode."""
        # Mock database paths
        with patch('src.storage.cleanup.get_db_session') as mock_get_db_session:
            mock_db = Mock()
            mock_get_db_session.return_value.__enter__.return_value = mock_db
            mock_db.query.return_value.all.return_value = [("files/existing.pdf",)]
            
            # Mock S3 objects
            mock_paginator = Mock()
            cleanup_service.s3_client.get_paginator.return_value = mock_paginator
            mock_paginator.paginate.return_value = [
                {
                    'Contents': [
                        {'Key': 'files/existing.pdf', 'Size': 1000},
                        {'Key': 'files/orphaned.pdf', 'Size': 2000}
                    ]
                }
            ]
            
            result = cleanup_service.cleanup_orphaned_files(dry_run=True)
            
            assert result.files_processed == 2
            assert result.files_deleted == 1  # Only orphaned file
            assert result.bytes_freed == 2000
            assert len(result.errors) == 0
            
            # Verify no actual deletion
            cleanup_service.s3_client.delete_object.assert_not_called()
    
    def test_cleanup_orphaned_files_success(self, cleanup_service):
        """Test successful orphaned files cleanup."""
        # Mock database paths
        with patch('src.storage.cleanup.get_db_session') as mock_get_db_session:
            mock_db = Mock()
            mock_get_db_session.return_value.__enter__.return_value = mock_db
            mock_db.query.return_value.all.return_value = [("files/existing.pdf",)]
            
            # Mock S3 objects
            mock_paginator = Mock()
            cleanup_service.s3_client.get_paginator.return_value = mock_paginator
            mock_paginator.paginate.return_value = [
                {
                    'Contents': [
                        {'Key': 'files/existing.pdf', 'Size': 1000},
                        {'Key': 'files/orphaned.pdf', 'Size': 2000}
                    ]
                }
            ]
            
            # Mock S3 deletion
            cleanup_service.s3_client.delete_object.return_value = {}
            
            result = cleanup_service.cleanup_orphaned_files(dry_run=False)
            
            assert result.files_processed == 2
            assert result.files_deleted == 1
            assert result.bytes_freed == 2000
            assert len(result.errors) == 0
            
            # Verify S3 deletion call
            cleanup_service.s3_client.delete_object.assert_called_once_with(
                Bucket=cleanup_service.bucket_name,
                Key='files/orphaned.pdf'
            )
    
    def test_get_cleanup_candidates(self, cleanup_service, sample_expired_files):
        """Test getting cleanup candidates."""
        # Create a file that will expire soon
        with patch('src.storage.cleanup.get_db_session') as mock_get_db_session:
            mock_db = Mock()
            mock_get_db_session.return_value.__enter__.return_value = mock_db
            
            # Mock file that expires in 12 hours
            expiring_file = Mock()
            expiring_file.id = uuid.uuid4()
            expiring_file.original_filename = "expiring.pdf"
            expiring_file.file_size = 1000
            expiring_file.expires_at = datetime.now(timezone.utc) + timedelta(hours=12)
            expiring_file.storage_path = "files/expiring.pdf"
            expiring_file.task_id = uuid.uuid4()
            
            mock_db.query.return_value.filter.return_value.all.return_value = [expiring_file]
            
            candidates = cleanup_service.get_cleanup_candidates(days_ahead=1)
            
            assert len(candidates) == 1
            assert candidates[0]["filename"] == "expiring.pdf"
            assert candidates[0]["size_bytes"] == 1000
    
    @patch('src.storage.cleanup.get_db_session')
    def test_extend_file_ttl_success(self, mock_get_db_session, cleanup_service):
        """Test successful TTL extension."""
        mock_db = Mock()
        mock_get_db_session.return_value.__enter__.return_value = mock_db
        
        # Mock file metadata
        mock_file = Mock()
        mock_file.id = str(uuid.uuid4())
        mock_file.storage_policy = StoragePolicyEnum.TEMPORARY
        mock_file.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_file
        
        result = cleanup_service.extend_file_ttl(mock_file.id, additional_hours=24)
        
        assert result is True
        assert mock_file.expires_at > datetime.now(timezone.utc) + timedelta(hours=20)
        mock_db.commit.assert_called_once()
    
    @patch('src.storage.cleanup.get_db_session')
    def test_extend_file_ttl_not_found(self, mock_get_db_session, cleanup_service):
        """Test TTL extension when file not found."""
        mock_db = Mock()
        mock_get_db_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = cleanup_service.extend_file_ttl(str(uuid.uuid4()), additional_hours=24)
        
        assert result is False
    
    @patch('src.storage.cleanup.get_db_session')
    def test_extend_file_ttl_permanent_file(self, mock_get_db_session, cleanup_service):
        """Test TTL extension on permanent file (should fail)."""
        mock_db = Mock()
        mock_get_db_session.return_value.__enter__.return_value = mock_db
        
        # Mock permanent file
        mock_file = Mock()
        mock_file.id = str(uuid.uuid4())
        mock_file.storage_policy = StoragePolicyEnum.PERMANENT
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_file
        
        result = cleanup_service.extend_file_ttl(mock_file.id, additional_hours=24)
        
        assert result is False


@pytest.fixture
def db_session():
    """Mock database session for testing."""
    from unittest.mock import Mock
    return Mock()


if __name__ == "__main__":
    pytest.main([__file__])