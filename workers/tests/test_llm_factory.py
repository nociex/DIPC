"""Tests for LLM client factory."""

import pytest
from unittest.mock import patch, Mock
from openai import OpenAI

from src.llm.factory import LLMClientFactory, LLMProvider, LLMProviderConfig
from src.llm.exceptions import LLMConfigurationError
from src.llm.testing import LLMTestUtils


class TestLLMProviderConfig:
    """Test LLM provider configuration validation."""
    
    def test_valid_config(self):
        """Test creating a valid provider configuration."""
        config = LLMProviderConfig(
            base_url="https://api.openai.com/v1",
            api_key="test-key",
            model="gpt-4"
        )
        
        assert config.base_url == "https://api.openai.com/v1"
        assert config.api_key == "test-key"
        assert config.model == "gpt-4"
        assert config.timeout == 60  # default
        assert config.max_retries == 3  # default
    
    def test_invalid_api_key(self):
        """Test validation of empty API key."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            LLMProviderConfig(
                base_url="https://api.openai.com/v1",
                api_key="",
                model="gpt-4"
            )
    
    def test_invalid_base_url(self):
        """Test validation of invalid base URL."""
        with pytest.raises(ValueError, match="Base URL must be a valid HTTP/HTTPS URL"):
            LLMProviderConfig(
                base_url="invalid-url",
                api_key="test-key",
                model="gpt-4"
            )
    
    def test_base_url_trailing_slash_removal(self):
        """Test that trailing slashes are removed from base URL."""
        config = LLMProviderConfig(
            base_url="https://api.openai.com/v1/",
            api_key="test-key"
        )
        
        assert config.base_url == "https://api.openai.com/v1"


class TestLLMClientFactory:
    """Test LLM client factory functionality."""
    
    def test_create_client_with_config(self):
        """Test creating a client with explicit configuration."""
        config = LLMProviderConfig(
            base_url="https://api.openai.com/v1",
            api_key="test-key",
            model="gpt-4"
        )
        
        client = LLMClientFactory.create_client(LLMProvider.OPENAI, config)
        
        assert isinstance(client, OpenAI)
        LLMTestUtils.assert_client_configured(client, "openai", "https://api.openai.com/v1")
        assert client._model == "gpt-4"
    
    def test_create_client_from_environment(self, monkeypatch):
        """Test creating a client from environment variables."""
        # Set up environment
        LLMTestUtils.patch_environment_variables(monkeypatch, {
            "openai": {
                "api_key": "test-openai-key",
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4"
            }
        })
        
        client = LLMClientFactory.create_client(LLMProvider.OPENAI)
        
        assert isinstance(client, OpenAI)
        LLMTestUtils.assert_client_configured(
            client, "openai", "https://api.openai.com/v1"
        )
    
    def test_create_openrouter_client(self, monkeypatch):
        """Test creating an OpenRouter client."""
        LLMTestUtils.patch_environment_variables(monkeypatch, {
            "openrouter": {
                "api_key": "test-openrouter-key",
                "base_url": "https://openrouter.ai/api/v1",
                "model": "openai/gpt-4-vision-preview"
            }
        })
        
        client = LLMClientFactory.create_client(LLMProvider.OPENROUTER)
        
        assert isinstance(client, OpenAI)
        LLMTestUtils.assert_client_configured(
            client, "openrouter", "https://openrouter.ai/api/v1"
        )
    
    def test_create_litelm_client(self, monkeypatch):
        """Test creating a LiteLM client."""
        LLMTestUtils.patch_environment_variables(monkeypatch, {
            "litelm": {
                "api_key": "test-litelm-key",
                "base_url": "https://api.litelm.com/v1",
                "model": "gpt-4"
            }
        })
        
        client = LLMClientFactory.create_client(LLMProvider.LITELM)
        
        assert isinstance(client, OpenAI)
        LLMTestUtils.assert_client_configured(
            client, "litelm", "https://api.litelm.com/v1"
        )
    
    def test_missing_api_key_error(self, monkeypatch):
        """Test error when API key is missing."""
        # Clear all environment variables
        LLMTestUtils.patch_environment_variables(monkeypatch, {})
        
        with pytest.raises(LLMConfigurationError, match="Missing required environment variable: OPENAI_API_KEY"):
            LLMClientFactory.create_client(LLMProvider.OPENAI)
    
    def test_missing_base_url_for_litelm(self, monkeypatch):
        """Test error when base URL is missing for LiteLM."""
        LLMTestUtils.patch_environment_variables(monkeypatch, {
            "litelm": {
                "api_key": "test-key"
                # base_url is missing
            }
        })
        
        with pytest.raises(LLMConfigurationError, match="Missing required environment variable: LITELM_BASE_URL"):
            LLMClientFactory.create_client(LLMProvider.LITELM)
    
    def test_get_available_providers(self, monkeypatch):
        """Test checking available providers."""
        # Configure only OpenAI
        LLMTestUtils.patch_environment_variables(monkeypatch, {
            "openai": {
                "api_key": "test-key"
            }
        })
        
        availability = LLMClientFactory.get_available_providers()
        
        assert availability["openai"] is True
        assert availability["openrouter"] is False
        assert availability["litelm"] is False
    
    def test_get_default_provider(self, monkeypatch):
        """Test getting the default provider."""
        # Configure OpenRouter only (OpenAI should be preferred)
        LLMTestUtils.patch_environment_variables(monkeypatch, {
            "openrouter": {
                "api_key": "test-key"
            }
        })
        
        default_provider = LLMClientFactory.get_default_provider()
        assert default_provider == LLMProvider.OPENROUTER
    
    def test_get_default_provider_prefers_openai(self, monkeypatch):
        """Test that OpenAI is preferred when multiple providers are available."""
        LLMTestUtils.patch_environment_variables(monkeypatch, {
            "openai": {"api_key": "test-key"},
            "openrouter": {"api_key": "test-key"}
        })
        
        default_provider = LLMClientFactory.get_default_provider()
        assert default_provider == LLMProvider.OPENAI
    
    def test_no_providers_configured_error(self, monkeypatch):
        """Test error when no providers are configured."""
        LLMTestUtils.patch_environment_variables(monkeypatch, {})
        
        with pytest.raises(LLMConfigurationError, match="No LLM providers are configured"):
            LLMClientFactory.get_default_provider()
    
    def test_create_default_client(self, monkeypatch):
        """Test creating a client with the default provider."""
        LLMTestUtils.patch_environment_variables(monkeypatch, {
            "openai": {
                "api_key": "test-key"
            }
        })
        
        client = LLMClientFactory.create_default_client()
        
        assert isinstance(client, OpenAI)
        assert client._provider == "openai"
    
    @patch('src.llm.factory.OpenAI')
    def test_validate_client_success(self, mock_openai_class):
        """Test successful client validation."""
        # Create a mock client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(), Mock()]  # Non-empty list
        mock_client.models.list.return_value = mock_response
        
        result = LLMClientFactory.validate_client(mock_client)
        
        assert result is True
        mock_client.models.list.assert_called_once()
    
    @patch('src.llm.factory.OpenAI')
    def test_validate_client_failure(self, mock_openai_class):
        """Test client validation failure."""
        # Create a mock client that raises an exception
        mock_client = Mock()
        mock_client.models.list.side_effect = Exception("API Error")
        
        result = LLMClientFactory.validate_client(mock_client)
        
        assert result is False
    
    def test_default_configurations(self):
        """Test that default configurations are properly defined."""
        configs = LLMClientFactory.DEFAULT_CONFIGS
        
        # Check that all providers have configurations
        assert LLMProvider.OPENAI in configs
        assert LLMProvider.OPENROUTER in configs
        assert LLMProvider.LITELM in configs
        
        # Check OpenAI config
        openai_config = configs[LLMProvider.OPENAI]
        assert openai_config["base_url"] == "https://api.openai.com/v1"
        assert openai_config["model"] == "gpt-4-vision-preview"
        
        # Check OpenRouter config
        openrouter_config = configs[LLMProvider.OPENROUTER]
        assert openrouter_config["base_url"] == "https://openrouter.ai/api/v1"
        assert openrouter_config["model"] == "openai/gpt-4-vision-preview"
        
        # Check LiteLM config (should require environment variables)
        litelm_config = configs[LLMProvider.LITELM]
        assert litelm_config["base_url"] is None
        assert litelm_config["model"] is None