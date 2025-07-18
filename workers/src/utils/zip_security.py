"""
Secure ZIP file extraction utilities with security checks and validation.
"""

import os
import zipfile
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import structlog
from dataclasses import dataclass

logger = structlog.get_logger(__name__)

# Security configuration constants
MAX_EXTRACTED_SIZE = 500 * 1024 * 1024  # 500MB max total extracted size
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB max individual file size
MAX_FILES_COUNT = 1000  # Maximum number of files in archive
MAX_COMPRESSION_RATIO = 100  # Maximum compression ratio to prevent zip bombs
MAX_PATH_LENGTH = 255  # Maximum path length
ALLOWED_FILE_EXTENSIONS = {
    '.pdf', '.txt', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp',
    '.csv', '.json', '.xml', '.html', '.md', '.rtf'
}

@dataclass
class ZipValidationResult:
    """Result of ZIP file validation."""
    is_valid: bool
    error_message: Optional[str] = None
    total_files: int = 0
    total_size: int = 0
    compressed_size: int = 0
    compression_ratio: float = 0.0
    suspicious_files: List[str] = None
    
    def __post_init__(self):
        if self.suspicious_files is None:
            self.suspicious_files = []

@dataclass
class ExtractedFile:
    """Information about an extracted file."""
    original_path: str
    safe_path: str
    file_size: int
    file_type: str
    is_valid: bool
    error_message: Optional[str] = None


class ZipSecurityError(Exception):
    """Custom exception for ZIP security violations."""
    pass


