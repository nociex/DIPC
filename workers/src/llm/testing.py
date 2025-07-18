"""Testing utilities for LLM clients."""

from typing import Dict, Any, Optional, List
from unittest.mock import Mock, MagicMock
from openai import OpenAI
from openai.types import Model
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from .factory import LLMProvider


class MockLLMResponse:
    """Mock response for LLM API calls."""
    
    def __init__(
        self,
        content: str = "Mock response",
        model: str = "gpt-4-vision-preview",
        usage_tokens: int = 100,
        finish_reason: str = "stop"
    ):
        self.content = content
        self.model = model
        self.usage_tokens = usage_tokens
        self.finish_reason = finish_reason
    
    def to_chat_completion(self) -> ChatCompletion:
        """Convert to OpenAI ChatCompletion format."""
        return ChatCompletion(
            id="chatcmpl-mock123",
            choices=[
                Choice(
                    finish_reason=self.finish_reason,
                    index=0,
                    message=ChatCompletionMessage(
                        content=self.content,
                        role="assistant"
                    )
                )
            ],
            created=1234567890,
            model=self.model,
            object="chat.completion",
            usage={
                "completion_tokens": self.usage_tokens // 2,
                "prompt_tokens": self.usage_tokens // 2,
                "total_tokens": self.usage_tokens
            }
        )


class MockLLMClient:
    """Mock LLM client for testing."""
    
    def __init__(self, provider: LLMProvider = LLMProvider.OPENAI):
        self.provider = provider.value
        self._model = "gpt-4-vision-preview"
        self.chat = Mock()
        self.models = Mock()
        
        # Set up default mock responses
        self.set_chat_response()
        self.set_models_response()
    
    def set_chat_response(self, response: Optional[MockLLMResponse] = None):
        """Set the mock response for chat completions."""
        if response is None:
            response = MockLLMResponse()
        
        self.chat.completions = Mock()
        self.chat.completions.create = Mock(return_value=response.to_chat_completion())
    
    def set_models_response(self, models: Optional[List[str]] = None):
        """Set the mock response for models list."""
        if models is None:
            models = ["gpt-4-vision-preview", "gpt-3.5-turbo"]
        
        mock_models = [
            Model(id=model, created=1234567890, object="model", owned_by="openai")
            for model in models
        ]
        
        mock_response = Mock()
        mock_response.data = mock_models
        self.models.list = Mock(return_value=mock_response)
    
    def set_error_response(self, error_type: Exception = Exception, message: str = "Mock error"):
        """Set the client to raise an error on API calls."""
        error = error_type(message)
        self.chat.completions.create = Mock(side_effect=error)
        self.models.list = Mock(side_effect=error)


class LLMTestUtils:
    """Utilities for testing LLM functionality."""
    
    @staticmethod
    def create_mock_client(provider: LLMProvider = LLMProvider.OPENAI) -> MockLLMClient:
        """Create a mock LLM client."""
        return MockLLMClient(provider)
    
    @staticmethod
    def create_mock_response(
        content: str = "Test response",
        tokens: int = 50
    ) -> MockLLMResponse:
        """Create a mock LLM response."""
        return MockLLMResponse(content=content, usage_tokens=tokens)
    
    @staticmethod
    def patch_environment_variables(monkeypatch, provider_configs: Dict[str, Dict[str, str]]):
        """
        Patch environment variables for testing different provider configurations.
        
        Args:
            monkeypatch: pytest monkeypatch fixture
            provider_configs: Dict mapping provider names to their config values
        """
        env_mappings = {
            "openai": {
                "api_key": "OPENAI_API_KEY",
                "base_url": "OPENAI_BASE_URL",
                "model": "OPENAI_MODEL"
            },
            "openrouter": {
                "api_key": "OPENROUTER_API_KEY",
                "base_url": "OPENROUTER_BASE_URL", 
                "model": "OPENROUTER_MODEL"
            },
            "litelm": {
                "api_key": "LITELM_API_KEY",
                "base_url": "LITELM_BASE_URL",
                "model": "LITELM_MODEL"
            }
        }
        
        # Clear all LLM-related environment variables first
        for provider_env_vars in env_mappings.values():
            for env_var in provider_env_vars.values():
                monkeypatch.delenv(env_var, raising=False)
        
        # Set the requested configurations
        for provider, config in provider_configs.items():
            if provider in env_mappings:
                env_vars = env_mappings[provider]
                for config_key, config_value in config.items():
                    if config_key in env_vars:
                        monkeypatch.setenv(env_vars[config_key], config_value)
    
    @staticmethod
    def get_test_provider_config() -> Dict[str, Dict[str, str]]:
        """Get a complete test configuration for all providers."""
        return {
            "openai": {
                "api_key": "test-openai-key",
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4-vision-preview"
            },
            "openrouter": {
                "api_key": "test-openrouter-key",
                "base_url": "https://openrouter.ai/api/v1",
                "model": "openai/gpt-4-vision-preview"
            },
            "litelm": {
                "api_key": "test-litelm-key",
                "base_url": "https://api.litelm.com/v1",
                "model": "gpt-4-vision-preview"
            }
        }
    
    @staticmethod
    def assert_client_configured(client: OpenAI, expected_provider: str, expected_base_url: str):
        """Assert that a client is configured correctly."""
        assert hasattr(client, '_provider'), "Client should have provider information"
        assert client._provider == expected_provider, f"Expected provider {expected_provider}, got {client._provider}"
        # OpenAI client automatically adds trailing slash, so normalize both URLs for comparison
        expected_normalized = expected_base_url.rstrip('/') + '/'
        actual_normalized = str(client.base_url).rstrip('/') + '/'
        assert actual_normalized == expected_normalized, f"Expected base_url {expected_normalized}, got {actual_normalized}"