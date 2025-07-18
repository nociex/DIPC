"""Tests for vector database client."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from vector.client import (
    VectorDatabaseClient,
    VectorDocument,
    VectorSearchResult,
    VectorDatabaseError,
    VectorDatabaseConnectionError,
    get_vector_client
)


class TestVectorDocument:
    """Test VectorDocument dataclass."""
    
    def test_vector_document_creation(self):
        """Test creating a VectorDocument."""
        doc = VectorDocument(
            id="test-id",
            content="Test content",
            metadata={"type": "test"},
            embedding=[0.1, 0.2, 0.3]
        )
        
        assert doc.id == "test-id"
        assert doc.content == "Test content"
        assert doc.metadata == {"type": "test"}
        assert doc.embedding == [0.1, 0.2, 0.3]
    
    def test_vector_document_without_embedding(self):
        """Test creating a VectorDocument without embedding."""
        doc = VectorDocument(
            id="test-id",
            content="Test content",
            metadata={"type": "test"}
        )
        
        assert doc.embedding is None


class TestVectorSearchResult:
    """Test VectorSearchResult dataclass."""
    
    def test_vector_search_result_creation(self):
        """Test creating a VectorSearchResult."""
        result = VectorSearchResult(
            id="result-id",
            score=0.95,
            content="Result content",
            metadata={"source": "test"}
        )
        
        assert result.id == "result-id"
        assert result.score == 0.95
        assert result.content == "Result content"
        assert result.metadata == {"source": "test"}


class TestVectorDatabaseClient:
    """Test VectorDatabaseClient functionality."""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Create a mock Qdrant client."""
        with patch('vector.client.QdrantClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            yield mock_client
    
    @pytest.fixture
    def vector_client(self, mock_qdrant_client):
        """Create a VectorDatabaseClient with mocked dependencies."""
        client = VectorDatabaseClient(
            url="http://test:6333",
            collection_name="test_collection",
            vector_size=384
        )
        return client
    
    def test_client_initialization(self):
        """Test client initialization with custom parameters."""
        client = VectorDatabaseClient(
            url="http://custom:6333",
            api_key="test-key",
            collection_name="custom_collection",
            vector_size=512
        )
        
        assert client.url == "http://custom:6333"
        assert client.api_key == "test-key"
        assert client.collection_name == "custom_collection"
        assert client.vector_size == 512
        assert not client._connected
    
    def test_client_property_creates_qdrant_client(self, vector_client, mock_qdrant_client):
        """Test that accessing client property creates Qdrant client."""
        # Access client property
        client = vector_client.client
        
        # Verify Qdrant client was created
        assert client is mock_qdrant_client
    
    @pytest.mark.asyncio
    async def test_connect_success(self, vector_client, mock_qdrant_client):
        """Test successful connection to vector database."""
        # Mock successful connection
        mock_collections = Mock()
        mock_collections.collections = []
        mock_qdrant_client.get_collections.return_value = mock_collections
        mock_qdrant_client.create_collection.return_value = None
        
        # Test connection
        result = await vector_client.connect()
        
        assert result is True
        assert vector_client._connected is True
        # get_collections is called twice: once in connect() and once in _ensure_collection_exists()
        assert mock_qdrant_client.get_collections.call_count == 2
        mock_qdrant_client.create_collection.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_failure(self, vector_client, mock_qdrant_client):
        """Test connection failure handling."""
        # Mock connection failure
        mock_qdrant_client.get_collections.side_effect = Exception("Connection failed")
        
        # Test connection failure
        with pytest.raises(VectorDatabaseConnectionError):
            await vector_client.connect()
        
        assert vector_client._connected is False
    
    @pytest.mark.asyncio
    async def test_ensure_collection_exists_creates_new(self, vector_client, mock_qdrant_client):
        """Test collection creation when it doesn't exist."""
        # Mock no existing collections
        mock_collections = Mock()
        mock_collections.collections = []
        mock_qdrant_client.get_collections.return_value = mock_collections
        
        # Test collection creation
        await vector_client._ensure_collection_exists()
        
        mock_qdrant_client.create_collection.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ensure_collection_exists_skips_existing(self, vector_client, mock_qdrant_client):
        """Test skipping collection creation when it exists."""
        # Mock existing collection
        mock_collection = Mock()
        mock_collection.name = "test_collection"
        mock_collections = Mock()
        mock_collections.collections = [mock_collection]
        mock_qdrant_client.get_collections.return_value = mock_collections
        
        # Test collection check
        await vector_client._ensure_collection_exists()
        
        mock_qdrant_client.create_collection.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_store_documents_success(self, vector_client, mock_qdrant_client):
        """Test successful document storage."""
        # Setup mocks
        vector_client._connected = True
        mock_qdrant_client.upsert.return_value = None
        
        # Create test documents
        documents = [
            VectorDocument(
                id="doc1",
                content="Content 1",
                metadata={"type": "test"},
                embedding=[0.1] * 384
            ),
            VectorDocument(
                id="doc2",
                content="Content 2",
                metadata={"type": "test"},
                embedding=[0.2] * 384
            )
        ]
        
        # Test storage
        stored_ids = await vector_client.store_documents(documents)
        
        assert stored_ids == ["doc1", "doc2"]
        mock_qdrant_client.upsert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_documents_skips_invalid_embeddings(self, vector_client, mock_qdrant_client):
        """Test that documents with invalid embeddings are skipped."""
        # Setup mocks
        vector_client._connected = True
        mock_qdrant_client.upsert.return_value = None
        
        # Create test documents with invalid embeddings
        documents = [
            VectorDocument(
                id="doc1",
                content="Content 1",
                metadata={"type": "test"},
                embedding=None  # No embedding
            ),
            VectorDocument(
                id="doc2",
                content="Content 2",
                metadata={"type": "test"},
                embedding=[0.2] * 100  # Wrong size
            ),
            VectorDocument(
                id="doc3",
                content="Content 3",
                metadata={"type": "test"},
                embedding=[0.3] * 384  # Correct
            )
        ]
        
        # Test storage
        stored_ids = await vector_client.store_documents(documents)
        
        assert stored_ids == ["doc3"]
        mock_qdrant_client.upsert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_document_single(self, vector_client, mock_qdrant_client):
        """Test storing a single document."""
        # Setup mocks
        vector_client._connected = True
        mock_qdrant_client.upsert.return_value = None
        
        # Create test document
        document = VectorDocument(
            id="doc1",
            content="Content 1",
            metadata={"type": "test"},
            embedding=[0.1] * 384
        )
        
        # Test storage
        stored_id = await vector_client.store_document(document)
        
        assert stored_id == "doc1"
        mock_qdrant_client.upsert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_similar_success(self, vector_client, mock_qdrant_client):
        """Test successful similarity search."""
        # Setup mocks
        vector_client._connected = True
        
        mock_result = Mock()
        mock_result.id = "result1"
        mock_result.score = 0.95
        mock_result.payload = {"content": "Test content", "type": "test"}
        
        mock_qdrant_client.search.return_value = [mock_result]
        
        # Test search
        query_vector = [0.1] * 384
        results = await vector_client.search_similar(query_vector, limit=5)
        
        assert len(results) == 1
        assert results[0].id == "result1"
        assert results[0].score == 0.95
        assert results[0].content == "Test content"
        assert results[0].metadata == {"type": "test"}
        
        mock_qdrant_client.search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_similar_with_filters(self, vector_client, mock_qdrant_client):
        """Test similarity search with metadata filters."""
        # Setup mocks
        vector_client._connected = True
        mock_qdrant_client.search.return_value = []
        
        # Test search with filters
        query_vector = [0.1] * 384
        filter_conditions = {"type": "document", "category": "test"}
        
        await vector_client.search_similar(
            query_vector,
            limit=10,
            filter_conditions=filter_conditions
        )
        
        # Verify search was called with filter
        call_args = mock_qdrant_client.search.call_args
        assert call_args[1]['query_filter'] is not None
    
    @pytest.mark.asyncio
    async def test_get_document_success(self, vector_client, mock_qdrant_client):
        """Test successful document retrieval."""
        # Setup mocks
        vector_client._connected = True
        
        mock_point = Mock()
        mock_point.id = "doc1"
        mock_point.payload = {"content": "Test content", "type": "test"}
        
        mock_qdrant_client.retrieve.return_value = [mock_point]
        
        # Test retrieval
        result = await vector_client.get_document("doc1")
        
        assert result is not None
        assert result.id == "doc1"
        assert result.content == "Test content"
        assert result.metadata == {"type": "test"}
        assert result.score == 1.0
        
        mock_qdrant_client.retrieve.assert_called_once_with(
            collection_name="test_collection",
            ids=["doc1"],
            with_payload=True
        )
    
    @pytest.mark.asyncio
    async def test_get_document_not_found(self, vector_client, mock_qdrant_client):
        """Test document retrieval when document doesn't exist."""
        # Setup mocks
        vector_client._connected = True
        mock_qdrant_client.retrieve.return_value = []
        
        # Test retrieval
        result = await vector_client.get_document("nonexistent")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_document_success(self, vector_client, mock_qdrant_client):
        """Test successful document deletion."""
        # Setup mocks
        vector_client._connected = True
        mock_qdrant_client.delete.return_value = None
        
        # Test deletion
        result = await vector_client.delete_document("doc1")
        
        assert result is True
        mock_qdrant_client.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, vector_client, mock_qdrant_client):
        """Test health check when database is healthy."""
        # Setup mocks
        mock_collections = Mock()
        mock_collections.collections = []
        mock_qdrant_client.get_collections.return_value = mock_collections
        
        # Test health check
        health = await vector_client.health_check()
        
        assert health["status"] == "healthy"
        assert health["connected"] is True
        assert health["collections_count"] == 0
        assert health["collection_exists"] is False
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, vector_client, mock_qdrant_client):
        """Test health check when database is unhealthy."""
        # Setup mocks
        mock_qdrant_client.get_collections.side_effect = Exception("Connection failed")
        
        # Test health check
        health = await vector_client.health_check()
        
        assert health["status"] == "unhealthy"
        assert health["connected"] is False
        assert "error" in health
    
    @pytest.mark.asyncio
    async def test_close_connection(self, vector_client, mock_qdrant_client):
        """Test closing the database connection."""
        # Setup client with connection
        vector_client._client = mock_qdrant_client
        vector_client._connected = True
        
        # Test close
        await vector_client.close()
        
        mock_qdrant_client.close.assert_called_once()
        assert vector_client._client is None
        assert vector_client._connected is False


class TestGlobalClient:
    """Test global client management."""
    
    def test_get_vector_client_singleton(self):
        """Test that get_vector_client returns singleton instance."""
        # Clear global client
        import vector.client
        vector.client._vector_client = None
        
        # Get client instances
        client1 = get_vector_client()
        client2 = get_vector_client()
        
        # Verify same instance
        assert client1 is client2
    
    def test_get_vector_client_with_params(self):
        """Test get_vector_client with custom parameters."""
        # Clear global client
        import vector.client
        vector.client._vector_client = None
        
        # Get client with custom params
        client = get_vector_client(
            collection_name="custom_collection",
            vector_size=512
        )
        
        assert client.collection_name == "custom_collection"
        assert client.vector_size == 512


if __name__ == "__main__":
    pytest.main([__file__])