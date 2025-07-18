"""Integration tests for document parsing pipeline."""

import os
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from src.document.parser import DocumentParsingService, ExtractionMode
from src.document.preprocessing import DocumentPreprocessor, ProcessedDocument, DocumentFormat
from src.llm.factory import LLMProvider
from src.tasks.parsing import parse_document_task


class TestDocumentParsingIntegration:
    """Integration tests for the complete document parsing pipeline."""
    
    @patch('src.document.parser.LLMClientFactory.create_client')
    @patch('src.document.preprocessing.requests.get')
    def test_parse_text_document_end_to_end(self, mock_requests_get, mock_create_client):
        """Test complete parsing pipeline for text document."""
        # Mock file download
        mock_response = Mock()
        mock_response.headers = {'content-type': 'text/plain'}
        mock_response.iter_content.return_value = [b'This is a test document with important information.\nIt contains names like John Doe and dates like 2024-01-15.']
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response
        
        # Mock LLM client
        mock_usage = Mock()
        mock_usage.prompt_tokens = 150
        mock_usage.completion_tokens = 75
        mock_usage.total_tokens = 225
        
        mock_choice = Mock()
        mock_choice.message.content = json.dumps({
            "document_type": "text_document",
            "title": "Test Document",
            "summary": "A test document containing names and dates",
            "key_information": {
                "names": ["John Doe"],
                "dates": ["2024-01-15"]
            },
            "metadata": {
                "confidence": 0.9,
                "language": "English"
            }
        })
        
        mock_response_obj = Mock()
        mock_response_obj.choices = [mock_choice]
        mock_response_obj.usage = mock_usage
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response_obj
        mock_client._model = "gpt-4-vision-preview"
        mock_create_client.return_value = mock_client
        
        # Test parsing service
        service = DocumentParsingService(LLMProvider.OPENAI, "gpt-4-vision-preview")
        result = service.parse_from_url(
            "https://example.com/test.txt",
            "task-123",
            ExtractionMode.STRUCTURED
        )
        
        # Verify results
        assert result.task_id == "task-123"
        assert result.error_message is None
        assert result.confidence_score == 0.9
        assert result.extracted_content["document_type"] == "text_document"
        assert "John Doe" in result.extracted_content["key_information"]["names"]
        assert "2024-01-15" in result.extracted_content["key_information"]["dates"]
        assert result.token_usage.total_tokens == 225
    
    @patch('src.document.parser.LLMClientFactory.create_client')
    @patch('src.document.preprocessing.requests.get')
    @patch('src.document.preprocessing.Image.open')
    @patch('src.document.preprocessing.pytesseract.image_to_string')
    def test_parse_image_document_with_ocr(self, mock_ocr, mock_image_open, mock_requests_get, mock_create_client):
        """Test parsing pipeline for image document with OCR."""
        # Mock file download
        mock_response = Mock()
        mock_response.headers = {'content-type': 'image/jpeg'}
        mock_response.iter_content.return_value = [b'fake image data']
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response
        
        # Mock image processing
        mock_img = Mock()
        mock_img.width = 800
        mock_img.height = 600
        mock_img.format = 'JPEG'
        mock_img.mode = 'RGB'
        mock_image_open.return_value.__enter__.return_value = mock_img
        
        # Mock OCR
        mock_ocr.return_value = "Invoice #12345\nDate: 2024-01-15\nAmount: $500.00"
        
        # Mock LLM client
        mock_usage = Mock()
        mock_usage.prompt_tokens = 200
        mock_usage.completion_tokens = 100
        mock_usage.total_tokens = 300
        
        mock_choice = Mock()
        mock_choice.message.content = json.dumps({
            "document_type": "invoice",
            "title": "Invoice #12345",
            "summary": "Invoice for $500.00 dated 2024-01-15",
            "key_information": {
                "amounts": ["$500.00"],
                "dates": ["2024-01-15"],
                "invoice_number": "12345"
            },
            "metadata": {
                "confidence": 0.85,
                "language": "English"
            }
        })
        
        mock_response_obj = Mock()
        mock_response_obj.choices = [mock_choice]
        mock_response_obj.usage = mock_usage
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response_obj
        mock_client._model = "gpt-4-vision-preview"
        mock_create_client.return_value = mock_client
        
        # Test parsing service
        service = DocumentParsingService(LLMProvider.OPENAI, "gpt-4-vision-preview")
        result = service.parse_from_url(
            "https://example.com/invoice.jpg",
            "task-456",
            ExtractionMode.STRUCTURED
        )
        
        # Verify results
        assert result.task_id == "task-456"
        assert result.error_message is None
        assert result.confidence_score == 0.85
        assert result.extracted_content["document_type"] == "invoice"
        assert "$500.00" in result.extracted_content["key_information"]["amounts"]
        assert result.token_usage.total_tokens == 300
    
    @patch('src.document.parser.LLMClientFactory.create_client')
    @patch('src.document.preprocessing.requests.get')
    @patch('src.document.preprocessing.PyPDF2.PdfReader')
    def test_parse_pdf_document(self, mock_pdf_reader, mock_requests_get, mock_create_client):
        """Test parsing pipeline for PDF document."""
        # Mock file download
        mock_response = Mock()
        mock_response.headers = {'content-type': 'application/pdf'}
        mock_response.iter_content.return_value = [b'fake pdf data']
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response
        
        # Mock PDF processing
        mock_page = Mock()
        mock_page.extract_text.return_value = "Contract Agreement\nParty A: ABC Corp\nParty B: XYZ Ltd\nDate: 2024-01-15"
        
        mock_reader_instance = Mock()
        mock_reader_instance.pages = [mock_page]
        mock_reader_instance.metadata = {
            '/Title': 'Contract Agreement',
            '/Author': 'Legal Department'
        }
        mock_pdf_reader.return_value = mock_reader_instance
        
        # Mock LLM client
        mock_usage = Mock()
        mock_usage.prompt_tokens = 180
        mock_usage.completion_tokens = 90
        mock_usage.total_tokens = 270
        
        mock_choice = Mock()
        mock_choice.message.content = json.dumps({
            "document_type": "contract",
            "title": "Contract Agreement",
            "summary": "Contract between ABC Corp and XYZ Ltd dated 2024-01-15",
            "key_information": {
                "names": ["ABC Corp", "XYZ Ltd"],
                "dates": ["2024-01-15"]
            },
            "sections": [
                {
                    "heading": "Parties",
                    "content": "ABC Corp and XYZ Ltd"
                }
            ],
            "metadata": {
                "confidence": 0.95,
                "language": "English"
            }
        })
        
        mock_response_obj = Mock()
        mock_response_obj.choices = [mock_choice]
        mock_response_obj.usage = mock_usage
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response_obj
        mock_client._model = "gpt-4-vision-preview"
        mock_create_client.return_value = mock_client
        
        # Test parsing service
        service = DocumentParsingService(LLMProvider.OPENAI, "gpt-4-vision-preview")
        result = service.parse_from_url(
            "https://example.com/contract.pdf",
            "task-789",
            ExtractionMode.STRUCTURED
        )
        
        # Verify results
        assert result.task_id == "task-789"
        assert result.error_message is None
        assert result.confidence_score == 0.95
        assert result.extracted_content["document_type"] == "contract"
        assert "ABC Corp" in result.extracted_content["key_information"]["names"]
        assert "XYZ Ltd" in result.extracted_content["key_information"]["names"]
    
    def test_different_extraction_modes(self):
        """Test different extraction modes produce different prompts."""
        with patch('src.document.parser.LLMClientFactory.create_client'):
            parser = DocumentParsingService(LLMProvider.OPENAI)
            
            # Test structured mode
            structured_prompt = parser.parser._build_system_prompt(ExtractionMode.STRUCTURED)
            assert "STRUCTURED" in structured_prompt
            assert "document_type" in structured_prompt
            
            # Test summary mode
            summary_prompt = parser.parser._build_system_prompt(ExtractionMode.SUMMARY)
            assert "SUMMARY" in summary_prompt
            assert "executive_summary" in summary_prompt
            
            # Test full text mode
            full_text_prompt = parser.parser._build_system_prompt(ExtractionMode.FULL_TEXT)
            assert "FULL_TEXT" in full_text_prompt
            assert "full_text" in full_text_prompt
            
            # Test custom mode
            custom_prompt = "Extract only phone numbers"
            custom_system_prompt = parser.parser._build_system_prompt(ExtractionMode.CUSTOM, custom_prompt)
            assert "CUSTOM" in custom_system_prompt
            assert custom_prompt in custom_system_prompt
    
    @patch('src.document.parser.LLMClientFactory.create_client')
    def test_error_handling_llm_failure(self, mock_create_client):
        """Test error handling when LLM API fails."""
        # Mock client that fails
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_client._model = "gpt-4-vision-preview"
        mock_create_client.return_value = mock_client
        
        # Create a simple processed document
        processed_doc = ProcessedDocument(
            format=DocumentFormat.TEXT,
            text_content="Test content",
            original_filename="test.txt",
            file_size=100
        )
        
        # Test parsing
        service = DocumentParsingService(LLMProvider.OPENAI)
        result = service.parser.parse_document(processed_doc, "task-error")
        
        # Verify error handling
        assert result.task_id == "task-error"
        assert result.error_message is not None
        assert "Document parsing failed" in result.error_message
        assert result.confidence_score == 0.0
        assert result.extracted_content == {}
    
    @patch('src.document.parser.LLMClientFactory.create_client')
    @patch('src.document.preprocessing.requests.get')
    def test_error_handling_download_failure(self, mock_requests_get, mock_create_client):
        """Test error handling when file download fails."""
        # Mock download failure
        mock_requests_get.side_effect = Exception("Network error")
        
        # Mock client (won't be used due to download failure)
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        
        # Test parsing service
        service = DocumentParsingService(LLMProvider.OPENAI)
        
        with pytest.raises(Exception, match="File download failed"):
            service.parse_from_url("https://example.com/test.txt", "task-fail")
    
    @patch('src.tasks.parsing.validate_processing_cost')
    @patch('src.tasks.parsing.store_parsing_results')
    @patch('src.tasks.parsing.calculate_actual_cost')
    @patch('src.document.parser.DocumentParsingService')
    def test_celery_task_full_pipeline_integration(self, mock_parsing_service_class, mock_calc_cost, mock_store_results, mock_validate_cost):
        """Test complete Celery task integration with full processing pipeline."""
        # Mock cost validation
        from src.utils.cost_estimation import CostEstimate
        cost_estimate = CostEstimate(
            estimated_input_tokens=100,
            estimated_output_tokens=50,
            total_estimated_tokens=150,
            estimated_cost_usd=0.15,
            max_possible_cost_usd=0.30,
            model_name="gpt-4-vision-preview",
            provider="openai",
            confidence=0.8
        )
        mock_validate_cost.return_value = (True, None, cost_estimate)
        
        # Mock actual cost calculation
        mock_calc_cost.return_value = 0.12
        
        # Mock result storage
        mock_store_results.return_value = None
        
        # Mock parsing service
        from src.document.parser import ParsingResult, TokenUsage
        parsing_result = ParsingResult(
            task_id="550e8400-e29b-41d4-a716-446655440000",
            extracted_content={
                "document_type": "invoice",
                "title": "Test Invoice",
                "key_information": {
                    "amounts": ["$100.00"],
                    "dates": ["2024-01-15"]
                }
            },
            confidence_score=0.9,
            processing_time=2.5,
            token_usage=TokenUsage(100, 50, 150, 0.15),
            metadata={
                "model": "gpt-4-vision-preview",
                "original_filename": "invoice.pdf",
                "processing_method": "llm_extraction"
            }
        )
        
        mock_service = Mock()
        mock_service.parse_from_url.return_value = parsing_result
        mock_parsing_service_class.return_value = mock_service
        
        # Test task data with comprehensive options
        task_data = {
            'task_id': '550e8400-e29b-41d4-a716-446655440000',
            'file_url': 'https://example.com/invoice.pdf',
            'user_id': 'user-123',
            'options': {
                'extraction_mode': 'structured',
                'llm_provider': 'openai',
                'model_name': 'gpt-4-vision-preview',
                'enable_vectorization': False,  # Disable to avoid vectorization mocking
                'storage_policy': 'permanent',
                'max_cost_limit': 1.00
            }
        }
        
        # Execute task
        result = parse_document_task(task_data)
        
        # Verify result structure
        assert result['status'] == 'completed'
        assert result['result']['extracted_content']['document_type'] == 'invoice'
        assert result['result']['confidence_score'] == 0.9
        assert result['result']['processing_time'] == 2.5
        assert result['result']['token_usage']['total_tokens'] == 150
        assert result['result']['token_usage']['estimated_cost'] == 0.12
        
        # Verify metadata
        metadata = result['result']['metadata']
        assert metadata['extraction_mode'] == 'structured'
        assert metadata['llm_provider'] == 'openai'
        assert metadata['model_name'] == 'gpt-4-vision-preview'
        assert metadata['storage_policy'] == 'permanent'
        assert metadata['vectorization_enabled'] == False
        assert 'processing_stages_completed' in metadata
        assert 'cost_validation' in metadata['processing_stages_completed']
        assert 'document_parsing' in metadata['processing_stages_completed']
        assert 'result_storage' in metadata['processing_stages_completed']
        
        # Verify function calls
        mock_validate_cost.assert_called_once()
        mock_parsing_service_class.assert_called_once()
        mock_calc_cost.assert_called_once()
        mock_store_results.assert_called_once()
    
    @patch('src.tasks.parsing.validate_processing_cost')
    @patch('src.tasks.parsing.store_parsing_results')
    @patch('src.tasks.parsing.calculate_actual_cost')
    @patch('src.document.parser.DocumentParsingService')
    @patch('src.tasks.vectorization.vectorize_content_task')
    def test_celery_task_with_vectorization(self, mock_vectorization_task, mock_parsing_service_class, mock_calc_cost, mock_store_results, mock_validate_cost):
        """Test Celery task with vectorization enabled."""
        # Mock cost validation
        from src.utils.cost_estimation import CostEstimate
        cost_estimate = CostEstimate(
            estimated_input_tokens=100,
            estimated_output_tokens=50,
            total_estimated_tokens=150,
            estimated_cost_usd=0.15,
            max_possible_cost_usd=0.30,
            model_name="gpt-4-vision-preview",
            provider="openai",
            confidence=0.8
        )
        mock_validate_cost.return_value = (True, None, cost_estimate)
        
        # Mock actual cost calculation
        mock_calc_cost.return_value = 0.12
        
        # Mock result storage
        mock_store_results.return_value = None
        
        # Mock vectorization task
        mock_vectorization_result = Mock()
        mock_vectorization_result.id = "vectorization-task-123"
        mock_vectorization_task.apply_async.return_value = mock_vectorization_result
        
        # Mock parsing service
        from src.document.parser import ParsingResult, TokenUsage
        parsing_result = ParsingResult(
            task_id="task-vector",
            extracted_content={
                "document_type": "report",
                "title": "Research Report",
                "summary": "Important research findings"
            },
            confidence_score=0.95,
            processing_time=3.2,
            token_usage=TokenUsage(120, 60, 180, 0.18),
            metadata={"model": "gpt-4-vision-preview"}
        )
        
        mock_service = Mock()
        mock_service.parse_from_url.return_value = parsing_result
        mock_parsing_service_class.return_value = mock_service
        
        # Test task data with vectorization enabled
        task_data = {
            'task_id': '550e8400-e29b-41d4-a716-446655440001',
            'file_url': 'https://example.com/report.pdf',
            'user_id': 'user-456',
            'options': {
                'extraction_mode': 'structured',
                'enable_vectorization': True,
                'storage_policy': 'temporary'
            }
        }
        
        # Execute task
        result = parse_document_task(task_data)
        
        # Verify result
        assert result['status'] == 'completed'
        assert result['result']['metadata']['vectorization_enabled'] == True
        assert result['result']['metadata']['vectorization_task_id'] == "vectorization-task-123"
        assert 'vectorization_trigger' in result['result']['metadata']['processing_stages_completed']
        
        # Verify vectorization task was called
        mock_vectorization_task.apply_async.assert_called_once()
        vectorization_args = mock_vectorization_task.apply_async.call_args[1]['args'][0]
        assert vectorization_args['task_id'] == 'task-vector'
        assert vectorization_args['user_id'] == 'user-456'
        assert 'content' in vectorization_args
    
    @patch('src.tasks.parsing.validate_processing_cost')
    def test_celery_task_cost_limit_exceeded(self, mock_validate_cost):
        """Test Celery task when cost limit is exceeded."""
        # Mock cost validation failure
        from src.utils.cost_estimation import CostEstimate
        cost_estimate = CostEstimate(
            estimated_input_tokens=5000,
            estimated_output_tokens=2000,
            total_estimated_tokens=7000,
            estimated_cost_usd=15.50,
            max_possible_cost_usd=20.00,
            model_name="gpt-4-vision-preview",
            provider="openai",
            confidence=0.9
        )
        mock_validate_cost.return_value = (False, "Estimated cost ($15.50) exceeds limit ($10.00)", cost_estimate)
        
        # Test task data
        task_data = {
            'task_id': '550e8400-e29b-41d4-a716-446655440002',
            'file_url': 'https://example.com/large-document.pdf',
            'user_id': 'user-123',
            'options': {
                'max_cost_limit': 10.00
            }
        }
        
        # Execute task
        result = parse_document_task(task_data)
        
        # Verify result
        assert result['status'] == 'failed'
        assert "Estimated cost" in result['error_message']
        assert "exceeds limit" in result['error_message']
        assert result['result']['error_code'] == 'COST_LIMIT_EXCEEDED'
        assert result['result']['processing_stage'] == 'cost_validation'
        assert result['result']['cost_estimate']['estimated_cost_usd'] == 15.50
    
    @patch('src.tasks.parsing.validate_processing_cost')
    @patch('src.document.parser.DocumentParsingService')
    def test_celery_task_parsing_service_failure(self, mock_parsing_service_class, mock_validate_cost):
        """Test Celery task when parsing service fails."""
        # Mock successful cost validation
        from src.utils.cost_estimation import CostEstimate
        cost_estimate = CostEstimate(
            estimated_input_tokens=100,
            estimated_output_tokens=50,
            total_estimated_tokens=150,
            estimated_cost_usd=0.15,
            max_possible_cost_usd=0.30,
            model_name="gpt-4-vision-preview",
            provider="openai",
            confidence=0.8
        )
        mock_validate_cost.return_value = (True, None, cost_estimate)
        
        # Mock parsing service initialization failure
        mock_parsing_service_class.side_effect = Exception("LLM service unavailable")
        
        # Test task data
        task_data = {
            'task_id': '550e8400-e29b-41d4-a716-446655440003',
            'file_url': 'https://example.com/document.pdf',
            'user_id': 'user-789',
            'options': {
                'llm_provider': 'openai'
            }
        }
        
        # Execute task
        result = parse_document_task(task_data)
        
        # Verify result
        assert result['status'] == 'failed'
        assert "Failed to initialize parsing service" in result['error_message']
        assert result['result']['error_code'] == 'INITIALIZATION_ERROR'
        assert result['result']['processing_stage'] == 'service_initialization'
    
    @patch('src.tasks.parsing.validate_processing_cost')
    @patch('src.tasks.parsing.store_parsing_results')
    @patch('src.document.parser.DocumentParsingService')
    def test_celery_task_storage_failure_graceful_handling(self, mock_parsing_service_class, mock_store_results, mock_validate_cost):
        """Test Celery task graceful handling of storage failures."""
        # Mock successful cost validation
        from src.utils.cost_estimation import CostEstimate
        cost_estimate = CostEstimate(
            estimated_input_tokens=100,
            estimated_output_tokens=50,
            total_estimated_tokens=150,
            estimated_cost_usd=0.15,
            max_possible_cost_usd=0.30,
            model_name="gpt-4-vision-preview",
            provider="openai",
            confidence=0.8
        )
        mock_validate_cost.return_value = (True, None, cost_estimate)
        
        # Mock storage failure
        mock_store_results.side_effect = Exception("Database connection failed")
        
        # Mock successful parsing
        from src.document.parser import ParsingResult, TokenUsage
        parsing_result = ParsingResult(
            task_id="task-storage-fail",
            extracted_content={"document_type": "test", "title": "Test Document"},
            confidence_score=0.8,
            processing_time=1.5,
            token_usage=TokenUsage(80, 40, 120, 0.12),
            metadata={"model": "gpt-4-vision-preview"}
        )
        
        mock_service = Mock()
        mock_service.parse_from_url.return_value = parsing_result
        mock_parsing_service_class.return_value = mock_service
        
        # Test task data
        task_data = {
            'task_id': '550e8400-e29b-41d4-a716-446655440004',
            'file_url': 'https://example.com/document.txt',
            'user_id': 'user-storage',
            'options': {
                'enable_vectorization': False
            }
        }
        
        # Execute task
        result = parse_document_task(task_data)
        
        # Verify task still completes with warning
        assert result['status'] == 'completed'
        assert result['result']['extracted_content']['document_type'] == 'test'
        assert 'storage_warning' in result['result']
        assert "Failed to store parsing results" in result['result']['storage_warning']
    
    @patch('src.tasks.parsing.validate_processing_cost')
    @patch('src.tasks.parsing.cleanup_temporary_resources')
    def test_celery_task_cleanup_on_failure(self, mock_cleanup, mock_validate_cost):
        """Test that cleanup is called even when task fails."""
        # Mock cost validation failure
        mock_validate_cost.return_value = (False, "Cost too high", None)
        
        # Test task data
        task_data = {
            'task_id': '550e8400-e29b-41d4-a716-446655440005',
            'file_url': 'https://example.com/document.pdf',
            'user_id': 'user-cleanup',
            'options': {}
        }
        
        # Execute task
        result = parse_document_task(task_data)
        
        # Verify cleanup was called
        mock_cleanup.assert_called_once()
        cleanup_args = mock_cleanup.call_args[0]
        assert cleanup_args[2] == '550e8400-e29b-41d4-a716-446655440005'  # task_id parameter
        
        # Verify task failed as expected
        assert result['status'] == 'failed'


