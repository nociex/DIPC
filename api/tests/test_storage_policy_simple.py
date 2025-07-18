"""Simple tests for storage policy management without full environment setup."""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock

# Mock the settings to avoid environment validation
with patch('src.config.Settings') as mock_settings_class:
    mock_settings = Mock()
    mock_settings.temp_file_ttl_hours = 24
    mock_settings.s3_bucket_name = "test-bucket"
    mock_settings.s3_endpoint_url = "http://localhost:9000"
    mock_settings.s3_access_key_id = "test_key"
    mock_settings.s3_secret_access_key = "test_secret"
    mock_settings.default_storage_policy = "temporary"
    mock_settings_class.return_value = mock_settings
    
    with patch('src.config.settings', mock_settings):
        from src.storage.policy import (
            StoragePolicyManager, 
            StorageUsageTracker,
            StoragePolicyConfig,
            StorageUsageStats
        )


class TestStoragePolicyConfig:
    """Test storage policy configuration."""
    
    def test_storage_policy_config_initialization(self):
        """Test storage policy configuration initialization."""
        from src.database.models import StoragePolicyEnum
        
        # Test temporary policy with default TTL
        config = StoragePolicyConfig(policy=StoragePolicyEnum.TEMPORARY)
        assert config.policy == StoragePolicyEnum.TEMPORARY
        assert config.ttl_hours == 24  # From mock settings
        
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
    
    def test_validate_file_against_policy_size_limit(self, policy_manager):
        """Test file validation against size limits."""
        from src.database.models import StoragePolicyEnum
        
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
        from src.database.models import StoragePolicyEnum
        
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
        from src.database.models import StoragePolicyEnum
        
        # Default temporary policy
        config = policy_manager.get_default_policy_config()
        assert config.policy == StoragePolicyEnum.TEMPORARY
        assert config.ttl_hours == 24
        
        # Override to permanent
        config = policy_manager.get_default_policy_config("permanent")
        assert config.policy == StoragePolicyEnum.PERMANENT
        assert config.ttl_hours is None
    
    def test_apply_storage_policy_temporary(self, policy_manager):
        """Test applying temporary storage policy."""
        from src.database.models import StoragePolicyEnum
        
        # Mock file metadata
        mock_file = Mock()
        mock_file.storage_policy = None
        mock_file.expires_at = None
        
        config = StoragePolicyConfig(
            policy=StoragePolicyEnum.TEMPORARY,
            ttl_hours=24
        )
        
        before_time = datetime.now(timezone.utc)
        updated_file = policy_manager.apply_storage_policy(mock_file, config)
        after_time = datetime.now(timezone.utc)
        
        assert updated_file.storage_policy == StoragePolicyEnum.TEMPORARY
        assert updated_file.expires_at is not None
        assert before_time + timedelta(hours=24) <= updated_file.expires_at <= after_time + timedelta(hours=24)
    
    def test_apply_storage_policy_permanent(self, policy_manager):
        """Test applying permanent storage policy."""
        from src.database.models import StoragePolicyEnum
        
        # Mock file metadata
        mock_file = Mock()
        mock_file.storage_policy = None
        mock_file.expires_at = None
        
        config = StoragePolicyConfig(policy=StoragePolicyEnum.PERMANENT)
        
        updated_file = policy_manager.apply_storage_policy(mock_file, config)
        
        assert updated_file.storage_policy == StoragePolicyEnum.PERMANENT
        assert updated_file.expires_at is None


class TestStorageUsageStats:
    """Test storage usage statistics."""
    
    def test_storage_usage_stats_creation(self):
        """Test creating storage usage stats."""
        stats = StorageUsageStats(
            total_files=100,
            total_size_bytes=1024000,
            permanent_files=60,
            permanent_size_bytes=614400,
            temporary_files=40,
            temporary_size_bytes=409600,
            expired_files=10,
            expired_size_bytes=102400
        )
        
        assert stats.total_files == 100
        assert stats.total_size_bytes == 1024000
        assert stats.permanent_files == 60
        assert stats.permanent_size_bytes == 614400
        assert stats.temporary_files == 40
        assert stats.temporary_size_bytes == 409600
        assert stats.expired_files == 10
        assert stats.expired_size_bytes == 102400


if __name__ == "__main__":
    pytest.main([__file__])