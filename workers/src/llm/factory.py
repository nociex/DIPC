"""LLM client factory with multi-provider support."""

import os
from enum import Enum
from typing import Optional, Dict, Any
from openai import OpenAI
from pydantic import BaseModel, field_validator

from .exceptions import LLMConfigurationError, LLMProviderError


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    OPENROUTER = "openrouter"
    LITELM = "litelm"


class LLMProviderConfig(BaseModel):
    """Configuration for an LLM provider."""
    base_url: str
    api_key: str
    model: Optional[str] = None
    timeout: int = 60
    max_retries: int = 3
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v):
        if not v or v.strip() == "":
            raise ValueError("API key cannot be empty")
        return v
    
    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, v):
        if not v or not v.startswith(('http://', 'https://')):
            raise ValueError("Base URL must be a valid HTTP/HTTPS URL")
        return v.rstrip('/')


class LLMClientFactory:
    """Factory for creating LLM clients with different providers."""
    
    # Default configurations for each provider
    DEFAULT_CONFIGS = {
        LLMProvider.OPENAI: {
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4-vision-preview"
        },
        LLMProvider.OPENROUTER: {
            "base_url": "https://openrouter.ai/api/v1",
            "model": "openai/gpt-4-vision-preview"
        },
        LLMProvider.LITELM: {
            "base_url": None,  # Must be provided via environment
            "model": None      # Must be provided via environment
        }
    }
    
    @classmethod
    def create_client(cls, provider: LLMProvider, config: Optional[LLMProviderConfig] = None) -> OpenAI:
        """
        Create an OpenAI-compatible client for the specified provider.
        
        Args:
            provider: The LLM provider to use
            config: Optional provider configuration. If not provided, will use environment variables.
            
        Returns:
            OpenAI client configured for the specified provider
            
        Raises:
            LLMConfigurationError: If provider configuration is invalid or missing
        """
        if config is None:
            config = cls._get_config_from_env(provider)
        
        try:
            # Create OpenAI client with provider-specific configuration
            client = OpenAI(
                base_url=config.base_url,
                api_key=config.api_key,
                timeout=config.timeout,
                max_retries=config.max_retries
            )
            
            # Store provider info for debugging
            client._provider = provider.value
            client._model = config.model
            
            return client
            
        except Exception as e:
            raise LLMConfigurationError(
                f"Failed to create {provider.value} client: {str(e)}"
            )
    
    @classmethod
    def _get_config_from_env(cls, provider: LLMProvider) -> LLMProviderConfig:
        """Get provider configuration from environment variables."""
        default_config = cls.DEFAULT_CONFIGS[provider]
        
        # Environment variable mapping
        env_mappings = {
            LLMProvider.OPENAI: {
                "api_key": "OPENAI_API_KEY",
                "base_url": "OPENAI_BASE_URL",
                "model": "OPENAI_MODEL"
            },
            LLMProvider.OPENROUTER: {
                "api_key": "OPENROUTER_API_KEY", 
                "base_url": "OPENROUTER_BASE_URL",
                "model": "OPENROUTER_MODEL"
            },
            LLMProvider.LITELM: {
                "api_key": "LITELM_API_KEY",
                "base_url": "LITELM_BASE_URL", 
                "model": "LITELM_MODEL"
            }
        }
        
        env_vars = env_mappings[provider]
        
        # Get API key (required)
        api_key = os.getenv(env_vars["api_key"])
        if not api_key:
            raise LLMConfigurationError(
                f"Missing required environment variable: {env_vars['api_key']}"
            )
        
        # Get base URL (use default if not provided, except for LiteLM)
        base_url = os.getenv(env_vars["base_url"]) or default_config["base_url"]
        if not base_url:
            raise LLMConfigurationError(
                f"Missing required environment variable: {env_vars['base_url']}"
            )
        
        # Get model (use default if not provided)
        model = os.getenv(env_vars["model"]) or default_config["model"]
        
        return LLMProviderConfig(
            base_url=base_url,
            api_key=api_key,
            model=model
        )
    
    @classmethod
    def get_available_providers(cls) -> Dict[str, bool]:
        """
        Check which providers are available based on environment configuration.
        
        Returns:
            Dictionary mapping provider names to availability status
        """
        availability = {}
        
        for provider in LLMProvider:
            try:
                cls._get_config_from_env(provider)
                availability[provider.value] = True
            except LLMConfigurationError:
                availability[provider.value] = False
        
        return availability
    
    @classmethod
    def get_default_provider(cls) -> LLMProvider:
        """
        Get the default provider based on available configuration.
        
        Returns:
            The first available provider, preferring OpenAI
            
        Raises:
            LLMConfigurationError: If no providers are configured
        """
        # Check providers in order of preference
        preferred_order = [LLMProvider.OPENAI, LLMProvider.OPENROUTER, LLMProvider.LITELM]
        
        for provider in preferred_order:
            try:
                cls._get_config_from_env(provider)
                return provider
            except LLMConfigurationError:
                continue
        
        raise LLMConfigurationError("No LLM providers are configured")
    
    @classmethod
    def create_default_client(cls) -> OpenAI:
        """
        Create a client using the default available provider.
        
        Returns:
            OpenAI client for the default provider
            
        Raises:
            LLMConfigurationError: If no providers are configured
        """
        default_provider = cls.get_default_provider()
        return cls.create_client(default_provider)
    
    @classmethod
    def validate_client(cls, client: OpenAI) -> bool:
        """
        Validate that a client is working by making a simple API call.
        
        Args:
            client: OpenAI client to validate
            
        Returns:
            True if client is working, False otherwise
        """
        try:
            # Make a simple API call to test connectivity
            response = client.models.list()
            return len(response.data) > 0
        except Exception:
            return False