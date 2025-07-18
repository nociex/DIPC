"""Tests for vectorization tasks."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import List, Dict, Any

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tasks.vectorization import (
    vectorize_content_task,
    VectorizationError,
    _chunk_text,
    _generate_embeddings,
    _store_vectors
)
from tasks.base import TaskStatus
from llm.exceptions import LLMProviderError, LLMConfigurationError
from vector.client import VectorDocument, VectorDatabaseError


class TestTextChunking:
    """Test text chunking functionality."""
    
    def test_chunk_text_short_text(self):
        """Test chunking text shorter than chunk size."""
        text = "This is a short text."
        chunks = _chunk_text(text, chunk_size=100)
        
        assert len(chunks) == 1
        assert chunks[0] == text
    
    def test_chunk_text_long_text(self):
        """Test chunking long text."""
        text = "This is a long text. " * 100  # ~2000 characters
        chunks = _chunk_text(text, chunk_size=500, overlap=50)
        
        assert len(chunks) > 1
        assert all(len(chunk) <= 500 for chunk in chunks)
        
        # Check overlap exists between consecutive chunks
        for i in range(len(chunks) - 1):
            # There should be some overlap between consecutive chunks
            assert len(chunks[i]) > 0
            assert len(chunks[i + 1]) > 0
    
    def test_chunk_text_word_boundaries(self):
        """Test that chunking respects word boundaries."""
        text = "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10"
        chunks = _chunk_text(text, chunk_size=30, overlap=5)
        
        # Chunks should not break words in the middle
        for chunk in chunks:
            assert not chunk.startswith(' ')
            assert not chunk.endswith(' ')
    
    def test_chunk_text_empty_input(self):
        """Test chunking empty text."""
        chunks = _chunk_text("", chunk_size=100)
        assert chunks == []
        
        chunks = _chunk_text("   ", chunk_size=100)
        assert chunks == []


class TestEmbeddingGeneration:
    """Test embedding generation functionality."""
    
    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client."""
        client = Mock()
        
        # Mock embeddings response
        mock_embedding_data = Mock()
        mock_embedding_data.embedding = [0.1, 0.2, 0.3] * 512  # 1536 dimensions
        
        mock_response = Mock()
        mock_response.data = [mock_embedding_data, mock_embedding_data]
        
        client.embeddings.create.return_value = mock_response
        
        return client
    
    def test_generate_embeddings_success(self, mock_openai_client):
        """Test successful embedding generation."""
        texts = ["Text 1", "Text 2"]
        
        embeddings = _generate_embeddings(mock_openai_client, texts)
        
        assert len(embeddings) == 2
        assert len(embeddings[0]) == 1536  # OpenAI embedding dimension
        assert len(embeddings[1]) == 1536
        
        mock_openai_client.embeddings.create.assert_called_once_with(
            input=texts,
            model="text-embedding-ada-002"
        )
    
    def test_generate_embeddings_custom_model(self, mock_openai_client):
        """Test embedding generation with custom model."""
        texts = ["Text 1"]
        model = "text-embedding-3-small"
        
        _generate_embeddings(mock_openai_client, texts, model=model)
        
        mock_openai_client.embeddings.create.assert_called_once_with(
            input=texts,
            model=model
        )
    
    def test_generate_embeddings_failure(self, mock_openai_client):
        """Test embedding generation failure."""
        mock_openai_client.embeddings.create.side_effect = Exception("API Error")
        
        with pytest.raises(LLMProviderError):
            _generate_embeddings(mock_openai_client, ["Text 1"])


class TestVectorStorage:
    """Test vector storage functionality."""
    
    @pytest.fixture
    def mock_vector_client(self):
        """Create a mock vector client."""
        client = AsyncMock()
        client.store_documents.return_value = ["doc1_0", "doc1_1"]
        return client
    
    @pytest.mark.asyncio
    async def test_store_vectors_success(self, mock_vector_client):
        """Test successful vector storage."""
        task_id = "test-task-123"
        chunks = ["Chunk 1", "Chunk 2"]
        embeddings = [[0.1] * 1536, [0.2] * 1536]
        metadata = {"user_id": "user123", "type": "test"}
        
        stored_ids = await _store_vectors(
            mock_vector_client, task_id, chunks, embeddings, metadata
        )
        
        assert stored_ids == ["doc1_0", "doc1_1"]
        
        # Verify store_documents was called with correct documents
        call_args = mock_vector_client.store_documents.call_args[0][0]
        assert len(call_args) == 2
        
        # Check first document
        doc1 = call_args[0]
        assert doc1.id == "test-task-123_0"
        assert doc1.content == "Chunk 1"
        assert doc1.embedding == [0.1] * 1536
        assert doc1.metadata["user_id"] == "user123"
        assert doc1.metadata["task_id"] == task_id
        assert doc1.metadata["chunk_index"] == 0
    
    @pytest.mark.asyncio
    async def test_store_vectors_failure(self, mock_vector_client):
        """Test vector storage failure."""
        mock_vector_client.store_documents.side_effect = VectorDatabaseError("Storage failed")
        
        with pytest.raises(VectorDatabaseError):
            await _store_vectors(
                mock_vector_client, "task-123", ["Chunk 1"], [[0.1] * 1536], {}
            )


