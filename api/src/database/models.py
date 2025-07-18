"""Database models for DIPC system."""

import enum
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column, String, Text, Integer, BigInteger, DateTime, 
    ForeignKey, Enum, DECIMAL, JSON, Boolean
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from pydantic import BaseModel, Field, field_validator, ConfigDict
import uuid

from .connection import Base


class TaskStatusEnum(enum.Enum):
    """Task status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StoragePolicyEnum(enum.Enum):
    """Storage policy enumeration."""
    PERMANENT = "permanent"
    TEMPORARY = "temporary"


class TaskTypeEnum(enum.Enum):
    """Task type enumeration."""
    DOCUMENT_PARSING = "document_parsing"
    ARCHIVE_PROCESSING = "archive_processing"
    VECTORIZATION = "vectorization"
    CLEANUP = "cleanup"


class Task(Base):
    """Task model for tracking document processing tasks."""
    
    __tablename__ = "tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    parent_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    status = Column(Enum(TaskStatusEnum), nullable=False, default=TaskStatusEnum.PENDING, index=True)
    task_type = Column(String(50), nullable=False)
    file_url = Column(Text, nullable=True)
    original_filename = Column(String(255), nullable=True)
    options = Column(JSON, nullable=False, default=dict)
    estimated_cost = Column(DECIMAL(10, 4), nullable=True)
    actual_cost = Column(DECIMAL(10, 4), nullable=True)
    results = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    parent_task = relationship("Task", remote_side=[id], backref="subtasks")
    file_metadata = relationship("FileMetadata", back_populates="task", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Task(id={self.id}, status={self.status.value}, type={self.task_type})>"
    
    @validates('status')
    def validate_status(self, key, status):
        """Validate status transitions."""
        if isinstance(status, str):
            status = TaskStatusEnum(status)
        return status
    
    @validates('task_type')
    def validate_task_type(self, key, task_type):
        """Validate task type."""
        valid_types = [e.value for e in TaskTypeEnum]
        if task_type not in valid_types:
            raise ValueError(f"Invalid task type: {task_type}. Must be one of: {valid_types}")
        return task_type
    
    @validates('options')
    def validate_options(self, key, options):
        """Validate options JSON structure."""
        if options is None:
            return {}
        if not isinstance(options, dict):
            raise ValueError("Options must be a dictionary")
        return options
    
    def is_completed(self) -> bool:
        """Check if task is in a completed state."""
        return self.status in [TaskStatusEnum.COMPLETED, TaskStatusEnum.FAILED, TaskStatusEnum.CANCELLED]
    
    def is_processing(self) -> bool:
        """Check if task is currently processing."""
        return self.status == TaskStatusEnum.PROCESSING
    
    def has_subtasks(self) -> bool:
        """Check if task has subtasks."""
        return len(self.subtasks) > 0
    
    def get_progress_percentage(self) -> float:
        """Calculate progress percentage for tasks with subtasks."""
        if not self.has_subtasks():
            return 100.0 if self.is_completed() else 0.0
        
        completed_subtasks = sum(1 for subtask in self.subtasks if subtask.is_completed())
        return (completed_subtasks / len(self.subtasks)) * 100.0
    
    def update_status(self, new_status: TaskStatusEnum, error_message: str = None):
        """Update task status with timestamp tracking."""
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)
        
        if error_message:
            self.error_message = error_message
        
        if new_status in [TaskStatusEnum.COMPLETED, TaskStatusEnum.FAILED, TaskStatusEnum.CANCELLED]:
            self.completed_at = datetime.now(timezone.utc)


class FileMetadata(Base):
    """File metadata model for tracking uploaded and processed files."""
    
    __tablename__ = "file_metadata"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    storage_path = Column(Text, nullable=False)
    storage_policy = Column(Enum(StoragePolicyEnum), nullable=False, default=StoragePolicyEnum.TEMPORARY)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    task = relationship("Task", back_populates="file_metadata")
    
    def __repr__(self):
        return f"<FileMetadata(id={self.id}, filename={self.original_filename}, policy={self.storage_policy.value})>"
    
    @validates('file_size')
    def validate_file_size(self, key, file_size):
        """Validate file size is positive."""
        if file_size <= 0:
            raise ValueError("File size must be positive")
        return file_size
    
    @validates('storage_policy')
    def validate_storage_policy(self, key, policy):
        """Validate storage policy."""
        if isinstance(policy, str):
            policy = StoragePolicyEnum(policy)
        return policy
    
    @validates('file_type')
    def validate_file_type(self, key, file_type):
        """Validate file type format."""
        if not file_type or len(file_type.strip()) == 0:
            raise ValueError("File type cannot be empty")
        return file_type.lower()
    
    def is_expired(self) -> bool:
        """Check if file has expired based on TTL."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def should_be_cleaned_up(self) -> bool:
        """Check if file should be cleaned up."""
        return self.storage_policy == StoragePolicyEnum.TEMPORARY and self.is_expired()
    
    def get_file_extension(self) -> str:
        """Get file extension from filename."""
        if '.' in self.original_filename:
            return self.original_filename.rsplit('.', 1)[1].lower()
        return ""
    
    def is_archive_file(self) -> bool:
        """Check if file is an archive type."""
        archive_extensions = ['zip', 'tar', 'gz', 'rar', '7z']
        return self.get_file_extension() in archive_extensions