class SecureZipExtractor:
    """Secure ZIP file extractor with comprehensive security checks."""
    
    def __init__(self, max_extracted_size: int = MAX_EXTRACTED_SIZE,
                 max_file_size: int = MAX_FILE_SIZE,
                 max_files_count: int = MAX_FILES_COUNT,
                 max_compression_ratio: int = MAX_COMPRESSION_RATIO,
                 allowed_extensions: set = None):
        """
        Initialize the secure ZIP extractor.
        
        Args:
            max_extracted_size: Maximum total size of extracted files
            max_file_size: Maximum size of individual files
            max_files_count: Maximum number of files in archive
            max_compression_ratio: Maximum compression ratio to prevent zip bombs
            allowed_extensions: Set of allowed file extensions
        """
        self.max_extracted_size = max_extracted_size
        self.max_file_size = max_file_size
        self.max_files_count = max_files_count
        self.max_compression_ratio = max_compression_ratio
        self.allowed_extensions = allowed_extensions or ALLOWED_FILE_EXTENSIONS
        
    def validate_zip_file(self, zip_path: str) -> ZipValidationResult:
        """
        Validate ZIP file for security issues before extraction.
        
        Args:
            zip_path: Path to the ZIP file
            
        Returns:
            ZipValidationResult with validation details
        """
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_file:
                return self._perform_validation_checks(zip_file)
        except zipfile.BadZipFile:
            return ZipValidationResult(
                is_valid=False,
                error_message="Invalid or corrupted ZIP file"
            )
        except Exception as e:
            logger.error("Unexpected error during ZIP validation", error=str(e))
            return ZipValidationResult(
                is_valid=False,
                error_message=f"Validation error: {str(e)}"
            )
    
    def _perform_validation_checks(self, zip_file: zipfile.ZipFile) -> ZipValidationResult:
        """Perform comprehensive validation checks on ZIP file."""
        info_list = zip_file.infolist()
        
        # Check file count
        if len(info_list) > self.max_files_count:
            return ZipValidationResult(
                is_valid=False,
                error_message=f"Too many files in archive: {len(info_list)} > {self.max_files_count}"
            )
        
        total_size = 0
        compressed_size = 0
        suspicious_files = []
        
        for info in info_list:
            # Check for path traversal attacks
            if self._is_path_traversal(info.filename):
                suspicious_files.append(f"Path traversal: {info.filename}")
                continue
            
            # Check file size
            if info.file_size > self.max_file_size:
                suspicious_files.append(f"File too large: {info.filename} ({info.file_size} bytes)")
                continue
            
            # Check file extension
            if not self._is_allowed_file_type(info.filename):
                suspicious_files.append(f"Disallowed file type: {info.filename}")
                continue
            
            # Check for zip bombs (high compression ratio)
            if info.compress_size > 0:
                ratio = info.file_size / info.compress_size
                if ratio > self.max_compression_ratio:
                    suspicious_files.append(f"Suspicious compression ratio: {info.filename} ({ratio:.1f}:1)")
                    continue
            
            total_size += info.file_size
            compressed_size += info.compress_size
        
        # Check total extracted size
        if total_size > self.max_extracted_size:
            return ZipValidationResult(
                is_valid=False,
                error_message=f"Total extracted size too large: {total_size} > {self.max_extracted_size}",
                total_files=len(info_list),
                total_size=total_size,
                compressed_size=compressed_size,
                suspicious_files=suspicious_files
            )
        
        # If there are suspicious files but some valid files remain
        valid_files = len(info_list) - len(suspicious_files)
        if valid_files == 0:
            return ZipValidationResult(
                is_valid=False,
                error_message="No valid files found in archive",
                total_files=len(info_list),
                suspicious_files=suspicious_files
            )
        
        compression_ratio = compressed_size / total_size if total_size > 0 else 0
        
        return ZipValidationResult(
            is_valid=True,
            total_files=len(info_list),
            total_size=total_size,
            compressed_size=compressed_size,
            compression_ratio=compression_ratio,
            suspicious_files=suspicious_files
        )
    
    def _is_path_traversal(self, filename: str) -> bool:
        """Check if filename contains path traversal attempts."""
        # Normalize the path and check for traversal patterns
        normalized = os.path.normpath(filename)
        
        # Check for absolute paths
        if os.path.isabs(normalized):
            return True
        
        # Check for parent directory references in both Unix and Windows style
        if '..' in normalized.split(os.sep) or '..' in normalized.split('/') or '..' in normalized.split('\\'):
            return True
        
        # Check for Windows-style paths with backslashes
        if '\\' in filename and '..' in filename:
            return True
        
        # Check for overly long paths
        if len(normalized) > MAX_PATH_LENGTH:
            return True
        
        return False
    
    def _is_allowed_file_type(self, filename: str) -> bool:
        """Check if file type is allowed based on extension."""
        file_ext = Path(filename).suffix.lower()
        return file_ext in self.allowed_extensions
    
    def extract_zip_safely(self, zip_path: str, extract_to: Optional[str] = None) -> Tuple[str, List[ExtractedFile]]:
        """
        Safely extract ZIP file to a temporary directory.
        
        Args:
            zip_path: Path to the ZIP file
            extract_to: Optional directory to extract to (creates temp dir if None)
            
        Returns:
            Tuple of (extraction_directory, list_of_extracted_files)
            
        Raises:
            ZipSecurityError: If security validation fails
        """
        # First validate the ZIP file
        validation_result = self.validate_zip_file(zip_path)
        if not validation_result.is_valid:
            raise ZipSecurityError(f"ZIP validation failed: {validation_result.error_message}")
        
        # Create extraction directory
        if extract_to is None:
            extract_dir = tempfile.mkdtemp(prefix="secure_zip_extract_")
        else:
            extract_dir = extract_to
            os.makedirs(extract_dir, exist_ok=True)
        
        logger.info(
            "Starting secure ZIP extraction",
            zip_path=zip_path,
            extract_dir=extract_dir,
            total_files=validation_result.total_files,
            total_size=validation_result.total_size
        )
        
        extracted_files = []
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_file:
                for info in zip_file.infolist():
                    # Skip suspicious files identified during validation
                    if any(info.filename in suspicious for suspicious in validation_result.suspicious_files):
                        logger.warning("Skipping suspicious file", filename=info.filename)
                        continue
                    
                    # Create safe filename
                    safe_filename = self._create_safe_filename(info.filename)
                    safe_path = os.path.join(extract_dir, safe_filename)
                    
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(safe_path), exist_ok=True)
                    
                    # Extract file
                    try:
                        with zip_file.open(info) as source, open(safe_path, 'wb') as target:
                            # Extract with size monitoring
                            extracted_size = 0
                            while True:
                                chunk = source.read(8192)
                                if not chunk:
                                    break
                                
                                extracted_size += len(chunk)
                                if extracted_size > self.max_file_size:
                                    raise ZipSecurityError(f"File {info.filename} exceeded size limit during extraction")
                                
                                target.write(chunk)
                        
                        # Verify extracted file
                        actual_size = os.path.getsize(safe_path)
                        if actual_size != info.file_size:
                            logger.warning(
                                "File size mismatch after extraction",
                                filename=info.filename,
                                expected=info.file_size,
                                actual=actual_size
                            )
                        
                        extracted_files.append(ExtractedFile(
                            original_path=info.filename,
                            safe_path=safe_path,
                            file_size=actual_size,
                            file_type=Path(info.filename).suffix.lower(),
                            is_valid=True
                        ))
                        
                        logger.debug("Successfully extracted file", filename=info.filename, size=actual_size)
                        
                    except Exception as e:
                        logger.error("Failed to extract file", filename=info.filename, error=str(e))
                        extracted_files.append(ExtractedFile(
                            original_path=info.filename,
                            safe_path="",
                            file_size=0,
                            file_type=Path(info.filename).suffix.lower(),
                            is_valid=False,
                            error_message=str(e)
                        ))
            
            logger.info(
                "ZIP extraction completed",
                extract_dir=extract_dir,
                total_extracted=len([f for f in extracted_files if f.is_valid]),
                total_failed=len([f for f in extracted_files if not f.is_valid])
            )
            
            return extract_dir, extracted_files
            
        except Exception as e:
            # Cleanup on failure
            if extract_to is None:  # Only cleanup temp dirs we created
                self._cleanup_directory(extract_dir)
            raise ZipSecurityError(f"Extraction failed: {str(e)}")
    
    def _create_safe_filename(self, original_filename: str) -> str:
        """Create a safe filename from the original filename."""
        # Remove any path components and use only the filename
        safe_name = os.path.basename(original_filename)
        
        # Replace any remaining problematic characters
        safe_name = "".join(c for c in safe_name if c.isalnum() or c in "._-")
        
        # Ensure it's not empty
        if not safe_name:
            safe_name = "extracted_file"
        
        # Limit length
        if len(safe_name) > 100:
            name, ext = os.path.splitext(safe_name)
            safe_name = name[:95] + ext
        
        return safe_name
    
    def _cleanup_directory(self, directory: str) -> None:
        """Safely cleanup extraction directory."""
        try:
            import shutil
            shutil.rmtree(directory)
            logger.debug("Cleaned up extraction directory", directory=directory)
        except Exception as e:
            logger.error("Failed to cleanup extraction directory", directory=directory, error=str(e))


def create_secure_extractor(**kwargs) -> SecureZipExtractor:
    """Factory function to create a SecureZipExtractor with custom settings."""
    return SecureZipExtractor(**kwargs)