class TestDocumentParsingErrorHandling:
    """Test error handling and recovery mechanisms in document parsing."""
    
    @patch('src.tasks.parsing.validate_processing_cost')
    @patch('src.tasks.parsing.store_parsing_results')
    @patch('src.tasks.parsing.calculate_actual_cost')
    @patch('src.document.parser.DocumentParsingService')
    def test_retry_mechanism_on_transient_failure(self, mock_parsing_service_class, mock_calc_cost, mock_store_results, mock_validate_cost):
        """Test retry mechanism when transient failures occur."""
        # Mock successful cost validation
        from src.utils.cost_estimation import CostEstimate
        cost_estimate = CostEstimate(
            estimated_input_tokens=100,
            estimated_output_tokens=50,
            total_estimated_tokens=150,
            estimated_cost_usd=0.15,
            max_possible_cost_usd=0.30,
            model_name="gpt-4-vision-preview",
            provider="openai",
            confidence=0.8
        )
        mock_validate_cost.return_value = (True, None, cost_estimate)
        
        # Mock cost calculation
        mock_calc_cost.return_value = 0.12
        
        # Mock storage success
        mock_store_results.return_value = None
        
        # Mock parsing service that fails first, then succeeds
        from src.document.parser import ParsingResult, TokenUsage
        success_result = ParsingResult(
            task_id="task-retry",
            extracted_content={"document_type": "test", "title": "Test Document"},
            confidence_score=0.8,
            processing_time=1.5,
            token_usage=TokenUsage(80, 40, 120, 0.12),
            metadata={"model": "gpt-4-vision-preview"}
        )
        
        mock_service = Mock()
        # First call fails with transient error, second succeeds
        mock_service.parse_from_url.side_effect = [
            Exception("Temporary network error"),
            success_result
        ]
        mock_parsing_service_class.return_value = mock_service
        
        # Test task data
        task_data = {
            'task_id': '550e8400-e29b-41d4-a716-446655440006',
            'file_url': 'https://example.com/document.txt',
            'user_id': 'user-retry',
            'options': {
                'enable_vectorization': False
            }
        }
        
        # Execute task - should fail on first attempt
        result = parse_document_task(task_data)
        
        # Verify first attempt failed
        assert result['status'] == 'failed'
        assert "Document parsing failed" in result['error_message']
        assert result['result']['error_code'] == 'PARSING_SERVICE_ERROR'
    
    @patch('src.tasks.parsing.validate_processing_cost')
    @patch('src.document.parser.DocumentParsingService')
    def test_graceful_degradation_on_llm_failure(self, mock_parsing_service_class, mock_validate_cost):
        """Test graceful degradation when LLM service fails."""
        # Mock successful cost validation
        from src.utils.cost_estimation import CostEstimate
        cost_estimate = CostEstimate(
            estimated_input_tokens=100,
            estimated_output_tokens=50,
            total_estimated_tokens=150,
            estimated_cost_usd=0.15,
            max_possible_cost_usd=0.30,
            model_name="gpt-4-vision-preview",
            provider="openai",
            confidence=0.8
        )
        mock_validate_cost.return_value = (True, None, cost_estimate)
        
        # Mock parsing service that returns error result (not exception)
        from src.document.parser import ParsingResult, TokenUsage
        error_result = ParsingResult(
            task_id="task-llm-fail",
            extracted_content={},
            confidence_score=0.0,
            processing_time=1.0,
            token_usage=TokenUsage(0, 0, 0, 0.0),
            metadata={"model": "gpt-4-vision-preview"},
            error_message="LLM API rate limit exceeded"
        )
        
        mock_service = Mock()
        mock_service.parse_from_url.return_value = error_result
        mock_parsing_service_class.return_value = mock_service
        
        # Test task data
        task_data = {
            'task_id': '550e8400-e29b-41d4-a716-446655440007',
            'file_url': 'https://example.com/document.txt',
            'user_id': 'user-llm-fail',
            'options': {}
        }
        
        # Execute task
        result = parse_document_task(task_data)
        
        # Verify graceful failure
        assert result['status'] == 'failed'
        assert result['error_message'] == "LLM API rate limit exceeded"
        assert result['result']['error_code'] == 'PARSING_ERROR'
        assert result['result']['processing_time'] == 1.0
    
    @patch('src.tasks.parsing.validate_processing_cost')
    @patch('src.tasks.parsing.store_parsing_results')
    @patch('src.tasks.parsing.calculate_actual_cost')
    @patch('src.document.parser.DocumentParsingService')
    def test_partial_success_with_warnings(self, mock_parsing_service_class, mock_calc_cost, mock_store_results, mock_validate_cost):
        """Test handling of partial success scenarios with warnings."""
        # Mock successful cost validation
        from src.utils.cost_estimation import CostEstimate
        cost_estimate = CostEstimate(
            estimated_input_tokens=100,
            estimated_output_tokens=50,
            total_estimated_tokens=150,
            estimated_cost_usd=0.15,
            max_possible_cost_usd=0.30,
            model_name="gpt-4-vision-preview",
            provider="openai",
            confidence=0.8
        )
        mock_validate_cost.return_value = (True, None, cost_estimate)
        
        # Mock cost calculation
        mock_calc_cost.return_value = 0.12
        
        # Mock storage failure (should not fail the task)
        mock_store_results.side_effect = Exception("Storage temporarily unavailable")
        
        # Mock parsing service with low confidence result
        from src.document.parser import ParsingResult, TokenUsage
        partial_result = ParsingResult(
            task_id="task-partial",
            extracted_content={
                "document_type": "unknown",
                "title": "Partially Extracted Document",
                "metadata": {
                    "confidence": 0.3,
                    "extraction_warnings": ["Low quality image", "Text partially obscured"]
                }
            },
            confidence_score=0.3,
            processing_time=2.8,
            token_usage=TokenUsage(150, 75, 225, 0.18),
            metadata={
                "model": "gpt-4-vision-preview",
                "extraction_warnings": ["Low confidence extraction"]
            }
        )
        
        mock_service = Mock()
        mock_service.parse_from_url.return_value = partial_result
        mock_parsing_service_class.return_value = mock_service
        
        # Test task data
        task_data = {
            'task_id': '550e8400-e29b-41d4-a716-446655440008',
            'file_url': 'https://example.com/poor-quality.jpg',
            'user_id': 'user-partial',
            'options': {
                'enable_vectorization': False
            }
        }
        
        # Execute task
        result = parse_document_task(task_data)
        
        # Verify partial success
        assert result['status'] == 'completed'
        assert result['result']['confidence_score'] == 0.3
        assert result['result']['extracted_content']['document_type'] == 'unknown'
        assert 'storage_warning' in result['result']
        assert "Storage temporarily unavailable" in result['result']['storage_warning']
        assert 'extraction_warnings' in result['result']['metadata']
    
    @patch('src.tasks.parsing.validate_processing_cost')
    @patch('src.document.parser.DocumentParsingService')
    def test_timeout_handling(self, mock_parsing_service_class, mock_validate_cost):
        """Test handling of processing timeouts."""
        # Mock successful cost validation
        from src.utils.cost_estimation import CostEstimate
        cost_estimate = CostEstimate(
            estimated_input_tokens=100,
            estimated_output_tokens=50,
            total_estimated_tokens=150,
            estimated_cost_usd=0.15,
            max_possible_cost_usd=0.30,
            model_name="gpt-4-vision-preview",
            provider="openai",
            confidence=0.8
        )
        mock_validate_cost.return_value = (True, None, cost_estimate)
        
        # Mock parsing service that times out
        mock_service = Mock()
        mock_service.parse_from_url.side_effect = TimeoutError("Processing timeout exceeded")
        mock_parsing_service_class.return_value = mock_service
        
        # Test task data
        task_data = {
            'task_id': '550e8400-e29b-41d4-a716-446655440009',
            'file_url': 'https://example.com/large-document.pdf',
            'user_id': 'user-timeout',
            'options': {}
        }
        
        # Execute task
        result = parse_document_task(task_data)
        
        # Verify timeout handling
        assert result['status'] == 'failed'
        assert "Processing timeout exceeded" in result['error_message']
        assert result['result']['error_code'] == 'PARSING_SERVICE_ERROR'
    
    @patch('src.tasks.parsing.validate_processing_cost')
    @patch('src.tasks.parsing.store_parsing_results')
    @patch('src.tasks.parsing.calculate_actual_cost')
    @patch('src.document.parser.DocumentParsingService')
    def test_memory_management_large_document(self, mock_parsing_service_class, mock_calc_cost, mock_store_results, mock_validate_cost):
        """Test memory management for large documents."""
        # Mock successful cost validation for large document
        from src.utils.cost_estimation import CostEstimate
        cost_estimate = CostEstimate(
            estimated_input_tokens=10000,
            estimated_output_tokens=2000,
            total_estimated_tokens=12000,
            estimated_cost_usd=5.50,
            max_possible_cost_usd=8.00,
            model_name="gpt-4-vision-preview",
            provider="openai",
            confidence=0.9
        )
        mock_validate_cost.return_value = (True, None, cost_estimate)
        
        # Mock cost calculation
        mock_calc_cost.return_value = 4.80
        
        # Mock storage success
        mock_store_results.return_value = None
        
        # Mock parsing service with large document result
        from src.document.parser import ParsingResult, TokenUsage
        large_doc_result = ParsingResult(
            task_id="task-large",
            extracted_content={
                "document_type": "research_paper",
                "title": "Large Research Document",
                "summary": "Comprehensive research paper with extensive content",
                "sections": [{"heading": f"Section {i}", "content": f"Content {i}"} for i in range(50)],
                "metadata": {
                    "confidence": 0.9,
                    "page_count": 150,
                    "word_count": 50000
                }
            },
            confidence_score=0.9,
            processing_time=45.2,
            token_usage=TokenUsage(10000, 2000, 12000, 4.80),
            metadata={
                "model": "gpt-4-vision-preview",
                "document_size": "large",
                "memory_usage": "high"
            }
        )
        
        mock_service = Mock()
        mock_service.parse_from_url.return_value = large_doc_result
        mock_parsing_service_class.return_value = mock_service
        
        # Test task data for large document
        task_data = {
            'task_id': '550e8400-e29b-41d4-a716-446655440010',
            'file_url': 'https://example.com/large-research-paper.pdf',
            'user_id': 'user-large',
            'options': {
                'extraction_mode': 'structured',
                'enable_vectorization': False,
                'max_cost_limit': 10.00
            }
        }
        
        # Execute task
        result = parse_document_task(task_data)
        
        # Verify successful processing of large document
        assert result['status'] == 'completed'
        assert result['result']['confidence_score'] == 0.9
        assert result['result']['processing_time'] == 45.2
        assert result['result']['token_usage']['total_tokens'] == 12000
        assert result['result']['token_usage']['estimated_cost'] == 4.80
        assert len(result['result']['extracted_content']['sections']) == 50