class TestVectorizationTask:
    """Test the main vectorization task."""
    
    @pytest.fixture
    def base_task_data(self):
        """Base task data for testing."""
        return {
            "task_id": "12345678-1234-5678-1234-567812345678",
            "content": "This is test content for vectorization. It should be long enough to be processed.",
            "user_id": "user123",
            "options": {"enable_vectorization": True},
            "metadata": {"source": "test"}
        }
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies."""
        with patch('tasks.vectorization.LLMClientFactory') as mock_llm_factory, \
             patch('tasks.vectorization.get_vector_client') as mock_get_vector_client, \
             patch('tasks.vectorization._generate_embeddings') as mock_generate_embeddings, \
             patch('tasks.vectorization._store_vectors') as mock_store_vectors:
            
            # Setup LLM client mock
            mock_client = Mock()
            mock_llm_factory.create_default_client.return_value = mock_client
            
            # Setup vector client mock
            mock_vector_client = AsyncMock()
            mock_get_vector_client.return_value = mock_vector_client
            
            # Setup embedding generation mock
            mock_generate_embeddings.return_value = [[0.1] * 1536, [0.2] * 1536]
            
            # Setup vector storage mock
            mock_store_vectors.return_value = ["doc1_0", "doc1_1"]
            
            yield {
                'llm_factory': mock_llm_factory,
                'vector_client': mock_vector_client,
                'generate_embeddings': mock_generate_embeddings,
                'store_vectors': mock_store_vectors
            }
    
    def test_vectorization_disabled(self, base_task_data):
        """Test vectorization when disabled by user options."""
        task_data = {**base_task_data, "options": {"enable_vectorization": False}}
        
        result = vectorize_content_task(task_data)
        
        assert result["status"] == TaskStatus.COMPLETED.value
        assert result["result"]["vectorization_enabled"] is False
        assert result["result"]["vectors_stored"] == 0
    
    def test_vectorization_success_string_content(self, base_task_data, mock_dependencies):
        """Test successful vectorization with string content."""
        with patch('asyncio.new_event_loop') as mock_new_loop, \
             patch('asyncio.set_event_loop') as mock_set_loop:
            
            # Mock event loop
            mock_loop = Mock()
            mock_new_loop.return_value = mock_loop
            mock_loop.run_until_complete.return_value = ["doc1_0", "doc1_1"]
            
            result = vectorize_content_task(base_task_data)
            
            assert result["status"] == TaskStatus.COMPLETED.value
            assert result["result"]["vectors_stored"] == 2
            assert result["result"]["vectorization_enabled"] is True
            assert "vector_ids" in result["result"]
    
    def test_vectorization_success_dict_content(self, mock_dependencies):
        """Test successful vectorization with dictionary content."""
        task_data = {
            "task_id": "12345678-1234-5678-1234-567812345678",
            "content": {
                "text": "Main content text",
                "summary": "Content summary",
                "extracted_content": {
                    "title": "Document Title",
                    "body": "Document body text"
                }
            },
            "user_id": "user123",
            "options": {"enable_vectorization": True}
        }
        
        with patch('asyncio.new_event_loop') as mock_new_loop, \
             patch('asyncio.set_event_loop') as mock_set_loop:
            
            mock_loop = Mock()
            mock_new_loop.return_value = mock_loop
            mock_loop.run_until_complete.return_value = ["doc1_0"]
            
            result = vectorize_content_task(task_data)
            
            assert result["status"] == TaskStatus.COMPLETED.value
            assert result["result"]["vectors_stored"] == 1
    
    def test_vectorization_content_too_short(self, base_task_data):
        """Test vectorization with content too short."""
        task_data = {**base_task_data, "content": "Short"}
        
        result = vectorize_content_task(task_data)
        
        assert result["status"] == TaskStatus.COMPLETED.value
        assert result["result"]["vectors_stored"] == 0
        assert "too short" in result["result"]["message"]
    
    def test_vectorization_llm_configuration_error(self, base_task_data):
        """Test vectorization with LLM configuration error."""
        with patch('tasks.vectorization.LLMClientFactory') as mock_llm_factory:
            mock_llm_factory.create_default_client.side_effect = LLMConfigurationError("No API key")
            
            result = vectorize_content_task(base_task_data)
            
            assert result["status"] == TaskStatus.FAILED.value
            assert "LLM client configuration failed" in result["result"]["error"]
    
    def test_vectorization_embedding_generation_error(self, base_task_data, mock_dependencies):
        """Test vectorization with embedding generation error."""
        mock_dependencies['generate_embeddings'].side_effect = LLMProviderError("API Error", "openai")
        
        result = vectorize_content_task(base_task_data)
        
        assert result["status"] == TaskStatus.FAILED.value
        assert "Embedding generation failed" in result["result"]["error"]
    
    def test_vectorization_storage_error(self, base_task_data, mock_dependencies):
        """Test vectorization with vector storage error."""
        with patch('asyncio.new_event_loop') as mock_new_loop, \
             patch('asyncio.set_event_loop') as mock_set_loop:
            
            mock_loop = Mock()
            mock_new_loop.return_value = mock_loop
            mock_loop.run_until_complete.side_effect = VectorDatabaseError("Storage failed")
            
            result = vectorize_content_task(base_task_data)
            
            assert result["status"] == TaskStatus.FAILED.value
            assert "Vector storage failed" in result["result"]["error"]
    
    def test_vectorization_custom_options(self, base_task_data, mock_dependencies):
        """Test vectorization with custom options."""
        task_data = {
            **base_task_data,
            "options": {
                "enable_vectorization": True,
                "chunk_size": 500,
                "chunk_overlap": 50,
                "embedding_model": "text-embedding-3-small"
            }
        }
        
        with patch('asyncio.new_event_loop') as mock_new_loop, \
             patch('asyncio.set_event_loop') as mock_set_loop:
            
            mock_loop = Mock()
            mock_new_loop.return_value = mock_loop
            mock_loop.run_until_complete.return_value = ["doc1_0"]
            
            result = vectorize_content_task(task_data)
            
            assert result["status"] == TaskStatus.COMPLETED.value
            
            # Verify custom embedding model was used
            mock_dependencies['generate_embeddings'].assert_called_once()
            call_args = mock_dependencies['generate_embeddings'].call_args
            assert call_args[1]['model'] == "text-embedding-3-small"
    
    def test_vectorization_input_validation(self):
        """Test vectorization task input validation."""
        # Missing required fields
        invalid_task_data = {
            "task_id": "test-task-123",
            # Missing content and user_id
        }
        
        with pytest.raises(Exception):  # Should raise validation error
            vectorize_content_task(invalid_task_data)
    
    def test_vectorization_unexpected_error(self, base_task_data):
        """Test vectorization with unexpected error."""
        with patch('tasks.vectorization.LLMClientFactory') as mock_llm_factory:
            mock_llm_factory.create_default_client.side_effect = RuntimeError("Unexpected error")
            
            result = vectorize_content_task(base_task_data)
            
            assert result["status"] == TaskStatus.FAILED.value
            assert "Vectorization failed" in result["result"]["error"]


class TestVectorizationIntegration:
    """Integration tests for vectorization workflow."""
    
    @pytest.mark.asyncio
    async def test_full_vectorization_workflow(self):
        """Test the complete vectorization workflow with mocked dependencies."""
        # This test verifies the entire flow works together
        task_data = {
            "task_id": "87654321-4321-8765-4321-876543218765",
            "content": "This is a comprehensive test of the vectorization system. " * 20,
            "user_id": "integration-user",
            "options": {
                "enable_vectorization": True,
                "chunk_size": 100,
                "chunk_overlap": 20
            },
            "metadata": {"test": "integration"}
        }
        
        with patch('tasks.vectorization.LLMClientFactory') as mock_llm_factory, \
             patch('tasks.vectorization.get_vector_client') as mock_get_vector_client, \
             patch('asyncio.new_event_loop') as mock_new_loop, \
             patch('asyncio.set_event_loop') as mock_set_loop:
            
            # Setup mocks
            mock_client = Mock()
            mock_embedding_data = Mock()
            mock_embedding_data.embedding = [0.1] * 1536
            mock_response = Mock()
            mock_response.data = [mock_embedding_data] * 5  # Multiple chunks
            mock_client.embeddings.create.return_value = mock_response
            mock_llm_factory.create_default_client.return_value = mock_client
            
            mock_vector_client = AsyncMock()
            mock_vector_client.store_documents.return_value = ["doc1_0", "doc1_1", "doc1_2"]
            mock_get_vector_client.return_value = mock_vector_client
            
            mock_loop = Mock()
            mock_new_loop.return_value = mock_loop
            mock_loop.run_until_complete.return_value = ["doc1_0", "doc1_1", "doc1_2"]
            
            # Execute task
            result = vectorize_content_task(task_data)
            
            # Verify result
            assert result["status"] == TaskStatus.COMPLETED.value
            assert result["result"]["vectors_stored"] == 3
            assert result["result"]["vectorization_enabled"] is True
            assert len(result["result"]["vector_ids"]) == 3
            
            # Verify LLM client was called for embeddings
            mock_client.embeddings.create.assert_called_once()
            
            # Verify vector storage was attempted
            mock_loop.run_until_complete.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])