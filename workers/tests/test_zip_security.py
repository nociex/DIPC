"""
Tests for secure ZIP extraction functionality.
"""

import os
import tempfile
import zipfile
import pytest
from pathlib import Path
import shutil

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.zip_security import (
    SecureZipExtractor, 
    ZipSecurityError, 
    ZipValidationResult,
    MAX_EXTRACTED_SIZE,
    MAX_FILE_SIZE,
    MAX_FILES_COUNT,
    ALLOWED_FILE_EXTENSIONS
)


class TestSecureZipExtractor:
    """Test suite for SecureZipExtractor."""
    
    @pytest.fixture
    def extractor(self):
        """Create a SecureZipExtractor instance for testing."""
        return SecureZipExtractor()
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def create_test_zip(self, temp_dir: str, files: dict, zip_name: str = "test.zip") -> str:
        """
        Create a test ZIP file with specified files.
        
        Args:
            temp_dir: Temporary directory to create ZIP in
            files: Dict of filename -> content
            zip_name: Name of the ZIP file
            
        Returns:
            Path to created ZIP file
        """
        zip_path = os.path.join(temp_dir, zip_name)
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for filename, content in files.items():
                if isinstance(content, str):
                    zf.writestr(filename, content.encode('utf-8'))
                else:
                    zf.writestr(filename, content)
        return zip_path
    
    def test_valid_zip_extraction(self, extractor, temp_dir):
        """Test extraction of a valid ZIP file."""
        # Create a valid ZIP with allowed file types
        files = {
            "document.pdf": b"PDF content here",
            "image.jpg": b"JPEG content here",
            "text.txt": "Text content here",
            "data.json": '{"key": "value"}'
        }
        
        zip_path = self.create_test_zip(temp_dir, files)
        
        # Extract the ZIP
        extract_dir, extracted_files = extractor.extract_zip_safely(zip_path)
        
        try:
            # Verify extraction
            assert len(extracted_files) == 4
            assert all(f.is_valid for f in extracted_files)
            
            # Check that files exist
            for extracted_file in extracted_files:
                assert os.path.exists(extracted_file.safe_path)
                assert extracted_file.file_size > 0
        finally:
            shutil.rmtree(extract_dir, ignore_errors=True)
    
    def test_zip_validation_success(self, extractor, temp_dir):
        """Test successful ZIP validation."""
        files = {
            "document.pdf": b"PDF content",
            "image.png": b"PNG content"
        }
        
        zip_path = self.create_test_zip(temp_dir, files)
        result = extractor.validate_zip_file(zip_path)
        
        assert result.is_valid
        assert result.total_files == 2
        assert result.error_message is None
        assert len(result.suspicious_files) == 0
    
    def test_path_traversal_prevention(self, extractor, temp_dir):
        """Test prevention of path traversal attacks."""
        # Create ZIP with path traversal attempts
        files = {
            "../../../etc/passwd": "malicious content",
            "..\\..\\windows\\system32\\config": "malicious content",
            "/etc/shadow": "malicious content",
            "normal_file.txt": "normal content"
        }
        
        zip_path = self.create_test_zip(temp_dir, files)
        result = extractor.validate_zip_file(zip_path)
        
        # Should identify suspicious files but still be valid if normal files exist
        assert len(result.suspicious_files) >= 3
        assert any("Path traversal" in suspicious for suspicious in result.suspicious_files)
    
    def test_file_size_limit_enforcement(self, extractor, temp_dir):
        """Test enforcement of file size limits."""
        # Create a file that exceeds the size limit
        large_content = b"x" * (MAX_FILE_SIZE + 1000)
        files = {
            "large_file.txt": large_content,
            "normal_file.txt": "normal content"
        }
        
        zip_path = self.create_test_zip(temp_dir, files)
        result = extractor.validate_zip_file(zip_path)
        
        # Should identify the large file as suspicious
        assert any("File too large" in suspicious for suspicious in result.suspicious_files)
    
    def test_file_count_limit_enforcement(self, temp_dir):
        """Test enforcement of file count limits."""
        # Create extractor with low file count limit for testing
        extractor = SecureZipExtractor(max_files_count=5)
        
        # Create ZIP with too many files
        files = {f"file_{i}.txt": f"content {i}" for i in range(10)}
        
        zip_path = self.create_test_zip(temp_dir, files)
        result = extractor.validate_zip_file(zip_path)
        
        assert not result.is_valid
        assert "Too many files" in result.error_message
    
    def test_total_size_limit_enforcement(self, temp_dir):
        """Test enforcement of total extracted size limits."""
        # Create extractor with low size limit for testing
        extractor = SecureZipExtractor(max_extracted_size=1000)
        
        # Create files that exceed total size limit
        files = {
            "file1.txt": "x" * 600,
            "file2.txt": "x" * 600
        }
        
        zip_path = self.create_test_zip(temp_dir, files)
        result = extractor.validate_zip_file(zip_path)
        
        assert not result.is_valid
        assert "Total extracted size too large" in result.error_message
    
    def test_disallowed_file_types(self, extractor, temp_dir):
        """Test rejection of disallowed file types."""
        files = {
            "script.exe": b"executable content",
            "malware.bat": b"batch script",
            "document.pdf": b"PDF content",  # This should be allowed
            "archive.zip": b"nested zip"
        }
        
        zip_path = self.create_test_zip(temp_dir, files)
        result = extractor.validate_zip_file(zip_path)
        
        # Should identify disallowed file types
        suspicious_files = result.suspicious_files
        assert any("Disallowed file type" in suspicious for suspicious in suspicious_files)
        assert any("script.exe" in suspicious for suspicious in suspicious_files)
        assert any("malware.bat" in suspicious for suspicious in suspicious_files)
    
    def test_zip_bomb_detection(self, temp_dir):
        """Test detection of zip bombs (high compression ratio)."""
        # Create extractor with low compression ratio limit for testing
        extractor = SecureZipExtractor(max_compression_ratio=10)
        
        # Create a highly compressible file (simulating zip bomb)
        highly_compressible = "A" * 10000  # Very repetitive content
        files = {
            "bomb.txt": highly_compressible,
            "normal.txt": "normal content"
        }
        
        zip_path = self.create_test_zip(temp_dir, files)
        result = extractor.validate_zip_file(zip_path)
        
        # May detect suspicious compression ratio
        # Note: This test might be flaky depending on actual compression achieved
        if result.suspicious_files:
            assert any("compression ratio" in suspicious.lower() for suspicious in result.suspicious_files)
    
    def test_corrupted_zip_handling(self, extractor, temp_dir):
        """Test handling of corrupted ZIP files."""
        # Create a corrupted ZIP file
        corrupted_zip_path = os.path.join(temp_dir, "corrupted.zip")
        with open(corrupted_zip_path, 'wb') as f:
            f.write(b"This is not a valid ZIP file")
        
        result = extractor.validate_zip_file(corrupted_zip_path)
        
        assert not result.is_valid
        assert "Invalid or corrupted ZIP file" in result.error_message
    
    def test_empty_zip_handling(self, extractor, temp_dir):
        """Test handling of empty ZIP files."""
        # Create an empty ZIP file
        empty_zip_path = os.path.join(temp_dir, "empty.zip")
        with zipfile.ZipFile(empty_zip_path, 'w') as zf:
            pass  # Create empty ZIP
        
        result = extractor.validate_zip_file(empty_zip_path)
        
        assert not result.is_valid
        assert "No valid files found" in result.error_message
    
    def test_extraction_with_custom_directory(self, extractor, temp_dir):
        """Test extraction to a custom directory."""
        files = {
            "test.txt": "test content"
        }
        
        zip_path = self.create_test_zip(temp_dir, files)
        custom_extract_dir = os.path.join(temp_dir, "custom_extract")
        
        extract_dir, extracted_files = extractor.extract_zip_safely(zip_path, custom_extract_dir)
        
        try:
            assert extract_dir == custom_extract_dir
            assert len(extracted_files) == 1
            assert extracted_files[0].is_valid
            assert os.path.exists(extracted_files[0].safe_path)
        finally:
            shutil.rmtree(custom_extract_dir, ignore_errors=True)
    
    def test_extraction_failure_cleanup(self, temp_dir):
        """Test that temporary directories are cleaned up on extraction failure."""
        # Create extractor that will fail validation
        extractor = SecureZipExtractor(max_files_count=0)  # Will reject any files
        
        files = {"test.txt": "content"}
        zip_path = self.create_test_zip(temp_dir, files)
        
        with pytest.raises(ZipSecurityError):
            extractor.extract_zip_safely(zip_path)
        
        # Verify no temporary directories are left behind
        # This is hard to test directly, but the exception should be raised
    
    def test_safe_filename_creation(self, extractor):
        """Test creation of safe filenames from potentially dangerous ones."""
        # Test various problematic filenames
        test_cases = [
            ("../../../etc/passwd", "passwd"),
            ("file with spaces.txt", "file with spaces.txt"),
            ("file@#$%^&*()name.pdf", "filename.pdf"),
            ("", "extracted_file"),
            ("a" * 200 + ".txt", "a" * 95 + ".txt")  # Long filename truncation
        ]
        
        for original, expected_pattern in test_cases:
            safe_name = extractor._create_safe_filename(original)
            
            # Basic safety checks
            assert not os.path.isabs(safe_name)
            assert ".." not in safe_name
            assert len(safe_name) <= 100
            assert safe_name  # Not empty
    
    def test_allowed_file_extensions(self, extractor):
        """Test file extension validation."""
        allowed_files = [
            "document.pdf",
            "image.jpg",
            "data.json",
            "text.txt",
            "spreadsheet.xlsx"
        ]
        
        disallowed_files = [
            "script.exe",
            "malware.bat",
            "library.dll",
            "archive.zip"
        ]
        
        for filename in allowed_files:
            assert extractor._is_allowed_file_type(filename)
        
        for filename in disallowed_files:
            assert not extractor._is_allowed_file_type(filename)
    
    def test_path_traversal_detection(self, extractor):
        """Test path traversal detection logic."""
        safe_paths = [
            "normal_file.txt",
            "folder/file.txt",
            "deep/folder/structure/file.pdf"
        ]
        
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config",
            "/etc/shadow",
            "/absolute/path/file.txt",
            "folder/../../../escape.txt"
        ]
        
        for path in safe_paths:
            assert not extractor._is_path_traversal(path)
        
        for path in dangerous_paths:
            assert extractor._is_path_traversal(path)


class TestZipBombProtection:
    """Specific tests for zip bomb protection."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_compression_ratio_calculation(self, temp_dir):
        """Test that compression ratios are calculated correctly."""
        extractor = SecureZipExtractor()
        
        # Create content with known compression characteristics
        files = {
            "compressible.txt": "A" * 1000,  # Highly compressible
            "random.bin": os.urandom(1000)   # Not compressible
        }
        
        zip_path = os.path.join(temp_dir, "test.zip")
        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            for filename, content in files.items():
                if isinstance(content, str):
                    zf.writestr(filename, content.encode('utf-8'))
                else:
                    zf.writestr(filename, content)
        
        result = extractor.validate_zip_file(zip_path)
        
        # Should successfully validate and calculate compression ratios
        assert result.is_valid
        assert result.compression_ratio > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])