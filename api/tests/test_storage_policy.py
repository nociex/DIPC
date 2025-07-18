"""Tests for storage policy management."""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

from src.storage.policy import (
    StoragePolicyManager, 
    StorageUsageTracker,
    StoragePolicyConfig,
    StorageUsageStats
)
from src.database.models import FileMetadata, StoragePolicyEnum, Task, TaskStatusEnum
from src.config import settings


class TestStoragePolicyManager:
    """Test storage policy management functionality."""
    
    @pytest.fixture
    def mock_s3_client(self):
        """Mock S3 client."""
        return Mock()
    
    @pytest.fixture
    def policy_manager(self, mock_s3_client):
        """Storage policy manager with mocked S3."""
        return StoragePolicyManager(s3_client=mock_s3_client)
    
    @pytest.fixture
    def sample_file_metadata(self, db_session):
        """Create sample file metadata."""
        task = Task(
            user_id="test_user",
            task_type="document_parsing",
            status=TaskStatusEnum.COMPLETED
        )
        db_session.add(task)
        db_session.flush()
        
        file_metadata = FileMetadata(
            task_id=task.id,
            original_filename="test_document.pdf",
            file_type="pdf",
            file_size=1024000,
            storage_path="files/test_document.pdf",
            storage_policy=StoragePolicyEnum.TEMPORARY
        )
        db_session.add(file_metadata)
        db_session.commit()
        
        return file_metadata
    
    def test_storage_policy_config_initialization(self):
        """Test storage policy configuration initialization."""
        # Test temporary policy with default TTL
        config = StoragePolicyConfig(policy=StoragePolicyEnum.TEMPORARY)
        assert config.policy == StoragePolicyEnum.TEMPORARY
        assert config.ttl_hours == settings.temp_file_ttl_hours
        
        # Test permanent policy
        config = StoragePolicyConfig(policy=StoragePolicyEnum.PERMANENT)
        assert config.policy == StoragePolicyEnum.PERMANENT
        assert config.ttl_hours is None
        
        # Test custom TTL
        config = StoragePolicyConfig(
            policy=StoragePolicyEnum.TEMPORARY,
            ttl_hours=48
        )
        assert config.ttl_hours == 48
    
    def test_apply_storage_policy_temporary(self, policy_manager, sample_file_metadata):
        """Test applying temporary storage policy."""
        config = StoragePolicyConfig(
            policy=StoragePolicyEnum.TEMPORARY,
            ttl_hours=24
        )
        
        before_time = datetime.now(timezone.utc)
        updated_file = policy_manager.apply_storage_policy(sample_file_metadata, config)
        after_time = datetime.now(timezone.utc)
        
        assert updated_file.storage_policy == StoragePolicyEnum.TEMPORARY
        assert updated_file.expires_at is not None
        assert before_time + timedelta(hours=24) <= updated_file.expires_at <= after_time + timedelta(hours=24)
    
    def test_apply_storage_policy_permanent(self, policy_manager, sample_file_metadata):
        """Test applying permanent storage policy."""
        config = StoragePolicyConfig(policy=StoragePolicyEnum.PERMANENT)
        
        updated_file = policy_manager.apply_storage_policy(sample_file_metadata, config)
        
        assert updated_file.storage_policy == StoragePolicyEnum.PERMANENT
        assert updated_file.expires_at is None
    
    def test_validate_file_against_policy_size_limit(self, policy_manager):
        """Test file validation against size limits."""
        config = StoragePolicyConfig(
            policy=StoragePolicyEnum.TEMPORARY,
            max_file_size=1000000  # 1MB
        )
        
        # File within limit
        is_valid, error = policy_manager.validate_file_against_policy(
            file_size=500000,
            file_extension="pdf",
            policy_config=config
        )
        assert is_valid is True
        assert error is None
        
        # File exceeds limit
        is_valid, error = policy_manager.validate_file_against_policy(
            file_size=2000000,
            file_extension="pdf",
            policy_config=config
        )
        assert is_valid is False
        assert "exceeds policy limit" in error
    
    def test_validate_file_against_policy_extension(self, policy_manager):
        """Test file validation against allowed extensions."""
        config = StoragePolicyConfig(
            policy=StoragePolicyEnum.TEMPORARY,
            allowed_extensions=["pdf", "docx", "txt"]
        )
        
        # Allowed extension
        is_valid, error = policy_manager.validate_file_against_policy(
            file_size=1000,
            file_extension="pdf",
            policy_config=config
        )
        assert is_valid is True
        assert error is None
        
        # Disallowed extension
        is_valid, error = policy_manager.validate_file_against_policy(
            file_size=1000,
            file_extension="exe",
            policy_config=config
        )
        assert is_valid is False
        assert "not allowed by policy" in error
    
    def test_get_default_policy_config(self, policy_manager):
        """Test getting default policy configuration."""
        # Default temporary policy
        config = policy_manager.get_default_policy_config()
        assert config.policy == StoragePolicyEnum.TEMPORARY
        assert config.ttl_hours == settings.temp_file_ttl_hours
        
        # Override to permanent
        config = policy_manager.get_default_policy_config("permanent")
        assert config.policy == StoragePolicyEnum.PERMANENT
        assert config.ttl_hours is None
    
    @patch('src.storage.policy.get_db_session')
    def test_update_file_policy_success(self, mock_get_db_session, policy_manager):
        """Test successful file policy update."""
        # Mock database session and file metadata
        mock_db = Mock()
        mock_get_db_session.return_value.__enter__.return_value = mock_db
        
        mock_file = Mock()
        mock_file.id = str(uuid.uuid4())
        mock_file.storage_policy = StoragePolicyEnum.TEMPORARY
        mock_db.query.return_value.filter.return_value.first.return_value = mock_file
        
        result = policy_manager.update_file_policy(
            file_id=mock_file.id,
            new_policy=StoragePolicyEnum.PERMANENT
        )
        
        assert result is True
        assert mock_file.storage_policy == StoragePolicyEnum.PERMANENT
        assert mock_file.expires_at is None
        mock_db.commit.assert_called_once()
    
    @patch('src.storage.policy.get_db_session')
    def test_update_file_policy_not_found(self, mock_get_db_session, policy_manager):
        """Test file policy update when file not found."""
        mock_db = Mock()
        mock_get_db_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = policy_manager.update_file_policy(
            file_id=str(uuid.uuid4()),
            new_policy=StoragePolicyEnum.PERMANENT
        )
        
        assert result is False
    
    @patch('src.storage.policy.get_db_session')
    def test_enforce_storage_policies(self, mock_get_db_session, policy_manager):
        """Test storage policy enforcement."""
        mock_db = Mock()
        mock_get_db_session.return_value.__enter__.return_value = mock_db
        
        # Mock files needing policy updates
        mock_file1 = Mock()
        mock_file1.id = uuid.uuid4()
        mock_file1.storage_policy = StoragePolicyEnum.TEMPORARY
        mock_file1.expires_at = None
        
        mock_file2 = Mock()
        mock_file2.id = uuid.uuid4()
        mock_file2.storage_policy = StoragePolicyEnum.PERMANENT
        mock_file2.expires_at = None
        
        mock_db.query.return_value.all.return_value = [mock_file1, mock_file2]
        
        results = policy_manager.enforce_storage_policies()
        
        assert results["files_processed"] == 2
        assert results["policies_updated"] == 1  # Only temporary file updated
        assert len(results["errors"]) == 0
        assert mock_file1.expires_at is not None
        mock_db.commit.assert_called_once()


