"""Vectorization tasks."""

import asyncio
import uuid
from typing import Dict, Any, List, Optional
import structlog

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from celery_app import celery_app
from tasks.base import BaseTask, TaskStatus, create_task_result, validate_task_input
from llm.factory import LLMClientFactory, LLMProvider, LLMConfigurationError
from llm.exceptions import LLMProviderError
from vector.client import get_vector_client, VectorDocument, VectorDatabaseError

logger = structlog.get_logger(__name__)


class VectorizationError(Exception):
    """Exception raised during vectorization process."""
    pass


def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """
    Split text into overlapping chunks for vectorization.
    
    Args:
        text: Text to chunk
        chunk_size: Maximum size of each chunk
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    # Handle empty or whitespace-only text
    if not text or not text.strip():
        return []
    
    text = text.strip()
    
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # If this isn't the last chunk, try to break at a word boundary
        if end < len(text):
            # Look for the last space within the chunk
            last_space = text.rfind(' ', start, end)
            if last_space > start:
                end = last_space
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start position, accounting for overlap
        start = max(start + 1, end - overlap)
        
        # Prevent infinite loop
        if start >= len(text):
            break
    
    return chunks


def _generate_embeddings(client, texts: List[str], model: str = "text-embedding-ada-002") -> List[List[float]]:
    """
    Generate embeddings for a list of texts using OpenAI API.
    
    Args:
        client: OpenAI client
        texts: List of texts to embed
        model: Embedding model to use
        
    Returns:
        List of embedding vectors
        
    Raises:
        LLMProviderError: If embedding generation fails
    """
    try:
        response = client.embeddings.create(
            input=texts,
            model=model
        )
        
        embeddings = [data.embedding for data in response.data]
        
        logger.info(
            "Generated embeddings successfully",
            text_count=len(texts),
            embedding_dimension=len(embeddings[0]) if embeddings else 0,
            model=model
        )
        
        return embeddings
        
    except Exception as e:
        logger.error("Failed to generate embeddings", error=str(e), model=model)
        raise LLMProviderError(f"Embedding generation failed: {e}", "unknown")


async def _store_vectors(
    vector_client,
    task_id: str,
    chunks: List[str],
    embeddings: List[List[float]],
    metadata: Dict[str, Any]
) -> List[str]:
    """
    Store text chunks and their embeddings in the vector database.
    
    Args:
        vector_client: Vector database client
        task_id: Task ID for tracking
        chunks: Text chunks
        embeddings: Corresponding embeddings
        metadata: Additional metadata to store
        
    Returns:
        List of stored document IDs
        
    Raises:
        VectorDatabaseError: If storage fails
    """
    documents = []
    
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        doc_id = f"{task_id}_{i}"
        
        doc_metadata = {
            **metadata,
            "task_id": task_id,
            "chunk_index": i,
            "chunk_count": len(chunks),
            "created_at": str(asyncio.get_event_loop().time())
        }
        
        document = VectorDocument(
            id=doc_id,
            content=chunk,
            metadata=doc_metadata,
            embedding=embedding
        )
        
        documents.append(document)
    
    # Store all documents
    stored_ids = await vector_client.store_documents(documents)
    
    logger.info(
        "Stored vectors successfully",
        task_id=task_id,
        documents_stored=len(stored_ids),
        total_chunks=len(chunks)
    )
    
    return stored_ids


@celery_app.task(bind=True, base=BaseTask, name='workers.tasks.vectorization.vectorize_content_task')
def vectorize_content_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Vectorize processed content and store in vector database.
    
    Args:
        task_data: Dictionary containing task information
            - task_id: UUID of the task
            - content: Processed content to vectorize (string or dict)
            - user_id: ID of the user who submitted the task
            - options: Optional task options including vectorization settings
            - metadata: Optional metadata to store with vectors
    
    Returns:
        Dict containing vectorization results
    """
    # Validate input
    validate_task_input(task_data, ['task_id', 'content', 'user_id'])
    
    task_id = task_data['task_id']
    content = task_data['content']
    user_id = task_data['user_id']
    options = task_data.get('options', {})
    metadata = task_data.get('metadata', {})
    
    logger.info(
        "Starting vectorization task",
        task_id=task_id,
        user_id=user_id,
        content_type=type(content).__name__,
        options=options
    )
    
    try:
        # Check if vectorization is enabled
        enable_vectorization = options.get('enable_vectorization', True)
        if not enable_vectorization:
            logger.info("Vectorization disabled by user options", task_id=task_id)
            return create_task_result(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                result={
                    "message": "Vectorization skipped - disabled by user",
                    "vectors_stored": 0,
                    "vector_ids": [],
                    "vectorization_enabled": False
                }
            ).dict()
        
        # Extract text content for vectorization
        if isinstance(content, dict):
            # If content is structured, extract text fields
            text_content = []
            
            # Common text fields to extract
            text_fields = ['text', 'content', 'extracted_text', 'summary', 'description']
            
            for field in text_fields:
                if field in content and isinstance(content[field], str):
                    text_content.append(content[field])
            
            # Also check for nested content
            if 'extracted_content' in content and isinstance(content['extracted_content'], dict):
                for key, value in content['extracted_content'].items():
                    if isinstance(value, str) and len(value.strip()) > 0:
                        text_content.append(f"{key}: {value}")
            
            # Join all text content
            full_text = "\n\n".join(text_content)
            
        elif isinstance(content, str):
            full_text = content
        else:
            full_text = str(content)
        
        # Validate text content
        if not full_text or len(full_text.strip()) < 10:
            logger.warning("Content too short for vectorization", task_id=task_id, length=len(full_text))
            return create_task_result(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                result={
                    "message": "Content too short for vectorization",
                    "vectors_stored": 0,
                    "vector_ids": [],
                    "content_length": len(full_text)
                }
            ).dict()
        
        # Chunk the text for vectorization
        chunk_size = options.get('chunk_size', 1000)
        chunk_overlap = options.get('chunk_overlap', 100)
        chunks = _chunk_text(full_text, chunk_size=chunk_size, overlap=chunk_overlap)
        
        logger.info(
            "Text chunked for vectorization",
            task_id=task_id,
            original_length=len(full_text),
            chunk_count=len(chunks),
            chunk_size=chunk_size
        )
        
        # Create LLM client for embeddings
        try:
            llm_client = LLMClientFactory.create_default_client()
            embedding_model = options.get('embedding_model', 'text-embedding-ada-002')
            
        except LLMConfigurationError as e:
            logger.error("Failed to create LLM client for embeddings", task_id=task_id, error=str(e))
            raise VectorizationError(f"LLM client configuration failed: {e}")
        
        # Generate embeddings
        try:
            embeddings = _generate_embeddings(llm_client, chunks, model=embedding_model)
            
        except LLMProviderError as e:
            logger.error("Failed to generate embeddings", task_id=task_id, error=str(e))
            raise VectorizationError(f"Embedding generation failed: {e}")
        
        # Prepare metadata for storage
        vector_metadata = {
            **metadata,
            "user_id": user_id,
            "original_content_length": len(full_text),
            "embedding_model": embedding_model,
            "vectorization_timestamp": str(asyncio.get_event_loop().time())
        }
        
        # Store vectors in database
        try:
            vector_client = get_vector_client()
            
            # Run async storage in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                stored_ids = loop.run_until_complete(
                    _store_vectors(vector_client, task_id, chunks, embeddings, vector_metadata)
                )
            finally:
                loop.close()
            
        except VectorDatabaseError as e:
            logger.error("Failed to store vectors", task_id=task_id, error=str(e))
            raise VectorizationError(f"Vector storage failed: {e}")
        
        # Create success result
        result = create_task_result(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            result={
                "message": "Content vectorized successfully",
                "vectors_stored": len(stored_ids),
                "vector_ids": stored_ids,
                "chunk_count": len(chunks),
                "embedding_model": embedding_model,
                "original_content_length": len(full_text),
                "vectorization_enabled": True
            }
        )
        
        logger.info(
            "Vectorization task completed successfully",
            task_id=task_id,
            vectors_stored=len(stored_ids),
            chunk_count=len(chunks)
        )
        
        return result.dict()
        
    except VectorizationError:
        # Re-raise vectorization errors as-is
        raise
        
    except Exception as e:
        logger.error("Unexpected error in vectorization task", task_id=task_id, error=str(e))
        
        # Create error result
        result = create_task_result(
            task_id=task_id,
            status=TaskStatus.FAILED,
            result={
                "error": f"Vectorization failed: {str(e)}",
                "vectors_stored": 0,
                "vector_ids": []
            }
        )
        
        return result.dict()