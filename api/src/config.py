"""Configuration management and environment variable validation."""

import os
from typing import Optional
from pydantic import field_validator, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable validation."""
    
    # Database Configuration
    database_url: str
    
    # Redis Configuration
    redis_url: str
    celery_broker_url: str
    celery_result_backend: str
    
    # Storage Configuration
    storage_type: str = "local"
    
    # S3/MinIO Configuration (optional for local storage)
    s3_endpoint_url: Optional[str] = None
    s3_access_key_id: Optional[str] = None
    s3_secret_access_key: Optional[str] = None
    s3_bucket_name: Optional[str] = None
    
    # Local Storage Configuration
    local_storage_path: str = "/app/storage"
    storage_base_url: str = "http://localhost:38100/storage"
    
    # LLM Provider Configuration
    openai_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    litelm_base_url: Optional[str] = None
    litelm_api_key: Optional[str] = None
    
    # Vector Database Configuration
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    
    # Application Configuration
    environment: str = "development"
    log_level: str = "INFO"
    max_cost_limit: float = 50.0
    default_storage_policy: str = "temporary"
    temp_file_ttl_hours: int = 24
    
    # Security Configuration
    secret_key: str
    jwt_secret_key: str
    cors_origins: str = "http://localhost:3000"
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False
    )
    
    @field_validator('cors_origins')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v):
        """Validate environment value."""
        allowed_envs = ['development', 'staging', 'production']
        if v not in allowed_envs:
            raise ValueError(f'Environment must be one of: {allowed_envs}')
        return v
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        allowed_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed_levels:
            raise ValueError(f'Log level must be one of: {allowed_levels}')
        return v.upper()
    
    def has_llm_provider(self) -> bool:
        """Check if at least one LLM provider is configured."""
        return any([
            self.openai_api_key,
            self.openrouter_api_key,
            self.litelm_api_key
        ])


# Global settings instance
settings = Settings()


def validate_required_settings():
    """Validate that all required settings are present."""
    errors = []
    
    # Check database connection
    if not settings.database_url:
        errors.append("DATABASE_URL is required")
    
    # Check Redis connection
    if not settings.redis_url:
        errors.append("REDIS_URL is required")
    
    # Check S3 configuration only if using S3 storage
    if settings.storage_type == "s3" and not all([
        settings.s3_endpoint_url,
        settings.s3_access_key_id,
        settings.s3_secret_access_key,
        settings.s3_bucket_name
    ]):
        errors.append("S3 configuration is incomplete when using S3 storage")
    
    # Check security keys
    if not settings.secret_key:
        errors.append("SECRET_KEY is required")
    
    if not settings.jwt_secret_key:
        errors.append("JWT_SECRET_KEY is required")
    
    # Check LLM provider
    if not settings.has_llm_provider():
        errors.append("At least one LLM provider API key is required")
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")


def get_llm_provider_config() -> dict:
    """Get available LLM provider configurations."""
    providers = {}
    
    if settings.openai_api_key:
        providers['openai'] = {
            'base_url': 'https://api.openai.com/v1',
            'api_key': settings.openai_api_key
        }
    
    if settings.openrouter_api_key:
        providers['openrouter'] = {
            'base_url': 'https://openrouter.ai/api/v1',
            'api_key': settings.openrouter_api_key
        }
    
    if settings.litelm_api_key and settings.litelm_base_url:
        providers['litelm'] = {
            'base_url': settings.litelm_base_url,
            'api_key': settings.litelm_api_key
        }
    
    return providers


# Add method to Settings class for compatibility
Settings.get_llm_provider_config = lambda self: get_llm_provider_config()