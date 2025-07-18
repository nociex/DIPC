"""
Integration tests for archive processing workflow.
"""

import os
import tempfile
import zipfile
import pytest
import shutil
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4, UUID
import json

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tasks.archive import (
    process_archive_task, 
    cleanup_extraction_directory,
    _download_archive_file,
    _create_subtasks_for_files,
    _queue_subtasks_for_processing
)
from tasks.base import TaskStatus
from utils.zip_security import SecureZipExtractor, ZipSecurityError


class TestArchiveProcessingWorkflow:
    """Test suite for archive processing workflow."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        with patch('tasks.archive.get_db_session') as mock_session:
            mock_db = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_db
            mock_session.return_value.__exit__.return_value = None
            yield mock_db
    
    @pytest.fixture
    def mock_task_repo(self):
        """Mock task repository."""
        with patch('tasks.archive.TaskRepository') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            yield mock_repo
    
    @pytest.fixture
    def mock_file_repo(self):
        """Mock file metadata repository."""
        with patch('tasks.archive.FileMetadataRepository') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            yield mock_repo
    
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
    
    def test_download_archive_file_success(self, temp_dir):
        """Test successful archive file download."""
        # Create a test ZIP file to serve
        test_files = {"test.txt": "test content"}
        test_zip_path = self.create_test_zip(temp_dir, test_files)
        
        # Mock HTTP response
        with patch('tasks.archive.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.headers = {'content-length': '1000'}
            mock_response.raise_for_status.return_value = None
            
            # Read the actual ZIP file content
            with open(test_zip_path, 'rb') as f:
                zip_content = f.read()
            
            mock_response.iter_content.return_value = [zip_content]
            mock_get.return_value = mock_response
            
            # Test download
            task_id = str(uuid4())
            downloaded_path = _download_archive_file("http://example.com/test.zip", task_id)
            
            try:
                # Verify file was downloaded
                assert os.path.exists(downloaded_path)
                assert downloaded_path.endswith('.zip')
                
                # Verify content
                with zipfile.ZipFile(downloaded_path, 'r') as zf:
                    assert 'test.txt' in zf.namelist()
                    assert zf.read('test.txt').decode() == 'test content'
            finally:
                if os.path.exists(downloaded_path):
                    os.unlink(downloaded_path)
    
    def test_download_archive_file_too_large(self):
        """Test rejection of files that are too large."""
        with patch('tasks.archive.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.headers = {'content-length': str(600 * 1024 * 1024)}  # 600MB
            mock_get.return_value = mock_response
            
            task_id = str(uuid4())
            
            with pytest.raises(ValueError, match="Archive file too large"):
                _download_archive_file("http://example.com/large.zip", task_id)
    
    def test_create_subtasks_for_files(self, mock_db_session, mock_task_repo, mock_file_repo):
        """Test creation of subtasks for extracted files."""
        # Mock extracted files
        from utils.zip_security import ExtractedFile
        
        extracted_files = [
            ExtractedFile(
                original_path="doc1.pdf",
                safe_path="/tmp/doc1.pdf",
                file_size=1000,
                file_type=".pdf",
                is_valid=True
            ),
            ExtractedFile(
                original_path="doc2.txt",
                safe_path="/tmp/doc2.txt",
                file_size=500,
                file_type=".txt",
                is_valid=True
            )
        ]
        
        # Mock task creation
        mock_task1 = Mock()
        mock_task1.id = uuid4()
        mock_task2 = Mock()
        mock_task2.id = uuid4()
        mock_task_repo.create.side_effect = [mock_task1, mock_task2]
        
        # Mock queue function
        with patch('tasks.archive._queue_subtasks_for_processing') as mock_queue:
            parent_task_id = str(uuid4())
            user_id = "test_user"
            options = {"storage_policy": "temporary"}
            temp_dir = "/tmp/extraction"
            
            subtask_ids = _create_subtasks_for_files(
                parent_task_id, user_id, extracted_files, options, temp_dir
            )
            
            # Verify subtasks were created
            assert len(subtask_ids) == 2
            assert mock_task_repo.create.call_count == 2
            assert mock_file_repo.create.call_count == 2
            
            # Verify queue was called
            mock_queue.assert_called_once_with([mock_task1.id, mock_task2.id])
    
    def test_queue_subtasks_for_processing(self):
        """Test queuing of subtasks for document processing."""
        subtask_ids = [uuid4(), uuid4()]
        
        with patch('tasks.parsing.parse_document_task') as mock_parse_task:
            mock_parse_task.delay = Mock()
            
            _queue_subtasks_for_processing(subtask_ids)
            
            # Verify tasks were queued
            assert mock_parse_task.delay.call_count == 2
            
            # Check call arguments
            calls = mock_parse_task.delay.call_args_list
            for i, call in enumerate(calls):
                args = call[0][0]  # First argument of the call
                assert args['task_id'] == str(subtask_ids[i])
                assert args['source'] == 'archive_extraction'
    
    @patch('tasks.archive._download_archive_file')
    @patch('tasks.archive.SecureZipExtractor')
    def test_process_archive_task_success(
        self, 
        mock_extractor_class, 
        mock_download,
        mock_db_session,
        mock_task_repo,
        temp_dir
    ):
        """Test successful archive processing task."""
        # Setup mocks
        task_id = str(uuid4())
        file_url = "http://example.com/test.zip"
        user_id = "test_user"
        
        task_data = {
            'task_id': task_id,
            'file_url': file_url,
            'user_id': user_id,
            'options': {'storage_policy': 'temporary'}
        }
        
        # Mock download
        archive_path = os.path.join(temp_dir, "downloaded.zip")
        mock_download.return_value = archive_path
        
        # Mock extractor
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor
        
        from utils.zip_security import ExtractedFile
        extracted_files = [
            ExtractedFile(
                original_path="doc1.pdf",
                safe_path="/tmp/doc1.pdf",
                file_size=1000,
                file_type=".pdf",
                is_valid=True
            )
        ]
        
        extraction_dir = os.path.join(temp_dir, "extracted")
        mock_extractor.extract_zip_safely.return_value = (extraction_dir, extracted_files)
        
        # Mock subtask creation
        with patch('tasks.archive._create_subtasks_for_files') as mock_create_subtasks:
            subtask_ids = [uuid4()]
            mock_create_subtasks.return_value = subtask_ids
            
            # Execute task
            result = process_archive_task(None, task_data)
            
            # Verify result
            assert result['status'] == TaskStatus.COMPLETED.value
            assert result['result']['archive_processed'] is True
            assert result['result']['valid_files_extracted'] == 1
            assert result['result']['subtasks_created'] == 1
            
            # Verify calls
            mock_download.assert_called_once_with(file_url, task_id)
            mock_extractor.extract_zip_safely.assert_called_once_with(archive_path)
            mock_create_subtasks.assert_called_once()
            
            # Verify task status updates
            assert mock_task_repo.update_status.call_count == 2  # Processing + Completed
    
    @patch('tasks.archive._download_archive_file')
    @patch('tasks.archive.SecureZipExtractor')
    def test_process_archive_task_security_error(
        self,
        mock_extractor_class,
        mock_download,
        mock_db_session,
        mock_task_repo,
        temp_dir
    ):
        """Test archive processing with security error."""
        task_id = str(uuid4())
        task_data = {
            'task_id': task_id,
            'file_url': "http://example.com/malicious.zip",
            'user_id': "test_user"
        }
        
        # Mock download
        archive_path = os.path.join(temp_dir, "malicious.zip")
        mock_download.return_value = archive_path
        
        # Mock extractor to raise security error
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.extract_zip_safely.side_effect = ZipSecurityError("Zip bomb detected")
        
        # Execute task
        result = process_archive_task(None, task_data)
        
        # Verify result
        assert result['status'] == TaskStatus.FAILED.value
        assert "Archive security validation failed" in result['error']
        assert "Zip bomb detected" in result['error']
        
        # Verify task status was updated to failed
        mock_task_repo.update_status.assert_called()
        failed_call = [call for call in mock_task_repo.update_status.call_args_list 
                      if 'FAILED' in str(call)]
        assert len(failed_call) > 0
    
    @patch('tasks.archive._download_archive_file')
    def test_process_archive_task_download_error(
        self,
        mock_download,
        mock_db_session,
        mock_task_repo
    ):
        """Test archive processing with download error."""
        task_id = str(uuid4())
        task_data = {
            'task_id': task_id,
            'file_url': "http://example.com/nonexistent.zip",
            'user_id': "test_user"
        }
        
        # Mock download to raise error
        mock_download.side_effect = Exception("Download failed")
        
        # Execute task
        result = process_archive_task(None, task_data)
        
        # Verify result
        assert result['status'] == TaskStatus.FAILED.value
        assert "Archive processing failed" in result['error']
        assert "Download failed" in result['error']
    
    def test_cleanup_extraction_directory_with_incomplete_subtasks(
        self,
        mock_db_session,
        mock_task_repo
    ):
        """Test cleanup deferral when subtasks are still processing."""
        parent_task_id = str(uuid4())
        extraction_dir = "/tmp/extraction"
        
        # Mock parent task with incomplete subtasks
        mock_parent_task = Mock()
        mock_subtask1 = Mock()
        mock_subtask1.is_completed.return_value = False
        mock_subtask2 = Mock()
        mock_subtask2.is_completed.return_value = True
        
        mock_parent_task.subtasks = [mock_subtask1, mock_subtask2]
        mock_task_repo.get_by_id.return_value = mock_parent_task
        
        with patch('tasks.archive.cleanup_extraction_directory.apply_async') as mock_apply_async:
            # Execute cleanup
            result = cleanup_extraction_directory(None, extraction_dir, parent_task_id)
            
            # Verify cleanup was deferred
            assert result['status'] == TaskStatus.PENDING.value
            assert "Cleanup deferred" in result['result']['message']
            
            # Verify rescheduling
            mock_apply_async.assert_called_once()
            args, kwargs = mock_apply_async.call_args
            assert args == ([extraction_dir, parent_task_id],)
            assert kwargs['countdown'] == 300
    
    def test_cleanup_extraction_directory_success(
        self,
        mock_db_session,
        mock_task_repo,
        temp_dir
    ):
        """Test successful cleanup of extraction directory."""
        parent_task_id = str(uuid4())
        
        # Create a test extraction directory
        extraction_dir = os.path.join(temp_dir, "extraction")
        os.makedirs(extraction_dir)
        test_file = os.path.join(extraction_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        # Mock parent task with all subtasks completed
        mock_parent_task = Mock()
        mock_subtask1 = Mock()
        mock_subtask1.is_completed.return_value = True
        mock_subtask2 = Mock()
        mock_subtask2.is_completed.return_value = True
        
        mock_parent_task.subtasks = [mock_subtask1, mock_subtask2]
        mock_task_repo.get_by_id.return_value = mock_parent_task
        
        # Execute cleanup
        result = cleanup_extraction_directory(None, extraction_dir, parent_task_id)
        
        # Verify cleanup was successful
        assert result['status'] == TaskStatus.COMPLETED.value
        assert result['result']['cleanup_completed'] is True
        assert not os.path.exists(extraction_dir)
    
    def test_cleanup_extraction_directory_not_found(
        self,
        mock_db_session,
        mock_task_repo
    ):
        """Test cleanup when extraction directory doesn't exist."""
        parent_task_id = str(uuid4())
        extraction_dir = "/nonexistent/directory"
        
        # Mock parent task with all subtasks completed
        mock_parent_task = Mock()
        mock_parent_task.subtasks = []
        mock_task_repo.get_by_id.return_value = mock_parent_task
        
        # Execute cleanup
        result = cleanup_extraction_directory(None, extraction_dir, parent_task_id)
        
        # Verify cleanup completed despite directory not existing
        assert result['status'] == TaskStatus.COMPLETED.value
        assert result['result']['cleanup_completed'] is True


