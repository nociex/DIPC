"""Vector database client implementation with Qdrant support."""

import uuid
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import structlog
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from config import worker_settings

logger = structlog.get_logger(__name__)


@dataclass
class VectorDocument:
    """Represents a document to be stored in the vector database."""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


@dataclass
class VectorSearchResult:
    """Represents a search result from the vector database."""
    id: str
    score: float
    content: str
    metadata: Dict[str, Any]


class VectorDatabaseError(Exception):
    """Base exception for vector database operations."""
    pass


class VectorDatabaseConnectionError(VectorDatabaseError):
    """Exception raised when connection to vector database fails."""
    pass


class VectorDatabaseClient:
    """
    Vector database client with Qdrant backend support.
    
    Provides high-level operations for storing and retrieving document vectors.
    """
    
    def __init__(
        self,
        url: str = None,
        api_key: str = None,
        collection_name: str = "documents",
        vector_size: int = 1536  # OpenAI embedding size
    ):
        """
        Initialize the vector database client.
        
        Args:
            url: Qdrant server URL
            api_key: Optional API key for authentication
            collection_name: Name of the collection to use
            vector_size: Dimension of the vectors (default: 1536 for OpenAI embeddings)
        """
        self.url = url or worker_settings.qdrant_url
        self.api_key = api_key or worker_settings.qdrant_api_key
        self.collection_name = collection_name
        self.vector_size = vector_size
        
        self._client = None
        self._connected = False
        
        logger.info(
            "Initializing vector database client",
            url=self.url,
            collection_name=self.collection_name,
            vector_size=self.vector_size
        )
    
    @property
    def client(self) -> QdrantClient:
        """Get or create Qdrant client instance."""
        if self._client is None:
            try:
                self._client = QdrantClient(
                    url=self.url,
                    api_key=self.api_key,
                    timeout=30
                )
                logger.info("Qdrant client created successfully")
            except Exception as e:
                logger.error("Failed to create Qdrant client", error=str(e))
                raise VectorDatabaseConnectionError(f"Failed to create Qdrant client: {e}")
        
        return self._client
    
    async def connect(self) -> bool:
        """
        Establish connection to the vector database and ensure collection exists.
        
        Returns:
            bool: True if connection successful
            
        Raises:
            VectorDatabaseConnectionError: If connection fails
        """
        try:
            # Test connection
            info = self.client.get_collections()
            logger.info("Connected to Qdrant", collections_count=len(info.collections))
            
            # Ensure collection exists
            await self._ensure_collection_exists()
            
            self._connected = True
            return True
            
        except Exception as e:
            logger.error("Failed to connect to vector database", error=str(e))
            raise VectorDatabaseConnectionError(f"Connection failed: {e}")
    
    async def _ensure_collection_exists(self):
        """Create collection if it doesn't exist."""
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                logger.info("Creating collection", collection_name=self.collection_name)
                
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.vector_size,
                        distance=models.Distance.COSINE
                    )
                )
                
                logger.info("Collection created successfully", collection_name=self.collection_name)
            else:
                logger.info("Collection already exists", collection_name=self.collection_name)
                
        except Exception as e:
            logger.error("Failed to ensure collection exists", error=str(e))
            raise VectorDatabaseError(f"Collection setup failed: {e}")
    
    async def store_documents(self, documents: List[VectorDocument]) -> List[str]:
        """
        Store multiple documents in the vector database.
        
        Args:
            documents: List of VectorDocument objects to store
            
        Returns:
            List[str]: List of document IDs that were stored
            
        Raises:
            VectorDatabaseError: If storage operation fails
        """
        if not self._connected:
            await self.connect()
        
        if not documents:
            return []
        
        try:
            points = []
            stored_ids = []
            
            for doc in documents:
                if not doc.embedding:
                    logger.warning("Document has no embedding, skipping", doc_id=doc.id)
                    continue
                
                if len(doc.embedding) != self.vector_size:
                    logger.error(
                        "Invalid embedding size",
                        doc_id=doc.id,
                        expected_size=self.vector_size,
                        actual_size=len(doc.embedding)
                    )
                    continue
                
                point = models.PointStruct(
                    id=doc.id,
                    vector=doc.embedding,
                    payload={
                        "content": doc.content,
                        **doc.metadata
                    }
                )
                points.append(point)
                stored_ids.append(doc.id)
            
            if points:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                
                logger.info(
                    "Documents stored successfully",
                    collection_name=self.collection_name,
                    count=len(points)
                )
            
            return stored_ids
            
        except Exception as e:
            logger.error("Failed to store documents", error=str(e))
            raise VectorDatabaseError(f"Storage operation failed: {e}")
    
    async def store_document(self, document: VectorDocument) -> str:
        """
        Store a single document in the vector database.
        
        Args:
            document: VectorDocument to store
            
        Returns:
            str: Document ID that was stored
        """
        stored_ids = await self.store_documents([document])
        return stored_ids[0] if stored_ids else None
    
    async def search_similar(
        self,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """
        Search for similar documents using vector similarity.
        
        Args:
            query_vector: Query vector to search with
            limit: Maximum number of results to return
            score_threshold: Minimum similarity score threshold
            filter_conditions: Optional metadata filters
            
        Returns:
            List[VectorSearchResult]: List of similar documents
        """
        if not self._connected:
            await self.connect()
        
        try:
            search_filter = None
            if filter_conditions:
                # Convert filter conditions to Qdrant filter format
                search_filter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value)
                        )
                        for key, value in filter_conditions.items()
                    ]
                )
            
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=search_filter,
                with_payload=True
            )
            
            results = []
            for result in search_results:
                results.append(VectorSearchResult(
                    id=str(result.id),
                    score=result.score,
                    content=result.payload.get("content", ""),
                    metadata={k: v for k, v in result.payload.items() if k != "content"}
                ))
            
            logger.info(
                "Vector search completed",
                query_size=len(query_vector),
                results_count=len(results),
                score_threshold=score_threshold
            )
            
            return results
            
        except Exception as e:
            logger.error("Vector search failed", error=str(e))
            raise VectorDatabaseError(f"Search operation failed: {e}")
    
    async def get_document(self, document_id: str) -> Optional[VectorSearchResult]:
        """
        Retrieve a specific document by ID.
        
        Args:
            document_id: ID of the document to retrieve
            
        Returns:
            VectorSearchResult: Document if found, None otherwise
        """
        if not self._connected:
            await self.connect()
        
        try:
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[document_id],
                with_payload=True
            )
            
            if result:
                point = result[0]
                return VectorSearchResult(
                    id=str(point.id),
                    score=1.0,  # Perfect match for direct retrieval
                    content=point.payload.get("content", ""),
                    metadata={k: v for k, v in point.payload.items() if k != "content"}
                )
            
            return None
            
        except Exception as e:
            logger.error("Failed to retrieve document", document_id=document_id, error=str(e))
            raise VectorDatabaseError(f"Document retrieval failed: {e}")
    
    async def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from the vector database.
        
        Args:
            document_id: ID of the document to delete
            
        Returns:
            bool: True if deletion successful
        """
        if not self._connected:
            await self.connect()
        
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=[document_id]
                )
            )
            
            logger.info("Document deleted successfully", document_id=document_id)
            return True
            
        except Exception as e:
            logger.error("Failed to delete document", document_id=document_id, error=str(e))
            raise VectorDatabaseError(f"Document deletion failed: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the vector database.
        
        Returns:
            Dict containing health status information
        """
        try:
            # Test basic connectivity
            collections = self.client.get_collections()
            
            # Get collection info if it exists
            collection_info = None
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name in collection_names:
                collection_info = self.client.get_collection(self.collection_name)
            
            health_status = {
                "status": "healthy",
                "connected": True,
                "url": self.url,
                "collections_count": len(collections.collections),
                "target_collection": self.collection_name,
                "collection_exists": self.collection_name in collection_names,
                "collection_info": {
                    "vectors_count": collection_info.vectors_count if collection_info else 0,
                    "indexed_vectors_count": collection_info.indexed_vectors_count if collection_info else 0,
                    "points_count": collection_info.points_count if collection_info else 0,
                } if collection_info else None
            }
            
            logger.info("Vector database health check passed", **health_status)
            return health_status
            
        except Exception as e:
            error_status = {
                "status": "unhealthy",
                "connected": False,
                "url": self.url,
                "error": str(e)
            }
            
            logger.error("Vector database health check failed", **error_status)
            return error_status
    
    async def close(self):
        """Close the vector database connection."""
        if self._client:
            try:
                self._client.close()
                logger.info("Vector database connection closed")
            except Exception as e:
                logger.warning("Error closing vector database connection", error=str(e))
            finally:
                self._client = None
                self._connected = False


# Global client instance
_vector_client = None


def get_vector_client(
    collection_name: str = "documents",
    vector_size: int = 1536
) -> VectorDatabaseClient:
    """
    Get or create a global vector database client instance.
    
    Args:
        collection_name: Name of the collection to use
        vector_size: Dimension of the vectors
        
    Returns:
        VectorDatabaseClient: Configured client instance
    """
    global _vector_client
    
    if _vector_client is None:
        _vector_client = VectorDatabaseClient(
            collection_name=collection_name,
            vector_size=vector_size
        )
    
    return _vector_client