# Pydantic models for API serialization and validation

class TaskOptions(BaseModel):
    """Task options model for API requests."""
    enable_vectorization: bool = True
    storage_policy: str = Field(default="temporary", pattern="^(permanent|temporary)$")
    max_cost_limit: Optional[float] = Field(default=None, gt=0)
    custom_prompt: Optional[str] = None
    output_format: str = Field(default="json", pattern="^(json|xml|yaml)$")
    
    @field_validator('storage_policy')
    @classmethod
    def validate_storage_policy(cls, v):
        """Validate storage policy value."""
        if v not in ["permanent", "temporary"]:
            raise ValueError("Storage policy must be 'permanent' or 'temporary'")
        return v


class TaskCreateRequest(BaseModel):
    """Request model for creating new tasks."""
    file_urls: List[str] = Field(..., min_items=1, max_items=100)
    user_id: str = Field(..., min_length=1, max_length=255)
    task_type: str = Field(default="document_parsing")
    options: TaskOptions = Field(default_factory=TaskOptions)
    
    @field_validator('file_urls')
    @classmethod
    def validate_file_urls(cls, v):
        """Validate file URLs format."""
        for url in v:
            if not url or not isinstance(url, str):
                raise ValueError("All file URLs must be non-empty strings")
        return v
    
    @field_validator('task_type')
    @classmethod
    def validate_task_type(cls, v):
        """Validate task type."""
        valid_types = [e.value for e in TaskTypeEnum]
        if v not in valid_types:
            raise ValueError(f"Task type must be one of: {valid_types}")
        return v


class TaskResponse(BaseModel):
    """Response model for task data."""
    id: str
    user_id: str
    parent_task_id: Optional[str]
    status: str
    task_type: str
    file_url: Optional[str]
    original_filename: Optional[str]
    options: Dict[str, Any]
    estimated_cost: Optional[float]
    actual_cost: Optional[float]
    results: Optional[Dict[str, Any]]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    progress_percentage: float
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, task: Task):
        """Create response from ORM model."""
        return cls(
            id=str(task.id),
            user_id=task.user_id,
            parent_task_id=str(task.parent_task_id) if task.parent_task_id else None,
            status=task.status.value,
            task_type=task.task_type,
            file_url=task.file_url,
            original_filename=task.original_filename,
            options=task.options or {},
            estimated_cost=float(task.estimated_cost) if task.estimated_cost else None,
            actual_cost=float(task.actual_cost) if task.actual_cost else None,
            results=task.results,
            error_message=task.error_message,
            created_at=task.created_at,
            updated_at=task.updated_at,
            completed_at=task.completed_at,
            progress_percentage=task.get_progress_percentage()
        )


class FileMetadataResponse(BaseModel):
    """Response model for file metadata."""
    id: str
    task_id: str
    original_filename: str
    file_type: str
    file_size: int
    storage_path: str
    storage_policy: str
    expires_at: Optional[datetime]
    created_at: datetime
    is_expired: bool
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, file_metadata: FileMetadata):
        """Create response from ORM model."""
        return cls(
            id=str(file_metadata.id),
            task_id=str(file_metadata.task_id),
            original_filename=file_metadata.original_filename,
            file_type=file_metadata.file_type,
            file_size=file_metadata.file_size,
            storage_path=file_metadata.storage_path,
            storage_policy=file_metadata.storage_policy.value,
            expires_at=file_metadata.expires_at,
            created_at=file_metadata.created_at,
            is_expired=file_metadata.is_expired()
        )


class TokenUsage(BaseModel):
    """Model for tracking LLM token usage."""
    prompt_tokens: int = Field(..., ge=0)
    completion_tokens: int = Field(..., ge=0)
    total_tokens: int = Field(..., ge=0)
    estimated_cost: float = Field(..., ge=0)
    
    @field_validator('total_tokens')
    @classmethod
    def validate_total_tokens(cls, v, info):
        """Validate that total tokens equals sum of prompt and completion tokens."""
        if info.data and 'prompt_tokens' in info.data and 'completion_tokens' in info.data:
            expected_total = info.data['prompt_tokens'] + info.data['completion_tokens']
            if v != expected_total:
                raise ValueError(f"Total tokens ({v}) must equal prompt_tokens + completion_tokens ({expected_total})")
        return v


class DocumentMetadata(BaseModel):
    """Model for document processing metadata."""
    file_type: str
    page_count: Optional[int] = None
    language: Optional[str] = None
    extraction_method: str
    processing_time: float = Field(..., ge=0)
    confidence_score: float = Field(..., ge=0, le=1)


class DocumentParsingResult(BaseModel):
    """Model for document parsing results."""
    task_id: str
    extracted_content: Dict[str, Any]
    confidence_score: float = Field(..., ge=0, le=1)
    processing_time: float = Field(..., ge=0)
    token_usage: TokenUsage
    metadata: DocumentMetadata
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }