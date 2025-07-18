"""
End-to-end integration tests for complete document processing workflows.
Tests Requirements: 5.1, 5.2, 5.3, 5.5
"""

import pytest
import asyncio
import tempfile
import zipfile
import json
from pathlib import Path
from httpx import AsyncClient
from unittest.mock import patch, MagicMock
from typing import Dict, Any

from src.main import app
from src.database.connection import get_db
from src.database.models import Task, TaskStatus
from src.config import get_settings


class TestEndToEndWorkflows:
    """Test complete document processing workflows from upload to results."""

    @pytest.fixture
    async def client(self):
        """Create test client with database override."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    @pytest.fixture
    def sample_pdf_file(self):
        """Create a sample PDF file for testing."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            # Create minimal PDF content
            f.write(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n")
            f.write(b"2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n")
            f.write(b"3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\n")
            f.write(b"xref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000079 00000 n \n0000000173 00000 n \n")
            f.write(b"trailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n253\n%%EOF")
            return Path(f.name)

    @pytest.fixture
    def sample_zip_archive(self, sample_pdf_file):
        """Create a ZIP archive with multiple test files."""
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
            with zipfile.ZipFile(f.name, 'w') as zf:
                # Add the PDF file
                zf.write(sample_pdf_file, "document1.pdf")
                
                # Add a text file
                zf.writestr("document2.txt", "This is a sample text document for testing.")
                
                # Add another PDF
                zf.writestr("subfolder/document3.pdf", sample_pdf_file.read_bytes())
                
            return Path(f.name)

    @pytest.mark.asyncio
    async def test_single_document_processing_workflow(self, client, sample_pdf_file):
        """Test complete workflow for processing a single document."""
        
        # Mock external dependencies
        with patch('src.storage.policy.upload_file_to_storage') as mock_upload, \
             patch('workers.src.tasks.parsing.parse_document_task.delay') as mock_parse_task:
            
            mock_upload.return_value = "https://storage.example.com/test-file.pdf"
            mock_task_result = MagicMock()
            mock_task_result.id = "task-123"
            mock_parse_task.return_value = mock_task_result
            
            # Step 1: Get pre-signed URL for upload
            response = await client.post(
                "/v1/upload/presigned-url",
                json={
                    "filename": "test-document.pdf",
                    "content_type": "application/pdf",
                    "user_id": "test-user"
                }
            )
            assert response.status_code == 200
            upload_data = response.json()
            assert "upload_url" in upload_data
            assert "file_id" in upload_data
            
            # Step 2: Create processing task
            task_response = await client.post(
                "/v1/tasks",
                json={
                    "file_urls": [upload_data["upload_url"]],
                    "user_id": "test-user",
                    "options": {
                        "enable_vectorization": True,
                        "storage_policy": "permanent"
                    }
                }
            )
            assert task_response.status_code == 201
            task_data = task_response.json()
            task_id = task_data["task_id"]
            
            # Step 3: Check task status
            status_response = await client.get(f"/v1/tasks/{task_id}/status")
            assert status_response.status_code == 200
            status_data = status_response.json()
            assert status_data["status"] in ["pending", "processing"]
            
            # Step 4: Simulate task completion and check results
            # Mock completed task in database
            with patch('src.database.repositories.TaskRepository.get_by_id') as mock_get_task:
                mock_task = Task(
                    id=task_id,
                    user_id="test-user",
                    status=TaskStatus.COMPLETED,
                    results={
                        "extracted_content": {
                            "title": "Test Document",
                            "content": "Sample document content",
                            "metadata": {"pages": 1}
                        },
                        "confidence_score": 0.95,
                        "processing_time": 2.5
                    }
                )
                mock_get_task.return_value = mock_task
                
                results_response = await client.get(f"/v1/tasks/{task_id}/results")
                assert results_response.status_code == 200
                results_data = results_response.json()
                assert "extracted_content" in results_data
                assert results_data["confidence_score"] == 0.95

    @pytest.mark.asyncio
    async def test_zip_archive_processing_workflow(self, client, sample_zip_archive):
        """Test complete workflow for processing ZIP archive with multiple documents."""
        
        with patch('src.storage.policy.upload_file_to_storage') as mock_upload, \
             patch('workers.src.tasks.archive.process_archive_task.delay') as mock_archive_task:
            
            mock_upload.return_value = "https://storage.example.com/test-archive.zip"
            mock_task_result = MagicMock()
            mock_task_result.id = "archive-task-123"
            mock_archive_task.return_value = mock_task_result
            
            # Step 1: Upload ZIP archive
            response = await client.post(
                "/v1/upload/presigned-url",
                json={
                    "filename": "test-archive.zip",
                    "content_type": "application/zip",
                    "user_id": "test-user"
                }
            )
            assert response.status_code == 200
            upload_data = response.json()
            
            # Step 2: Create archive processing task
            task_response = await client.post(
                "/v1/tasks",
                json={
                    "file_urls": [upload_data["upload_url"]],
                    "user_id": "test-user",
                    "options": {
                        "enable_vectorization": False,
                        "storage_policy": "temporary"
                    }
                }
            )
            assert task_response.status_code == 201
            task_data = task_response.json()
            parent_task_id = task_data["task_id"]
            
            # Step 3: Simulate archive extraction creating subtasks
            with patch('src.database.repositories.TaskRepository.get_by_parent_id') as mock_get_subtasks:
                mock_subtasks = [
                    Task(
                        id="subtask-1",
                        parent_task_id=parent_task_id,
                        user_id="test-user",
                        status=TaskStatus.COMPLETED,
                        results={"extracted_content": {"title": "Document 1"}}
                    ),
                    Task(
                        id="subtask-2", 
                        parent_task_id=parent_task_id,
                        user_id="test-user",
                        status=TaskStatus.COMPLETED,
                        results={"extracted_content": {"title": "Document 2"}}
                    )
                ]
                mock_get_subtasks.return_value = mock_subtasks
                
                # Check that subtasks were created
                subtasks_response = await client.get(f"/v1/tasks/{parent_task_id}/subtasks")
                assert subtasks_response.status_code == 200
                subtasks_data = subtasks_response.json()
                assert len(subtasks_data["subtasks"]) == 2

    @pytest.mark.asyncio
    async def test_cost_limit_workflow(self, client, sample_pdf_file):
        """Test workflow when cost limits are exceeded."""
        
        with patch('src.storage.policy.upload_file_to_storage') as mock_upload:
            mock_upload.return_value = "https://storage.example.com/large-file.pdf"
            
            # Create task with low cost limit
            task_response = await client.post(
                "/v1/tasks",
                json={
                    "file_urls": ["https://storage.example.com/large-file.pdf"],
                    "user_id": "test-user",
                    "options": {
                        "enable_vectorization": True,
                        "storage_policy": "permanent",
                        "max_cost_limit": 0.01  # Very low limit
                    }
                }
            )
            
            # Should reject due to cost limit
            assert task_response.status_code == 400
            error_data = task_response.json()
            assert "COST_LIMIT_EXCEEDED" in error_data["error_code"]

    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, client):
        """Test error handling in processing workflows."""
        
        # Test invalid file URL
        task_response = await client.post(
            "/v1/tasks",
            json={
                "file_urls": ["invalid-url"],
                "user_id": "test-user",
                "options": {"enable_vectorization": False}
            }
        )
        assert task_response.status_code == 400
        
        # Test missing required fields
        task_response = await client.post(
            "/v1/tasks",
            json={"file_urls": []}  # Missing user_id
        )
        assert task_response.status_code == 422

    @pytest.mark.asyncio
    async def test_vectorization_workflow(self, client, sample_pdf_file):
        """Test workflow with vectorization enabled."""
        
        with patch('src.storage.policy.upload_file_to_storage') as mock_upload, \
             patch('workers.src.tasks.parsing.parse_document_task.delay') as mock_parse_task, \
             patch('workers.src.tasks.vectorization.vectorize_content_task.delay') as mock_vector_task:
            
            mock_upload.return_value = "https://storage.example.com/test-file.pdf"
            mock_parse_result = MagicMock()
            mock_parse_result.id = "parse-task-123"
            mock_parse_task.return_value = mock_parse_result
            
            mock_vector_result = MagicMock()
            mock_vector_result.id = "vector-task-123"
            mock_vector_task.return_value = mock_vector_result
            
            # Create task with vectorization enabled
            task_response = await client.post(
                "/v1/tasks",
                json={
                    "file_urls": ["https://storage.example.com/test-file.pdf"],
                    "user_id": "test-user",
                    "options": {
                        "enable_vectorization": True,
                        "storage_policy": "permanent"
                    }
                }
            )
            assert task_response.status_code == 201
            
            # Verify vectorization task was queued
            mock_vector_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_temporary_storage_cleanup_workflow(self, client, sample_pdf_file):
        """Test workflow with temporary storage and cleanup."""
        
        with patch('src.storage.policy.upload_file_to_storage') as mock_upload, \
             patch('workers.src.tasks.cleanup.cleanup_temporary_files_task.delay') as mock_cleanup_task:
            
            mock_upload.return_value = "https://storage.example.com/temp-file.pdf"
            mock_cleanup_result = MagicMock()
            mock_cleanup_result.id = "cleanup-task-123"
            mock_cleanup_task.return_value = mock_cleanup_result
            
            # Create task with temporary storage
            task_response = await client.post(
                "/v1/tasks",
                json={
                    "file_urls": ["https://storage.example.com/temp-file.pdf"],
                    "user_id": "test-user",
                    "options": {
                        "enable_vectorization": False,
                        "storage_policy": "temporary"
                    }
                }
            )
            assert task_response.status_code == 201
            
            # Verify cleanup task scheduling
            # This would typically be scheduled after processing completion
            mock_cleanup_task.assert_called()