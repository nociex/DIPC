"""Configuration management for worker processes."""

import os
from typing import Optional
from pydantic import validator
from pydantic_settings import BaseSettings


class WorkerSettings(BaseSettings):
    """Worker-specific settings with environment variable validation."""
    
    # Database Configuration
    database_url: str = "postgresql://test:test@localhost:5432/test"
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    celery_broker_url: str = "redis://localhost:6379"
    celery_result_backend: str = "redis://localhost:6379"
    
    # Storage Configuration
    storage_type: str = "local"
    
    # S3/MinIO Configuration (optional for local storage)
    s3_endpoint_url: Optional[str] = None
    s3_access_key_id: Optional[str] = None
    s3_secret_access_key: Optional[str] = None
    s3_bucket_name: Optional[str] = None
    
    # LLM Provider Configuration
    openai_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    litelm_base_url: Optional[str] = None
    litelm_api_key: Optional[str] = None
    
    # Vector Database Configuration
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    
    # Processing Configuration
    max_file_size_mb: int = 100
    max_archive_size_mb: int = 500
    max_extraction_files: int = 1000
    processing_timeout_seconds: int = 300
    
    # Security Configuration
    temp_processing_dir: str = "/tmp/processing"
    allowed_file_types: str = "pdf,png,jpg,jpeg,docx,txt,zip"
    
    # Application Configuration
    environment: str = "development"
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @validator('allowed_file_types')
    def parse_allowed_file_types(cls, v):
        """Parse allowed file types from comma-separated string."""
        if isinstance(v, str):
            return [ext.strip().lower() for ext in v.split(',')]
        return v
    
    @validator('temp_processing_dir')
    def validate_processing_dir(cls, v):
        """Ensure processing directory exists and is writable."""
        os.makedirs(v, exist_ok=True)
        if not os.access(v, os.W_OK):
            raise ValueError(f"Processing directory {v} is not writable")
        return v
    
    def has_llm_provider(self) -> bool:
        """Check if at least one LLM provider is configured."""
        return any([
            self.openai_api_key,
            self.openrouter_api_key,
            self.litelm_api_key
        ])


# Global worker settings instance
worker_settings = WorkerSettings()


def validate_worker_settings():
    """Validate worker-specific settings."""
    errors = []
    
    # Check required settings
    if not worker_settings.database_url:
        errors.append("DATABASE_URL is required")
    
    if not worker_settings.celery_broker_url:
        errors.append("CELERY_BROKER_URL is required")
    
    # Check S3 configuration only if using S3 storage
    if worker_settings.storage_type == "s3" and not all([
        worker_settings.s3_endpoint_url,
        worker_settings.s3_access_key_id,
        worker_settings.s3_secret_access_key,
        worker_settings.s3_bucket_name
    ]):
        errors.append("S3 configuration is incomplete when using S3 storage")
    
    # Check LLM provider
    if not worker_settings.has_llm_provider():
        errors.append("At least one LLM provider API key is required")
    
    # Check processing limits
    if worker_settings.max_file_size_mb <= 0:
        errors.append("MAX_FILE_SIZE_MB must be positive")
    
    if worker_settings.processing_timeout_seconds <= 0:
        errors.append("PROCESSING_TIMEOUT_SECONDS must be positive")
    
    if errors:
        raise ValueError(f"Worker configuration errors: {', '.join(errors)}")


def get_celery_config() -> dict:
    """Get Celery configuration dictionary."""
    return {
        'broker_url': worker_settings.celery_broker_url,
        'result_backend': worker_settings.celery_result_backend,
        'task_serializer': 'json',
        'accept_content': ['json'],
        'result_serializer': 'json',
        'timezone': 'UTC',
        'enable_utc': True,
        'task_routes': {
            'src.tasks.archive.*': {'queue': 'archive_processing'},
            'src.tasks.parsing.*': {'queue': 'document_parsing'},
            'src.tasks.vectorization.*': {'queue': 'vectorization'},
            'src.tasks.cleanup.*': {'queue': 'cleanup'},
        },
        'task_default_queue': 'document_parsing',
        'worker_prefetch_multiplier': 1,
        'task_acks_late': True,
        'worker_max_tasks_per_child': 1000,
    }