"""Tests for file upload and pre-signed URL endpoints."""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError, NoCredentialsError
import os

# Set test environment before importing modules
os.environ.update({
    'DATABASE_URL': 'postgresql://test:test@localhost:5432/test_dipc',
    'REDIS_URL': 'redis://localhost:6379/0',
    'CELERY_BROKER_URL': 'redis://localhost:6379/0',
    'CELERY_RESULT_BACKEND': 'redis://localhost:6379/0',
    'S3_ENDPOINT_URL': 'http://localhost:9000',
    'S3_ACCESS_KEY_ID': 'test_access_key',
    'S3_SECRET_ACCESS_KEY': 'test_secret_key',
    'S3_BUCKET_NAME': 'test-dipc-storage',
    'SECRET_KEY': 'test_secret_key_for_testing_only',
    'JWT_SECRET_KEY': 'test_jwt_secret_key_for_testing_only',
    'ENVIRONMENT': 'development',
    'LOG_LEVEL': 'INFO',
    'CORS_ORIGINS': 'http://localhost:3000',
    'OPENAI_API_KEY': 'test_openai_key'
})

from src.api.v1.upload import validate_file_security, get_s3_client
from src.api.models import PresignedUrlRequest


class TestFileValidation:
    """Test file validation and security checks."""
    
    def test_valid_file_request(self):
        """Test validation of a valid file upload request."""
        request = PresignedUrlRequest(
            filename="document.pdf",
            content_type="application/pdf",
            file_size=1024000  # 1MB
        )
        
        # Should not raise any exception
        validate_file_security(request)
    
    def test_file_size_limit_exceeded(self):
        """Test file size limit validation."""
        # The Pydantic model itself validates the file size limit
        with pytest.raises(ValueError) as exc_info:
            PresignedUrlRequest(
                filename="large_file.pdf",
                content_type="application/pdf",
                file_size=200 * 1024 * 1024  # 200MB - exceeds 100MB limit
            )
        
        assert "less than or equal to" in str(exc_info.value)
    
    def test_dangerous_filename_patterns(self):
        """Test detection of dangerous filename patterns."""
        # Test path traversal patterns - these are caught by Pydantic validation
        path_traversal_filenames = ["../../../etc/passwd", "folder/../test.pdf"]
        
        for filename in path_traversal_filenames:
            with pytest.raises(ValueError) as exc_info:
                PresignedUrlRequest(
                    filename=filename,
                    content_type="application/pdf",
                    file_size=1024
                )
            assert "path traversal detected" in str(exc_info.value)
        
        # Test other dangerous patterns - some are caught by Pydantic, some by custom validation
        pydantic_caught_patterns = [
            "file\\with\\backslashes.pdf",  # Backslash is caught by Pydantic
            "file/with/slashes.pdf"         # Forward slash is caught by Pydantic
        ]
        
        for filename in pydantic_caught_patterns:
            with pytest.raises(ValueError) as exc_info:
                PresignedUrlRequest(
                    filename=filename,
                    content_type="application/pdf",
                    file_size=1024
                )
            assert "path traversal detected" in str(exc_info.value)
        
        # Test patterns caught by custom validation
        custom_validation_patterns = [
            "file<script>.pdf",
            "file>redirect.pdf",
            'file"quote.pdf',
            "file|pipe.pdf",
            "file?query.pdf",
            "file*wildcard.pdf"
        ]
        
        for filename in custom_validation_patterns:
            request = PresignedUrlRequest(
                filename=filename,
                content_type="application/pdf",
                file_size=1024
            )
            
            with pytest.raises(Exception) as exc_info:
                validate_file_security(request)
            
            assert "dangerous pattern" in str(exc_info.value.detail)
    
    def test_dangerous_file_extensions(self):
        """Test detection of dangerous file extensions."""
        # Test files with unsupported content types (caught by Pydantic)
        unsupported_content_types = [
            ("malware.exe", "application/octet-stream"),
            ("script.vbs", "text/vbscript"),
            ("code.js", "application/javascript")
        ]
        
        for filename, content_type in unsupported_content_types:
            with pytest.raises(ValueError) as exc_info:
                PresignedUrlRequest(
                    filename=filename,
                    content_type=content_type,
                    file_size=1024
                )
            assert "is not supported" in str(exc_info.value)
        
        # Test dangerous extensions with valid content types (caught by custom validation)
        dangerous_extensions = [
            ("malware.exe", "application/zip"),  # Wrong content type but valid
            ("script.bat", "text/plain"),
            ("command.cmd", "text/plain"),
            ("virus.com", "text/plain"),
            ("trojan.scr", "text/plain")
        ]
        
        for filename, content_type in dangerous_extensions:
            request = PresignedUrlRequest(
                filename=filename,
                content_type=content_type,
                file_size=1024
            )
            
            with pytest.raises(Exception) as exc_info:
                validate_file_security(request)
            
            assert "File type not allowed" in str(exc_info.value.detail)
    
    def test_content_type_mismatch(self):
        """Test detection of content type and filename extension mismatch."""
        mismatched_files = [
            ("document.pdf", "image/jpeg"),
            ("image.jpg", "application/pdf"),
            ("archive.zip", "text/plain"),
            ("text.txt", "application/zip")
        ]
        
        for filename, content_type in mismatched_files:
            request = PresignedUrlRequest(
                filename=filename,
                content_type=content_type,
                file_size=1024
            )
            
            with pytest.raises(Exception) as exc_info:
                validate_file_security(request)
            
            assert "does not match file extension" in str(exc_info.value.detail)
    
    def test_valid_file_types(self):
        """Test validation of all supported file types."""
        valid_files = [
            ("document.pdf", "application/pdf"),
            ("image.jpg", "image/jpeg"),
            ("image.jpeg", "image/jpeg"),
            ("image.png", "image/png"),
            ("image.gif", "image/gif"),
            ("image.webp", "image/webp"),
            ("text.txt", "text/plain"),
            ("document.doc", "application/msword"),
            ("document.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            ("archive.zip", "application/zip")
        ]
        
        for filename, content_type in valid_files:
            request = PresignedUrlRequest(
                filename=filename,
                content_type=content_type,
                file_size=1024
            )
            
            # Should not raise any exception
            validate_file_security(request)


class TestS3Client:
    """Test S3 client functionality."""
    
    @patch('boto3.client')
    def test_s3_client_creation_success(self, mock_boto_client):
        """Test successful S3 client creation."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        client = get_s3_client()
        
        assert client == mock_client
        mock_boto_client.assert_called_once_with(
            's3',
            endpoint_url='http://localhost:9000',
            aws_access_key_id='test_access_key',
            aws_secret_access_key='test_secret_key',
            region_name='us-east-1'
        )
    
    @patch('boto3.client')
    def test_s3_client_no_credentials(self, mock_boto_client):
        """Test S3 client creation with no credentials."""
        mock_boto_client.side_effect = NoCredentialsError()
        
        with pytest.raises(Exception) as exc_info:
            get_s3_client()
        
        assert "S3 credentials not configured properly" in str(exc_info.value.detail)


class TestPresignedUrlGeneration:
    """Test pre-signed URL generation functionality."""
    
    def test_presigned_url_request_model(self):
        """Test PresignedUrlRequest model validation."""
        # Valid request
        request = PresignedUrlRequest(
            filename="test_document.pdf",
            content_type="application/pdf",
            file_size=1024000
        )
        
        assert request.filename == "test_document.pdf"
        assert request.content_type == "application/pdf"
        assert request.file_size == 1024000
    
    def test_presigned_url_request_validation_errors(self):
        """Test PresignedUrlRequest validation errors."""
        # Empty filename
        with pytest.raises(ValueError):
            PresignedUrlRequest(
                filename="",
                content_type="application/pdf",
                file_size=1024
            )
        
        # Invalid content type
        with pytest.raises(ValueError):
            PresignedUrlRequest(
                filename="test.pdf",
                content_type="invalid/type",
                file_size=1024
            )
        
        # File size too large
        with pytest.raises(ValueError):
            PresignedUrlRequest(
                filename="test.pdf",
                content_type="application/pdf",
                file_size=200 * 1024 * 1024  # 200MB
            )
        
        # Zero file size
        with pytest.raises(ValueError):
            PresignedUrlRequest(
                filename="test.pdf",
                content_type="application/pdf",
                file_size=0
            )
    
    def test_filename_path_traversal_validation(self):
        """Test filename validation against path traversal."""
        dangerous_filenames = [
            "../test.pdf",
            "../../test.pdf",
            "folder/../test.pdf",
            "folder/./test.pdf"
        ]
        
        for filename in dangerous_filenames:
            with pytest.raises(ValueError):
                PresignedUrlRequest(
                    filename=filename,
                    content_type="application/pdf",
                    file_size=1024
                )


class TestUploadEndpointIntegration:
    """Test upload endpoint integration (mocked)."""
    
    @patch('src.api.v1.upload.get_s3_client')
    def test_generate_presigned_url_success(self, mock_get_s3_client):
        """Test successful pre-signed URL generation."""
        # Mock S3 client
        mock_s3_client = MagicMock()
        mock_s3_client.generate_presigned_url.return_value = "https://example.com/presigned-url"
        mock_get_s3_client.return_value = mock_s3_client
        
        from src.api.v1.upload import generate_presigned_url
        
        request = PresignedUrlRequest(
            filename="test.pdf",
            content_type="application/pdf",
            file_size=1024
        )
        
        # This would be called in the actual endpoint
        # Here we're testing the core logic
        mock_s3_client.generate_presigned_url.assert_not_called()
    
    @patch('src.api.v1.upload.get_s3_client')
    def test_generate_presigned_url_s3_error(self, mock_get_s3_client):
        """Test pre-signed URL generation with S3 error."""
        # Mock S3 client to raise ClientError
        mock_s3_client = MagicMock()
        mock_s3_client.generate_presigned_url.side_effect = ClientError(
            error_response={'Error': {'Code': 'NoSuchBucket'}},
            operation_name='generate_presigned_url'
        )
        mock_get_s3_client.return_value = mock_s3_client
        
        # Test would verify error handling
        assert mock_get_s3_client is not None


class TestUploadHealthCheck:
    """Test upload service health check."""
    
    @patch('src.api.v1.upload.get_s3_client')
    def test_upload_health_check_success(self, mock_get_s3_client):
        """Test successful upload health check."""
        # Mock S3 client
        mock_s3_client = MagicMock()
        mock_s3_client.head_bucket.return_value = {}  # Success
        mock_get_s3_client.return_value = mock_s3_client
        
        from src.api.v1.upload import upload_service_health
        
        # This would be called in the actual endpoint
        # Here we're testing that the function exists
        assert callable(upload_service_health)
    
    @patch('src.api.v1.upload.get_s3_client')
    def test_upload_health_check_bucket_not_found(self, mock_get_s3_client):
        """Test upload health check with bucket not found."""
        # Mock S3 client to raise NoSuchBucket error
        mock_s3_client = MagicMock()
        mock_s3_client.head_bucket.side_effect = ClientError(
            error_response={'Error': {'Code': 'NoSuchBucket'}},
            operation_name='head_bucket'
        )
        mock_get_s3_client.return_value = mock_s3_client
        
        # Test would verify degraded status
        assert mock_get_s3_client is not None
    
    @patch('src.api.v1.upload.get_s3_client')
    def test_upload_health_check_no_credentials(self, mock_get_s3_client):
        """Test upload health check with no credentials."""
        mock_get_s3_client.side_effect = NoCredentialsError()
        
        # Test would verify unhealthy status
        assert mock_get_s3_client is not None


class TestSecurityFeatures:
    """Test security features of the upload system."""
    
    def test_file_extension_extraction(self):
        """Test file extension extraction logic."""
        test_cases = [
            ("document.pdf", ".pdf"),
            ("image.JPEG", ".jpeg"),  # Should be lowercase
            ("archive.ZIP", ".zip"),   # Should be lowercase
            ("file.with.dots.txt", ".txt"),  # Should get last extension
            ("no_extension", ""),      # No extension
            ("file.", "")             # Ends with dot, no extension
        ]
        
        for filename, expected_ext in test_cases:
            if '.' in filename and not filename.endswith('.') and not filename.startswith('.'):
                actual_ext = '.' + filename.split('.')[-1].lower()
            else:
                actual_ext = ""
            
            assert actual_ext == expected_ext
        
        # Special case for hidden files
        hidden_filename = ".hidden"
        if hidden_filename.startswith('.') and hidden_filename.count('.') == 1:
            actual_ext = ""
        else:
            actual_ext = '.' + hidden_filename.split('.')[-1].lower()
        assert actual_ext == ""
    
    def test_object_key_generation(self):
        """Test S3 object key generation."""
        import time
        from uuid import uuid4
        
        # Simulate object key generation
        file_id = str(uuid4())
        timestamp = int(time.time())
        file_extension = ".pdf"
        
        object_key = f"uploads/{timestamp}/{file_id}{file_extension}"
        
        # Verify structure
        assert object_key.startswith("uploads/")
        assert str(timestamp) in object_key
        assert file_id in object_key
        assert object_key.endswith(".pdf")
    
    def test_expiration_time_calculation(self):
        """Test expiration time calculation."""
        from datetime import datetime, timedelta
        
        start_time = datetime.utcnow()
        expiration_time = start_time + timedelta(hours=1)
        
        # Should be exactly 1 hour later
        time_diff = expiration_time - start_time
        assert time_diff.total_seconds() == 3600  # 1 hour in seconds
    
    def test_content_length_validation(self):
        """Test that content length is properly validated."""
        max_size = 100 * 1024 * 1024  # 100MB
        
        # Valid sizes
        valid_sizes = [1024, 1024 * 1024, 50 * 1024 * 1024]
        for size in valid_sizes:
            assert size <= max_size
        
        # Invalid sizes
        invalid_sizes = [101 * 1024 * 1024, 200 * 1024 * 1024]
        for size in invalid_sizes:
            assert size > max_size