class TestDocumentFormatSupport:
    """Test support for different document formats."""
    
    def test_supported_formats_detection(self):
        """Test that all supported formats are properly detected."""
        preprocessor = DocumentPreprocessor()
        
        # Test format detection for various file types
        test_cases = [
            ("document.pdf", "application/pdf", DocumentFormat.PDF),
            ("image.jpg", "image/jpeg", DocumentFormat.IMAGE),
            ("image.png", "image/png", DocumentFormat.IMAGE),
            ("document.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", DocumentFormat.DOCX),
            ("spreadsheet.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", DocumentFormat.XLSX),
            ("text.txt", "text/plain", DocumentFormat.TEXT),
            ("readme.md", "text/markdown", DocumentFormat.TEXT),
            ("data.csv", "text/csv", DocumentFormat.TEXT),
            ("unknown.xyz", "application/octet-stream", DocumentFormat.UNKNOWN)
        ]
        
        for filename, content_type, expected_format in test_cases:
            detected_format = preprocessor.detect_format(filename, content_type)
            assert detected_format == expected_format, f"Failed for {filename} with {content_type}"
    
    @patch('src.document.parser.LLMClientFactory.create_client')
    def test_vision_model_image_handling(self, mock_create_client):
        """Test that vision models properly handle images."""
        mock_client = Mock()
        mock_client._model = "gpt-4-vision-preview"
        mock_create_client.return_value = mock_client
        
        parser = DocumentParsingService(LLMProvider.OPENAI, "gpt-4-vision-preview")
        
        # Create document with images
        processed_doc = ProcessedDocument(
            format=DocumentFormat.PDF,
            text_content="Document with images",
            image_paths=["/tmp/page1.png", "/tmp/page2.png"],
            original_filename="document.pdf"
        )
        
        with patch.object(parser.parser, '_encode_image', return_value="encoded_image"):
            content_parts = parser.parser._build_user_message(processed_doc)
            
            # Should have text + 2 images
            assert len(content_parts) == 3
            assert content_parts[0]["type"] == "text"
            assert content_parts[1]["type"] == "image_url"
            assert content_parts[2]["type"] == "image_url"


if __name__ == '__main__':
    pytest.main([__file__])