class TestArchiveProcessingIntegration:
    """Integration tests for the complete archive processing workflow."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def create_test_archive(self, temp_dir: str) -> str:
        """Create a test archive with multiple files."""
        files = {
            "document1.pdf": b"PDF content for document 1",
            "document2.txt": "Text content for document 2",
            "image.jpg": b"JPEG image data",
            "data.json": json.dumps({"key": "value", "number": 42}),
            "folder/nested_doc.docx": b"Word document content"
        }
        
        zip_path = os.path.join(temp_dir, "test_archive.zip")
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for filename, content in files.items():
                if isinstance(content, str):
                    zf.writestr(filename, content.encode('utf-8'))
                else:
                    zf.writestr(filename, content)
        
        return zip_path
    
    def test_end_to_end_archive_processing(self, temp_dir):
        """Test complete end-to-end archive processing workflow."""
        # Create test archive
        archive_path = self.create_test_archive(temp_dir)
        
        # Test secure extraction
        extractor = SecureZipExtractor()
        
        # Validate archive
        validation_result = extractor.validate_zip_file(archive_path)
        assert validation_result.is_valid
        assert validation_result.total_files == 5
        
        # Extract archive
        extraction_dir, extracted_files = extractor.extract_zip_safely(archive_path)
        
        try:
            # Verify extraction
            valid_files = [f for f in extracted_files if f.is_valid]
            assert len(valid_files) == 5
            
            # Verify files exist and have correct content
            for extracted_file in valid_files:
                assert os.path.exists(extracted_file.safe_path)
                assert extracted_file.file_size > 0
                
                # Check specific files
                if extracted_file.original_path == "document2.txt":
                    with open(extracted_file.safe_path, 'r') as f:
                        content = f.read()
                        assert content == "Text content for document 2"
                
                elif extracted_file.original_path == "data.json":
                    with open(extracted_file.safe_path, 'r') as f:
                        data = json.load(f)
                        assert data["key"] == "value"
                        assert data["number"] == 42
            
            # Verify security measures
            for extracted_file in extracted_files:
                # Check that safe paths don't contain traversal attempts
                assert ".." not in extracted_file.safe_path
                assert not os.path.isabs(extracted_file.safe_path.replace(extraction_dir, ""))
        
        finally:
            # Cleanup
            shutil.rmtree(extraction_dir, ignore_errors=True)
    
    def test_malicious_archive_rejection(self, temp_dir):
        """Test rejection of malicious archives."""
        # Create archive with path traversal attempt
        malicious_zip_path = os.path.join(temp_dir, "malicious.zip")
        with zipfile.ZipFile(malicious_zip_path, 'w') as zf:
            zf.writestr("../../../etc/passwd", "malicious content")
            zf.writestr("normal_file.txt", "normal content")
        
        extractor = SecureZipExtractor()
        
        # Validate archive - should identify suspicious files
        validation_result = extractor.validate_zip_file(malicious_zip_path)
        assert len(validation_result.suspicious_files) > 0
        assert any("Path traversal" in suspicious for suspicious in validation_result.suspicious_files)
        
        # Extract archive - should still work but skip malicious files
        extraction_dir, extracted_files = extractor.extract_zip_safely(malicious_zip_path)
        
        try:
            # Should have extracted only the normal file
            valid_files = [f for f in extracted_files if f.is_valid]
            assert len(valid_files) == 1
            assert valid_files[0].original_path == "normal_file.txt"
            
            # Verify no path traversal occurred
            for extracted_file in valid_files:
                assert extraction_dir in extracted_file.safe_path
                assert not extracted_file.safe_path.endswith("passwd")
        
        finally:
            shutil.rmtree(extraction_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])