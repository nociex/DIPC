"""Integration tests for cost estimation in document parsing tasks."""

import pytest
from unittest.mock import patch, MagicMock
import json

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tasks.parsing import parse_document_task, validate_processing_cost
from utils.cost_estimation import CostEstimate


class TestCostEstimationIntegration:
    """Test cost estimation integration with document parsing tasks."""
    
    def test_validate_processing_cost_success(self):
        """Test successful cost validation."""
        task_data = {
            'task_id': 'test-task-123',
            'file_url': 'https://example.com/test.pdf',
            'user_id': 'test-user',
            'options': {
                'model_name': 'gpt-4-vision-preview',
                'llm_provider': 'openai',
                'max_cost_limit': 1.0
            }
        }
        
        # Mock the file download
        with patch('tasks.parsing.download_file_for_analysis') as mock_download:
            mock_download.return_value = ('test.pdf', 5000, 'application/pdf')
            
            is_valid, error_message, cost_estimate = validate_processing_cost(task_data)
            
            assert is_valid is True
            assert error_message is None
            assert isinstance(cost_estimate, CostEstimate)
            assert cost_estimate.estimated_cost_usd > 0
            assert cost_estimate.model_name == 'gpt-4-vision-preview'
    
    def test_validate_processing_cost_exceeds_limit(self):
        """Test cost validation when limit is exceeded."""
        task_data = {
            'task_id': 'test-task-123',
            'file_url': 'https://example.com/large_document.pdf',
            'user_id': 'test-user',
            'options': {
                'model_name': 'gpt-4',
                'llm_provider': 'openai',
                'max_cost_limit': 0.01  # Very low limit
            }
        }
        
        # Mock the file download to return a large file
        with patch('tasks.parsing.download_file_for_analysis') as mock_download:
            mock_download.return_value = ('large_document.pdf', 1000000, 'application/pdf')  # 1MB
            
            is_valid, error_message, cost_estimate = validate_processing_cost(task_data)
            
            assert is_valid is False
            assert error_message is not None
            assert "exceeds limit" in error_message
            assert isinstance(cost_estimate, CostEstimate)
    
    def test_validate_processing_cost_no_limit(self):
        """Test cost validation with no limit set."""
        task_data = {
            'task_id': 'test-task-123',
            'file_url': 'https://example.com/test.pdf',
            'user_id': 'test-user',
            'options': {
                'model_name': 'gpt-4-vision-preview',
                'llm_provider': 'openai'
                # No max_cost_limit set
            }
        }
        
        # Mock the file download
        with patch('tasks.parsing.download_file_for_analysis') as mock_download:
            mock_download.return_value = ('test.pdf', 50000, 'application/pdf')
            
            is_valid, error_message, cost_estimate = validate_processing_cost(task_data)
            
            assert is_valid is True
            assert error_message is None
            assert isinstance(cost_estimate, CostEstimate)
    
    def test_parse_document_task_cost_validation_success(self):
        """Test document parsing task with successful cost validation."""
        task_data = {
            'task_id': 'test-task-123',
            'file_url': 'https://example.com/test.pdf',
            'user_id': 'test-user',
            'options': {
                'model_name': 'gpt-3.5-turbo',
                'llm_provider': 'openai',
                'max_cost_limit': 0.50
            }
        }
        
        # Mock the file download
        with patch('tasks.parsing.download_file_for_analysis') as mock_download:
            mock_download.return_value = ('test.pdf', 5000, 'application/pdf')
            
            # Test the cost validation function directly
            is_valid, error_message, cost_estimate = validate_processing_cost(task_data)
            
            assert is_valid is True
            assert error_message is None
            assert isinstance(cost_estimate, CostEstimate)
            assert cost_estimate.estimated_cost_usd > 0
            assert cost_estimate.estimated_cost_usd < 0.50  # Should be within limit
    
    def test_parse_document_task_cost_validation_failure(self):
        """Test document parsing task with cost validation failure."""
        task_data = {
            'task_id': 'test-task-123',
            'file_url': 'https://example.com/large_document.pdf',
            'user_id': 'test-user',
            'options': {
                'model_name': 'gpt-4',
                'llm_provider': 'openai',
                'max_cost_limit': 0.01  # Very low limit
            }
        }
        
        # Mock the file download to return a large file
        with patch('tasks.parsing.download_file_for_analysis') as mock_download:
            mock_download.return_value = ('large_document.pdf', 1000000, 'application/pdf')  # 1MB
            
            # Test the cost validation function directly
            is_valid, error_message, cost_estimate = validate_processing_cost(task_data)
            
            assert is_valid is False
            assert error_message is not None
            assert 'exceeds limit' in error_message
            assert isinstance(cost_estimate, CostEstimate)
            assert cost_estimate.max_possible_cost_usd > 0.01  # Should exceed the limit
    
    def test_parse_document_task_cost_estimation_error(self):
        """Test document parsing task when cost estimation fails."""
        task_data = {
            'task_id': 'test-task-123',
            'file_url': 'https://invalid-url.com/test.pdf',
            'user_id': 'test-user',
            'options': {
                'model_name': 'gpt-4-vision-preview',
                'llm_provider': 'openai',
                'max_cost_limit': 1.0
            }
        }
        
        # Mock the file download to raise an exception
        with patch('tasks.parsing.download_file_for_analysis') as mock_download:
            mock_download.side_effect = Exception("Network error")
            
            # Test the cost validation function directly
            is_valid, error_message, cost_estimate = validate_processing_cost(task_data)
            
            # Should handle the error gracefully and return fallback values
            assert is_valid is False
            assert error_message is not None
            assert "Cost validation failed" in error_message
            # Cost estimate might be None or a fallback estimate
    
    def test_different_document_types_cost_estimation(self):
        """Test cost estimation for different document types."""
        base_task_data = {
            'task_id': 'test-task-123',
            'user_id': 'test-user',
            'options': {
                'model_name': 'gpt-4-vision-preview',
                'llm_provider': 'openai',
                'max_cost_limit': 2.0
            }
        }
        
        test_cases = [
            ('https://example.com/text.txt', 'text.txt', 2000, 'text/plain'),
            ('https://example.com/document.pdf', 'document.pdf', 50000, 'application/pdf'),
            ('https://example.com/image.jpg', 'image.jpg', 500000, 'image/jpeg'),
            ('https://example.com/doc.docx', 'doc.docx', 30000, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        ]
        
        for file_url, filename, file_size, content_type in test_cases:
            task_data = {**base_task_data, 'file_url': file_url}
            
            with patch('tasks.parsing.download_file_for_analysis') as mock_download:
                mock_download.return_value = (filename, file_size, content_type)
                
                is_valid, error_message, cost_estimate = validate_processing_cost(task_data)
                
                assert isinstance(cost_estimate, CostEstimate)
                assert cost_estimate.estimated_cost_usd > 0
                assert cost_estimate.total_estimated_tokens > 0
                
                # Image files should generally have higher base token counts
                if content_type.startswith('image/'):
                    assert cost_estimate.estimated_input_tokens >= 1000
    
    def test_cost_estimation_with_different_models(self):
        """Test cost estimation with different LLM models."""
        base_task_data = {
            'task_id': 'test-task-123',
            'file_url': 'https://example.com/test.pdf',
            'user_id': 'test-user',
            'options': {
                'llm_provider': 'openai',
                'max_cost_limit': 1.0
            }
        }
        
        models = ['gpt-4-vision-preview', 'gpt-4', 'gpt-3.5-turbo']
        
        for model in models:
            task_data = {**base_task_data}
            task_data['options']['model_name'] = model
            
            with patch('tasks.parsing.download_file_for_analysis') as mock_download:
                mock_download.return_value = ('test.pdf', 10000, 'application/pdf')
                
                is_valid, error_message, cost_estimate = validate_processing_cost(task_data)
                
                assert isinstance(cost_estimate, CostEstimate)
                assert cost_estimate.model_name == model
                assert cost_estimate.estimated_cost_usd > 0
                
                # GPT-3.5-turbo should generally be cheaper than GPT-4
                if model == 'gpt-3.5-turbo':
                    assert cost_estimate.estimated_cost_usd < 0.10  # Should be relatively cheap
    
    def test_batch_cost_estimation_scenario(self):
        """Test scenario with multiple files for batch processing."""
        files = [
            ('https://example.com/doc1.txt', 'doc1.txt', 1000, 'text/plain'),
            ('https://example.com/doc2.pdf', 'doc2.pdf', 20000, 'application/pdf'),
            ('https://example.com/image.png', 'image.png', 300000, 'image/png')
        ]
        
        total_estimated_cost = 0.0
        
        for file_url, filename, file_size, content_type in files:
            task_data = {
                'task_id': f'test-task-{filename}',
                'file_url': file_url,
                'user_id': 'test-user',
                'options': {
                    'model_name': 'gpt-4-vision-preview',
                    'llm_provider': 'openai',
                    'max_cost_limit': 1.0
                }
            }
            
            with patch('tasks.parsing.download_file_for_analysis') as mock_download:
                mock_download.return_value = (filename, file_size, content_type)
                
                is_valid, error_message, cost_estimate = validate_processing_cost(task_data)
                
                assert is_valid is True
                assert isinstance(cost_estimate, CostEstimate)
                total_estimated_cost += cost_estimate.estimated_cost_usd
        
        # Total cost should be reasonable for batch processing
        assert total_estimated_cost > 0
        assert total_estimated_cost < 5.0  # Reasonable upper bound for test files


if __name__ == "__main__":
    pytest.main([__file__])