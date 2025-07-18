"""
Simplified tests for archive processing functionality.
"""

import os
import tempfile
import zipfile
import pytest
import shutil
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
import json

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.zip_security import SecureZipExtractor, ZipSecurityError


class TestArchiveProcessingCore:
    """Test core archive processing functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def create_test_zip(self, temp_dir: str, files: dict, zip_name: str = "test.zip") -> str:
        """Create a test ZIP file with specified files."""
        zip_path = os.path.join(temp_dir, zip_name)
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for filename, content in files.items():
                if isinstance(content, str):
                    zf.writestr(filename, content.encode('utf-8'))
                else:
                    zf.writestr(filename, content)
        return zip_path
    
    def test_secure_zip_extraction_basic(self, temp_dir):
        """Test basic secure ZIP extraction."""
        # Create test ZIP with valid files
        files = {
            "document.pdf": b"PDF content",
            "text.txt": "Text content",
            "data.json": json.dumps({"test": "data"})
        }
        
        zip_path = self.create_test_zip(temp_dir, files)
        
        # Extract using secure extractor
        extractor = SecureZipExtractor()
        extraction_dir, extracted_files = extractor.extract_zip_safely(zip_path)
        
        try:
            # Verify extraction
            assert len(extracted_files) == 3
            valid_files = [f for f in extracted_files if f.is_valid]
            assert len(valid_files) == 3
            
            # Verify files exist and have correct content
            for extracted_file in valid_files:
                assert os.path.exists(extracted_file.safe_path)
                assert extracted_file.file_size > 0
                
                if extracted_file.original_path == "text.txt":
                    with open(extracted_file.safe_path, 'r') as f:
                        content = f.read()
                        assert content == "Text content"
                
                elif extracted_file.original_path == "data.json":
                    with open(extracted_file.safe_path, 'r') as f:
                        data = json.load(f)
                        assert data["test"] == "data"
        
        finally:
            shutil.rmtree(extraction_dir, ignore_errors=True)
    
    def test_malicious_zip_handling(self, temp_dir):
        """Test handling of malicious ZIP files."""
        # Create ZIP with path traversal attempts
        files = {
            "../../../etc/passwd": "malicious content",
            "normal_file.txt": "normal content",
            "../../windows/system32/config": "another malicious file"
        }
        
        zip_path = self.create_test_zip(temp_dir, files)
        
        extractor = SecureZipExtractor()
        
        # Validate ZIP - should identify suspicious files
        validation_result = extractor.validate_zip_file(zip_path)
        assert len(validation_result.suspicious_files) >= 2
        assert any("Path traversal" in suspicious for suspicious in validation_result.suspicious_files)
        
        # Extract ZIP - should only extract safe files
        extraction_dir, extracted_files = extractor.extract_zip_safely(zip_path)
        
        try:
            valid_files = [f for f in extracted_files if f.is_valid]
            assert len(valid_files) == 1
            assert valid_files[0].original_path == "normal_file.txt"
            
            # Verify safe extraction
            with open(valid_files[0].safe_path, 'r') as f:
                content = f.read()
                assert content == "normal content"
        
        finally:
            shutil.rmtree(extraction_dir, ignore_errors=True)
    
    def test_zip_size_limits(self, temp_dir):
        """Test ZIP file size limit enforcement."""
        # Create extractor with small limits for testing
        extractor = SecureZipExtractor(
            max_extracted_size=1000,  # 1KB limit
            max_file_size=500         # 500B per file
        )
        
        # Create ZIP that exceeds limits
        large_content = "x" * 600  # Exceeds per-file limit
        files = {
            "large_file.txt": large_content,
            "normal_file.txt": "normal content"
        }
        
        zip_path = self.create_test_zip(temp_dir, files)
        
        # Validate - should identify large file as suspicious
        validation_result = extractor.validate_zip_file(zip_path)
        assert any("File too large" in suspicious for suspicious in validation_result.suspicious_files)
    
    def test_disallowed_file_types(self, temp_dir):
        """Test rejection of disallowed file types."""
        files = {
            "script.exe": b"executable content",
            "malware.bat": b"batch script",
            "document.pdf": b"PDF content",  # Should be allowed
            "virus.com": b"DOS executable"
        }
        
        zip_path = self.create_test_zip(temp_dir, files)
        
        extractor = SecureZipExtractor()
        validation_result = extractor.validate_zip_file(zip_path)
        
        # Should identify disallowed file types
        suspicious_files = validation_result.suspicious_files
        assert any("Disallowed file type" in suspicious for suspicious in suspicious_files)
        assert any("script.exe" in suspicious for suspicious in suspicious_files)
        assert any("malware.bat" in suspicious for suspicious in suspicious_files)
    
    def test_empty_zip_handling(self, temp_dir):
        """Test handling of empty ZIP files."""
        # Create empty ZIP
        empty_zip_path = os.path.join(temp_dir, "empty.zip")
        with zipfile.ZipFile(empty_zip_path, 'w') as zf:
            pass  # Create empty ZIP
        
        extractor = SecureZipExtractor()
        validation_result = extractor.validate_zip_file(empty_zip_path)
        
        assert not validation_result.is_valid
        assert "No valid files found" in validation_result.error_message
    
    def test_corrupted_zip_handling(self, temp_dir):
        """Test handling of corrupted ZIP files."""
        # Create corrupted ZIP file
        corrupted_zip_path = os.path.join(temp_dir, "corrupted.zip")
        with open(corrupted_zip_path, 'wb') as f:
            f.write(b"This is not a valid ZIP file")
        
        extractor = SecureZipExtractor()
        validation_result = extractor.validate_zip_file(corrupted_zip_path)
        
        assert not validation_result.is_valid
        assert "Invalid or corrupted ZIP file" in validation_result.error_message
    
    def test_nested_directories(self, temp_dir):
        """Test extraction of files in nested directories."""
        files = {
            "root_file.txt": "root content",
            "folder1/file1.txt": "folder1 content",
            "folder1/subfolder/file2.txt": "subfolder content",
            "folder2/document.pdf": b"PDF in folder2"
        }
        
        zip_path = self.create_test_zip(temp_dir, files)
        
        extractor = SecureZipExtractor()
        extraction_dir, extracted_files = extractor.extract_zip_safely(zip_path)
        
        try:
            # Verify all files were extracted
            valid_files = [f for f in extracted_files if f.is_valid]
            assert len(valid_files) == 4
            
            # Verify nested file content
            nested_file = next(f for f in valid_files if f.original_path == "folder1/subfolder/file2.txt")
            with open(nested_file.safe_path, 'r') as f:
                content = f.read()
                assert content == "subfolder content"
        
        finally:
            shutil.rmtree(extraction_dir, ignore_errors=True)
    
    def test_file_count_limits(self, temp_dir):
        """Test file count limit enforcement."""
        # Create extractor with low file count limit
        extractor = SecureZipExtractor(max_files_count=3)
        
        # Create ZIP with too many files
        files = {f"file_{i}.txt": f"content {i}" for i in range(5)}
        zip_path = self.create_test_zip(temp_dir, files)
        
        validation_result = extractor.validate_zip_file(zip_path)
        
        assert not validation_result.is_valid
        assert "Too many files" in validation_result.error_message
    
    def test_safe_filename_creation(self):
        """Test creation of safe filenames."""
        extractor = SecureZipExtractor()
        
        test_cases = [
            ("normal_file.txt", "normal_file.txt"),
            ("../../../etc/passwd", "passwd"),
            ("file with spaces.pdf", "file with spaces.pdf"),
            ("file@#$%^&*()name.doc", "filename.doc"),
            ("", "extracted_file"),
            ("a" * 200 + ".txt", "a" * 95 + ".txt")  # Long filename
        ]
        
        for original, expected_pattern in test_cases:
            safe_name = extractor._create_safe_filename(original)
            
            # Basic safety checks
            assert not os.path.isabs(safe_name)
            assert ".." not in safe_name
            assert len(safe_name) <= 100
            assert safe_name  # Not empty
            
            if expected_pattern == "extracted_file":
                assert safe_name == expected_pattern
            elif len(expected_pattern) > 100:
                assert len(safe_name) <= 100
    
    def test_path_traversal_detection(self):
        """Test path traversal detection."""
        extractor = SecureZipExtractor()
        
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
            assert not extractor._is_path_traversal(path), f"Safe path incorrectly flagged: {path}"
        
        for path in dangerous_paths:
            assert extractor._is_path_traversal(path), f"Dangerous path not detected: {path}"


class TestArchiveProcessingIntegration:
    """Integration tests for complete archive processing workflow."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def create_realistic_archive(self, temp_dir: str) -> str:
        """Create a realistic test archive with various file types."""
        files = {
            "README.txt": "This is a test archive with various document types.",
            "documents/report.pdf": b"PDF report content here",
            "documents/spreadsheet.xlsx": b"Excel spreadsheet data",
            "images/photo1.jpg": b"JPEG image data",
            "images/diagram.png": b"PNG diagram data",
            "data/config.json": json.dumps({
                "version": "1.0",
                "settings": {"debug": True, "timeout": 30}
            }),
            "data/export.csv": "name,age,city\nJohn,25,NYC\nJane,30,LA",
            "scripts/README.md": "# Scripts Directory\nThis contains utility scripts."
        }
        
        zip_path = os.path.join(temp_dir, "realistic_archive.zip")
        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            for filename, content in files.items():
                if isinstance(content, str):
                    zf.writestr(filename, content.encode('utf-8'))
                else:
                    zf.writestr(filename, content)
        
        return zip_path
    
    def test_realistic_archive_processing(self, temp_dir):
        """Test processing of a realistic archive."""
        archive_path = self.create_realistic_archive(temp_dir)
        
        extractor = SecureZipExtractor()
        
        # Validate archive
        validation_result = extractor.validate_zip_file(archive_path)
        assert validation_result.is_valid
        assert validation_result.total_files == 8
        assert len(validation_result.suspicious_files) == 0
        
        # Extract archive
        extraction_dir, extracted_files = extractor.extract_zip_safely(archive_path)
        
        try:
            # Verify all files extracted successfully
            valid_files = [f for f in extracted_files if f.is_valid]
            assert len(valid_files) == 8
            
            # Verify specific file contents
            readme_file = next(f for f in valid_files if f.original_path == "README.txt")
            with open(readme_file.safe_path, 'r') as f:
                content = f.read()
                assert "test archive" in content
            
            config_file = next(f for f in valid_files if f.original_path == "data/config.json")
            with open(config_file.safe_path, 'r') as f:
                config = json.load(f)
                assert config["version"] == "1.0"
                assert config["settings"]["debug"] is True
            
            csv_file = next(f for f in valid_files if f.original_path == "data/export.csv")
            with open(csv_file.safe_path, 'r') as f:
                csv_content = f.read()
                assert "John,25,NYC" in csv_content
            
            # Verify file types are correctly identified
            file_types = {f.file_type for f in valid_files}
            expected_types = {'.txt', '.pdf', '.xlsx', '.jpg', '.png', '.json', '.csv', '.md'}
            assert file_types == expected_types
            
        finally:
            shutil.rmtree(extraction_dir, ignore_errors=True)
    
    def test_mixed_safe_and_unsafe_archive(self, temp_dir):
        """Test archive with mix of safe and unsafe files."""
        files = {
            # Safe files
            "document.pdf": b"Safe PDF content",
            "data.json": json.dumps({"safe": "data"}),
            "image.jpg": b"Safe image data",
            
            # Unsafe files
            "../../../etc/passwd": "Path traversal attempt",
            "malware.exe": b"Executable content",
            "script.bat": b"Batch script",
            "virus.com": b"DOS executable"
        }
        
        zip_path = self.create_test_zip(temp_dir, files)
        
        extractor = SecureZipExtractor()
        
        # Should identify unsafe files but still process safe ones
        validation_result = extractor.validate_zip_file(zip_path)
        assert validation_result.is_valid  # Has some valid files
        assert len(validation_result.suspicious_files) >= 4  # All unsafe files flagged
        
        # Extract - should only get safe files
        extraction_dir, extracted_files = extractor.extract_zip_safely(zip_path)
        
        try:
            valid_files = [f for f in extracted_files if f.is_valid]
            assert len(valid_files) == 3  # Only safe files
            
            # Verify only safe files were extracted
            extracted_names = {f.original_path for f in valid_files}
            expected_safe = {"document.pdf", "data.json", "image.jpg"}
            assert extracted_names == expected_safe
            
        finally:
            shutil.rmtree(extraction_dir, ignore_errors=True)
    
    def create_test_zip(self, temp_dir: str, files: dict) -> str:
        """Helper to create test ZIP files."""
        zip_path = os.path.join(temp_dir, "test.zip")
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for filename, content in files.items():
                if isinstance(content, str):
                    zf.writestr(filename, content.encode('utf-8'))
                else:
                    zf.writestr(filename, content)
        return zip_path


if __name__ == "__main__":
    pytest.main([__file__, "-v"])