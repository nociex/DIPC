"""Pydantic models for API request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, ConfigDict


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """Task type enumeration."""
    DOCUMENT_PARSING = "document_parsing"
    ARCHIVE_PROCESSING = "archive_processing"
    VECTORIZATION = "vectorization"
    CLEANUP = "cleanup"


class StoragePolicy(str, Enum):
    """Storage policy enumeration."""
    PERMANENT = "permanent"
    TEMPORARY = "temporary"


class TaskOptions(BaseModel):
    """Task configuration options."""
    model_config = ConfigDict(protected_namespaces=())
    
    enable_vectorization: bool = Field(
        default=True,
        description="Whether to enable vectorization of processed content"
    )
    storage_policy: StoragePolicy = Field(
        default=StoragePolicy.TEMPORARY,
        description="Storage policy for processed files"
    )
    max_cost_limit: Optional[float] = Field(
        default=None,
        ge=0,
        description="Maximum cost limit for processing (USD)"
    )
    llm_provider: Optional[str] = Field(
        default=None,
        description="Preferred LLM provider (openai, openrouter, litelm)"
    )
    model_name: Optional[str] = Field(
        default=None,
        description="Specific model name to use for processing"
    )

    @field_validator('llm_provider')
    @classmethod
    def validate_llm_provider(cls, v):
        """Validate LLM provider."""
        if v is not None:
            allowed_providers = ['openai', 'openrouter', 'litelm']
            if v not in allowed_providers:
                raise ValueError(f'LLM provider must be one of: {allowed_providers}')
        return v


class TaskCreateRequest(BaseModel):
    """Request model for creating a new task."""
    file_urls: List[str] = Field(
        ...,
        min_length=1,
        description="List of file URLs to process"
    )
    user_id: str = Field(
        ...,
        min_length=1,
        description="User identifier"
    )
    options: TaskOptions = Field(
        default_factory=TaskOptions,
        description="Task processing options"
    )

    @field_validator('file_urls')
    @classmethod
    def validate_file_urls(cls, v):
        """Validate file URLs."""
        for url in v:
            if not url.strip():
                raise ValueError('File URLs cannot be empty')
        return v


class TokenUsage(BaseModel):
    """Token usage information."""
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    estimated_cost: float = Field(ge=0)


class DocumentMetadata(BaseModel):
    """Document metadata information."""
    file_type: str
    file_size: Optional[int] = Field(default=None, ge=0)
    page_count: Optional[int] = Field(default=None, ge=0)
    language: Optional[str] = None
    extraction_method: str
    processing_time: Optional[float] = Field(default=None, ge=0)


class TaskResponse(BaseModel):
    """Response model for task information."""
    task_id: UUID
    user_id: str
    parent_task_id: Optional[UUID] = None
    status: TaskStatus
    task_type: TaskType
    file_url: Optional[str] = None
    options: TaskOptions
    estimated_cost: Optional[float] = Field(default=None, ge=0)
    actual_cost: Optional[float] = Field(default=None, ge=0)
    results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    token_usage: Optional[TokenUsage] = None
    metadata: Optional[DocumentMetadata] = None


class TaskStatusResponse(BaseModel):
    """Response model for task status information."""
    task_id: UUID
    status: TaskStatus
    progress: Optional[float] = Field(default=None, ge=0, le=100)
    estimated_completion_time: Optional[datetime] = None
    error_message: Optional[str] = None
    updated_at: datetime


class TaskListResponse(BaseModel):
    """Response model for task list."""
    tasks: List[TaskResponse]
    total_count: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    has_next: bool


class PresignedUrlRequest(BaseModel):
    """Request model for generating pre-signed URLs."""
    filename: str = Field(
        ...,
        min_length=1,
        description="Original filename"
    )
    content_type: str = Field(
        ...,
        min_length=1,
        description="MIME type of the file"
    )
    file_size: int = Field(
        ...,
        gt=0,
        le=100 * 1024 * 1024,  # 100MB limit
        description="File size in bytes"
    )

    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v):
        """Validate filename."""
        # Basic filename validation
        if not v.strip():
            raise ValueError('Filename cannot be empty')
        
        # Check for path traversal attempts
        if '..' in v or '/' in v or '\\' in v:
            raise ValueError('Invalid filename: path traversal detected')
        
        return v.strip()

    @field_validator('content_type')
    @classmethod
    def validate_content_type(cls, v):
        """Validate content type."""
        allowed_types = [
            'application/pdf',
            'image/jpeg',
            'image/png',
            'image/gif',
            'image/webp',
            'text/plain',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/zip',
            'application/x-zip-compressed'
        ]
        
        if v not in allowed_types:
            raise ValueError(f'Content type {v} is not supported')
        
        return v


class PresignedUrlResponse(BaseModel):
    """Response model for pre-signed URL generation."""
    upload_url: str = Field(description="Pre-signed URL for file upload")
    file_id: str = Field(description="Unique file identifier")
    expires_at: datetime = Field(description="URL expiration timestamp")
    max_file_size: int = Field(description="Maximum allowed file size")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error_code: str = Field(description="Machine-readable error code")
    error_message: str = Field(description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )
    request_id: str = Field(description="Request identifier for tracking")
    timestamp: float = Field(description="Error timestamp")


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(description="Overall health status")
    service: str = Field(description="Service name")
    version: str = Field(description="Service version")
    timestamp: float = Field(description="Health check timestamp")
    components: Optional[Dict[str, Dict[str, Any]]] = Field(
        default=None,
        description="Individual component health status"
    )