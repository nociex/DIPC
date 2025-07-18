"""LLM client exceptions."""


class LLMClientError(Exception):
    """Base exception for LLM client errors."""
    pass


class LLMConfigurationError(LLMClientError):
    """Exception raised for LLM configuration errors."""
    pass


class LLMProviderError(LLMClientError):
    """Exception raised for LLM provider-specific errors."""
    
    def __init__(self, message: str, provider: str, status_code: int = None):
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code