class TestStorageUsageTracker:
    """Test storage usage tracking functionality."""
    
    @pytest.fixture
    def mock_s3_client(self):
        """Mock S3 client."""
        return Mock()
    
    @pytest.fixture
    def usage_tracker(self, mock_s3_client):
        """Storage usage tracker with mocked S3."""
        return StorageUsageTracker(s3_client=mock_s3_client)
    
    @pytest.fixture
    def sample_files(self, db_session):
        """Create sample files for testing."""
        task = Task(
            user_id="test_user",
            task_type="document_parsing",
            status=TaskStatusEnum.COMPLETED
        )
        db_session.add(task)
        db_session.flush()
        
        # Permanent file
        permanent_file = FileMetadata(
            task_id=task.id,
            original_filename="permanent.pdf",
            file_type="pdf",
            file_size=1000000,
            storage_path="files/permanent.pdf",
            storage_policy=StoragePolicyEnum.PERMANENT
        )
        
        # Temporary file (not expired)
        temp_file = FileMetadata(
            task_id=task.id,
            original_filename="temp.pdf",
            file_type="pdf",
            file_size=500000,
            storage_path="files/temp.pdf",
            storage_policy=StoragePolicyEnum.TEMPORARY,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=12)
        )
        
        # Expired temporary file
        expired_file = FileMetadata(
            task_id=task.id,
            original_filename="expired.pdf",
            file_type="pdf",
            file_size=300000,
            storage_path="files/expired.pdf",
            storage_policy=StoragePolicyEnum.TEMPORARY,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        
        db_session.add_all([permanent_file, temp_file, expired_file])
        db_session.commit()
        
        return [permanent_file, temp_file, expired_file]
    
    def test_get_storage_usage_stats(self, usage_tracker, sample_files):
        """Test getting storage usage statistics."""
        stats = usage_tracker.get_storage_usage_stats()
        
        assert isinstance(stats, StorageUsageStats)
        assert stats.total_files == 3
        assert stats.total_size_bytes == 1800000  # 1MB + 500KB + 300KB
        assert stats.permanent_files == 1
        assert stats.permanent_size_bytes == 1000000
        assert stats.temporary_files == 2
        assert stats.temporary_size_bytes == 800000
        assert stats.expired_files == 1
        assert stats.expired_size_bytes == 300000
    
    def test_get_usage_by_user(self, usage_tracker, sample_files):
        """Test getting usage statistics by user."""
        usage = usage_tracker.get_usage_by_user("test_user")
        
        assert usage["user_id"] == "test_user"
        assert usage["total_files"] == 3
        assert usage["total_size_bytes"] == 1800000
        assert usage["permanent_files"] == 1
        assert usage["temporary_files"] == 2
        assert usage["expired_files"] == 1
    
    def test_get_usage_by_user_not_found(self, usage_tracker):
        """Test getting usage for non-existent user."""
        usage = usage_tracker.get_usage_by_user("nonexistent_user")
        
        assert usage["user_id"] == "nonexistent_user"
        assert usage["total_files"] == 0
        assert usage["total_size_bytes"] == 0
    
    def test_verify_s3_storage_consistency(self, usage_tracker, sample_files):
        """Test S3 storage consistency verification."""
        # Mock S3 paginator
        mock_paginator = Mock()
        usage_tracker.s3_client.get_paginator.return_value = mock_paginator
        
        # Mock S3 objects
        s3_objects = [
            {'Key': 'files/permanent.pdf', 'Size': 1000000},
            {'Key': 'files/temp.pdf', 'Size': 500000},
            {'Key': 'files/orphaned.pdf', 'Size': 200000}  # Not in database
            # Missing files/expired.pdf (in database but not S3)
        ]
        
        mock_paginator.paginate.return_value = [{'Contents': s3_objects}]
        
        results = usage_tracker.verify_s3_storage_consistency()
        
        assert results["database_files"] == 3
        assert results["s3_objects"] == 3
        assert len(results["missing_in_s3"]) == 1
        assert results["missing_in_s3"][0]["path"] == "files/expired.pdf"
        assert len(results["orphaned_in_s3"]) == 1
        assert "files/orphaned.pdf" in results["orphaned_in_s3"]
        assert len(results["size_mismatches"]) == 0
    
    def test_verify_s3_storage_consistency_size_mismatch(self, usage_tracker, sample_files):
        """Test S3 storage consistency with size mismatches."""
        mock_paginator = Mock()
        usage_tracker.s3_client.get_paginator.return_value = mock_paginator
        
        # Mock S3 objects with size mismatch
        s3_objects = [
            {'Key': 'files/permanent.pdf', 'Size': 999999},  # Size mismatch
            {'Key': 'files/temp.pdf', 'Size': 500000},
            {'Key': 'files/expired.pdf', 'Size': 300000}
        ]
        
        mock_paginator.paginate.return_value = [{'Contents': s3_objects}]
        
        results = usage_tracker.verify_s3_storage_consistency()
        
        assert len(results["size_mismatches"]) == 1
        mismatch = results["size_mismatches"][0]
        assert mismatch["path"] == "files/permanent.pdf"
        assert mismatch["db_size"] == 1000000
        assert mismatch["s3_size"] == 999999
    
    def test_verify_s3_storage_consistency_client_error(self, usage_tracker, sample_files):
        """Test S3 storage consistency check with client error."""
        usage_tracker.s3_client.get_paginator.side_effect = ClientError(
            error_response={'Error': {'Code': 'AccessDenied'}},
            operation_name='ListObjectsV2'
        )
        
        results = usage_tracker.verify_s3_storage_consistency()
        
        assert "s3_error" in results
        assert results["database_files"] == 3
        assert results["s3_objects"] == 0


@pytest.fixture
def db_session():
    """Mock database session for testing."""
    from unittest.mock import Mock
    return Mock()


if __name__ == "__main__":
    pytest.main([__file__])