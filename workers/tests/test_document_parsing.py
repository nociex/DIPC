"""Tests for document parsing logic using LLM."""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

from src.document.parser import (
    DocumentParser,
    DocumentParsingService,
    ExtractionMode,
    ParsingResult,
    TokenUsage
)
from src.document.preprocessing import ProcessedDocument, DocumentFormat
from src.llm.factory import LLMProvider
from src.llm.exceptions import LLMProviderError


class TestDocumentParser:
    """Test cases for DocumentParser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('src.document.parser.LLMClientFactory.create_client'):
            self.parser = DocumentParser(
                llm_provider=LLMProvider.OPENAI,
                model_name="gpt-4-vision-preview"
            )
    
    def test_initialization_success(self):
        """Test successful parser initialization."""
        mock_client = Mock()
        mock_client._model = "gpt-4-vision-preview"
        
        with patch('src.document.parser.LLMClientFactory.create_client', return_value=mock_client):
            parser = DocumentParser(LLMProvider.OPENAI)
            
            assert parser.llm_provider == LLMProvider.OPENAI
            assert parser.model_name == "gpt-4-vision-preview"
            assert parser.client == mock_client
    
    def test_initialization_failure(self):
        """Test parser initialization failure."""
        with patch('src.document.parser.LLMClientFactory.create_client', side_effect=Exception("Config error")):
            with pytest.raises(LLMProviderError, match="LLM client initialization failed"):
                DocumentParser(LLMProvider.OPENAI)
    
    @patch('src.document.parser.Image.open')
    @patch('src.document.parser.base64.b64encode')
    def test_encode_image_success(self, mock_b64encode, mock_image_open):
        """Test successful image encoding."""
        # Mock PIL Image
        mock_img = Mock()
        mock_img.size = (800, 600)
        mock_img.mode = 'RGB'
        mock_img.thumbnail = Mock()
        mock_img.convert.return_value = mock_img
        mock_img.save = Mock()
        
        mock_image_open.return_value.__enter__.return_value = mock_img
        mock_b64encode.return_value = b'encoded_image_data'
        
        result = self.parser._encode_image("/path/to/image.jpg")
        
        assert result == 'encoded_image_data'
        mock_img.thumbnail.assert_called_once()
        mock_b64encode.assert_called_once()
    
    @patch('src.document.parser.Image.open')
    def test_encode_image_failure(self, mock_image_open):
        """Test image encoding failure."""
        mock_image_open.side_effect = Exception("Image error")
        
        with pytest.raises(Exception, match="Image encoding failed"):
            self.parser._encode_image("/path/to/image.jpg")
    
    def test_build_system_prompt_structured(self):
        """Test system prompt building for structured extraction."""
        prompt = self.parser._build_system_prompt(ExtractionMode.STRUCTURED)
        
        assert "EXTRACTION MODE: STRUCTURED" in prompt
        assert "document_type" in prompt
        assert "key_information" in prompt
        assert "JSON format" in prompt
    
    def test_build_system_prompt_summary(self):
        """Test system prompt building for summary extraction."""
        prompt = self.parser._build_system_prompt(ExtractionMode.SUMMARY)
        
        assert "EXTRACTION MODE: SUMMARY" in prompt
        assert "executive_summary" in prompt
        assert "main_points" in prompt
    
    def test_build_system_prompt_full_text(self):
        """Test system prompt building for full text extraction."""
        prompt = self.parser._build_system_prompt(ExtractionMode.FULL_TEXT)
        
        assert "EXTRACTION MODE: FULL_TEXT" in prompt
        assert "full_text" in prompt
        assert "text_structure" in prompt
    
    def test_build_system_prompt_custom(self):
        """Test system prompt building for custom extraction."""
        custom_prompt = "Extract only the names and dates from this document."
        prompt = self.parser._build_system_prompt(ExtractionMode.CUSTOM, custom_prompt)
        
        assert "EXTRACTION MODE: CUSTOM" in prompt
        assert custom_prompt in prompt
        assert "JSON format" in prompt
    
    def test_build_user_message_text_only(self):
        """Test user message building for text-only document."""
        processed_doc = ProcessedDocument(
            format=DocumentFormat.TEXT,
            text_content="This is test content",
            metadata={"line_count": 1},
            original_filename="test.txt"
        )
        
        content_parts = self.parser._build_user_message(processed_doc)
        
        assert len(content_parts) == 1
        assert content_parts[0]["type"] == "text"
        assert "This is test content" in content_parts[0]["text"]
        assert "line_count" in content_parts[0]["text"]
    
    @patch.object(DocumentParser, '_encode_image')
    def test_build_user_message_with_images(self, mock_encode_image):
        """Test user message building for document with images."""
        mock_encode_image.return_value = "encoded_image_data"
        
        processed_doc = ProcessedDocument(
            format=DocumentFormat.PDF,
            text_content="PDF content",
            image_paths=["/path/to/image1.png", "/path/to/image2.png"],
            metadata={"page_count": 2},
            original_filename="test.pdf"
        )
        
        content_parts = self.parser._build_user_message(processed_doc)
        
        # Should have text content + 2 images
        assert len(content_parts) == 3
        assert content_parts[0]["type"] == "text"
        assert content_parts[1]["type"] == "image_url"
        assert content_parts[2]["type"] == "image_url"
        
        # Check image encoding
        assert mock_encode_image.call_count == 2
    
    def test_build_user_message_no_content(self):
        """Test user message building for document with no content."""
        processed_doc = ProcessedDocument(
            format=DocumentFormat.UNKNOWN,
            text_content="",
            original_filename="unknown.file"
        )
        
        content_parts = self.parser._build_user_message(processed_doc)
        
        assert len(content_parts) == 1
        assert content_parts[0]["type"] == "text"
        assert "No extractable content found" in content_parts[0]["text"]
    
    def test_call_llm_api_success(self):
        """Test successful LLM API call."""
        # Mock response
        mock_usage = Mock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 50
        mock_usage.total_tokens = 150
        
        mock_choice = Mock()
        mock_choice.message.content = '{"extracted": "data", "confidence": 0.9}'
        
        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        
        # Mock client
        self.parser.client = Mock()
        self.parser.client.chat.completions.create.return_value = mock_response
        
        system_prompt = "Test system prompt"
        user_content = [{"type": "text", "text": "Test content"}]
        
        result, token_usage = self.parser._call_llm_api(system_prompt, user_content)
        
        assert result == {"extracted": "data", "confidence": 0.9}
        assert token_usage.prompt_tokens == 100
        assert token_usage.completion_tokens == 50
        assert token_usage.total_tokens == 150
    
    def test_call_llm_api_invalid_json(self):
        """Test LLM API call with invalid JSON response."""
        # Mock response with invalid JSON
        mock_usage = Mock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 50
        mock_usage.total_tokens = 150
        
        mock_choice = Mock()
        mock_choice.message.content = 'Invalid JSON response'
        
        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        
        # Mock client
        self.parser.client = Mock()
        self.parser.client.chat.completions.create.return_value = mock_response
        
        system_prompt = "Test system prompt"
        user_content = [{"type": "text", "text": "Test content"}]
        
        result, token_usage = self.parser._call_llm_api(system_prompt, user_content)
        
        assert "raw_response" in result
        assert "parse_error" in result
        assert result["raw_response"] == 'Invalid JSON response'
    
    def test_call_llm_api_failure(self):
        """Test LLM API call failure."""
        # Mock client failure
        self.parser.client = Mock()
        self.parser.client.chat.completions.create.side_effect = Exception("API Error")
        
        system_prompt = "Test system prompt"
        user_content = [{"type": "text", "text": "Test content"}]
        
        with pytest.raises(LLMProviderError, match="LLM API call failed"):
            self.parser._call_llm_api(system_prompt, user_content)
    
    def test_validate_and_post_process(self):
        """Test content validation and post-processing."""
        extracted_content = {
            "document_type": "invoice",
            "title": "Test Invoice",
            "metadata": {"confidence": 0.85}
        }
        
        processed_doc = ProcessedDocument(
            format=DocumentFormat.PDF,
            text_content="Invoice content",
            original_filename="invoice.pdf",
            file_size=1024
        )
        
        validated_content, confidence = self.parser._validate_and_post_process(
            extracted_content, processed_doc
        )
        
        assert confidence == 0.85
        assert validated_content["document_format"] == "pdf"
        assert validated_content["original_filename"] == "invoice.pdf"
        assert "processing_method" in validated_content["metadata"]
        assert validated_content["metadata"]["model_used"] == self.parser.model_name
    
    @patch.object(DocumentParser, '_build_system_prompt')
    @patch.object(DocumentParser, '_build_user_message')
    @patch.object(DocumentParser, '_call_llm_api')
    @patch.object(DocumentParser, '_validate_and_post_process')
    def test_parse_document_success(self, mock_validate, mock_api_call, mock_user_msg, mock_system_prompt):
        """Test successful document parsing."""
        # Setup mocks
        mock_system_prompt.return_value = "System prompt"
        mock_user_msg.return_value = [{"type": "text", "text": "Content"}]
        
        mock_token_usage = TokenUsage(100, 50, 150, 0.15)
        mock_api_call.return_value = ({"extracted": "data"}, mock_token_usage)
        
        mock_validate.return_value = ({"validated": "data"}, 0.9)
        
        processed_doc = ProcessedDocument(
            format=DocumentFormat.TEXT,
            text_content="Test content",
            original_filename="test.txt"
        )
        
        result = self.parser.parse_document(processed_doc, "task-123")
        
        assert isinstance(result, ParsingResult)
        assert result.task_id == "task-123"
        assert result.extracted_content == {"validated": "data"}
        assert result.confidence_score == 0.9
        assert result.token_usage == mock_token_usage
        assert result.error_message is None
    
    @patch.object(DocumentParser, '_build_system_prompt')
    @patch.object(DocumentParser, '_build_user_message')
    @patch.object(DocumentParser, '_call_llm_api')
    def test_parse_document_failure(self, mock_api_call, mock_user_msg, mock_system_prompt):
        """Test document parsing failure."""
        # Setup mocks
        mock_system_prompt.return_value = "System prompt"
        mock_user_msg.return_value = [{"type": "text", "text": "Content"}]
        mock_api_call.side_effect = Exception("Parsing failed")
        
        processed_doc = ProcessedDocument(
            format=DocumentFormat.TEXT,
            text_content="Test content",
            original_filename="test.txt"
        )
        
        result = self.parser.parse_document(processed_doc, "task-123")
        
        assert isinstance(result, ParsingResult)
        assert result.task_id == "task-123"
        assert result.extracted_content == {}
        assert result.confidence_score == 0.0
        assert "Document parsing failed" in result.error_message


class TestDocumentParsingService:
    """Test cases for DocumentParsingService."""
    
    @patch('src.document.parser.LLMClientFactory.get_default_provider')
    @patch('src.document.parser.DocumentParser')
    def test_initialization_auto_detect_provider(self, mock_parser_class, mock_get_default):
        """Test service initialization with auto-detected provider."""
        mock_get_default.return_value = LLMProvider.OPENAI
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        
        service = DocumentParsingService()
        
        mock_get_default.assert_called_once()
        mock_parser_class.assert_called_once_with(LLMProvider.OPENAI, None)
        assert service.parser == mock_parser
    
    @patch('src.document.parser.LLMClientFactory.get_default_provider')
    def test_initialization_no_provider_available(self, mock_get_default):
        """Test service initialization when no provider is available."""
        mock_get_default.side_effect = Exception("No provider configured")
        
        with pytest.raises(LLMProviderError, match="No LLM provider available"):
            DocumentParsingService()
    
    @patch('src.document.parser.DocumentPreprocessor')
    @patch.object(DocumentParsingService, '__init__', return_value=None)
    def test_parse_from_url_success(self, mock_init, mock_preprocessor_class):
        """Test successful parsing from URL."""
        # Setup service
        service = DocumentParsingService.__new__(DocumentParsingService)
        mock_parser = Mock()
        service.parser = mock_parser
        
        # Setup preprocessor
        mock_preprocessor = Mock()
        mock_preprocessor_class.return_value = mock_preprocessor
        
        processed_doc = ProcessedDocument(
            format=DocumentFormat.TEXT,
            text_content="Test content",
            image_paths=["/tmp/image.png"]
        )
        mock_preprocessor.process_document.return_value = processed_doc
        
        # Setup parser result
        expected_result = ParsingResult(
            task_id="task-123",
            extracted_content={"data": "extracted"},
            confidence_score=0.9,
            processing_time=1.5,
            token_usage=TokenUsage(100, 50, 150),
            metadata={}
        )
        mock_parser.parse_document.return_value = expected_result
        
        # Test parsing
        result = service.parse_from_url(
            "https://example.com/test.txt",
            "task-123",
            ExtractionMode.STRUCTURED
        )
        
        assert result == expected_result
        mock_preprocessor.process_document.assert_called_once_with("https://example.com/test.txt")
        mock_parser.parse_document.assert_called_once_with(
            processed_doc, "task-123", ExtractionMode.STRUCTURED, None
        )
        mock_preprocessor.cleanup_temp_files.assert_called_once_with(["/tmp/image.png"])
    
    @patch('src.document.parser.DocumentPreprocessor')
    @patch.object(DocumentParsingService, '__init__', return_value=None)
    def test_parse_from_url_with_cleanup_on_error(self, mock_init, mock_preprocessor_class):
        """Test parsing from URL with cleanup on error."""
        # Setup service
        service = DocumentParsingService.__new__(DocumentParsingService)
        mock_parser = Mock()
        service.parser = mock_parser
        
        # Setup preprocessor
        mock_preprocessor = Mock()
        mock_preprocessor_class.return_value = mock_preprocessor
        
        processed_doc = ProcessedDocument(
            format=DocumentFormat.TEXT,
            text_content="Test content",
            image_paths=["/tmp/image1.png", "/tmp/image2.png"]
        )
        mock_preprocessor.process_document.return_value = processed_doc
        
        # Setup parser to fail
        mock_parser.parse_document.side_effect = Exception("Parsing error")
        
        # Test parsing
        with pytest.raises(Exception, match="Parsing error"):
            service.parse_from_url("https://example.com/test.txt", "task-123")
        
        # Verify cleanup was called
        mock_preprocessor.cleanup_temp_files.assert_called_once_with(["/tmp/image1.png", "/tmp/image2.png"])


class TestParsingResult:
    """Test cases for ParsingResult."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        token_usage = TokenUsage(100, 50, 150, 0.15)
        
        result = ParsingResult(
            task_id="task-123",
            extracted_content={"data": "test"},
            confidence_score=0.9,
            processing_time=2.5,
            token_usage=token_usage,
            metadata={"model": "gpt-4"},
            error_message=None
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["task_id"] == "task-123"
        assert result_dict["extracted_content"] == {"data": "test"}
        assert result_dict["confidence_score"] == 0.9
        assert result_dict["processing_time"] == 2.5
        assert result_dict["token_usage"]["prompt_tokens"] == 100
        assert result_dict["token_usage"]["completion_tokens"] == 50
        assert result_dict["token_usage"]["total_tokens"] == 150
        assert result_dict["token_usage"]["estimated_cost"] == 0.15
        assert result_dict["metadata"] == {"model": "gpt-4"}
        assert result_dict["error_message"] is None


if __name__ == '__main__':
    pytest.main([__file__])