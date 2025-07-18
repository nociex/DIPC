"""Tests for cost estimation utilities."""

import pytest
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.cost_estimation import (
    CostEstimationService,
    TokenEstimator,
    ModelPricingRegistry,
    DocumentType,
    TokenEstimate,
    CostEstimate,
    estimate_processing_cost
)


class TestTokenEstimator:
    """Test token estimation functionality."""
    
    def test_detect_document_type_from_content_type(self):
        """Test document type detection from content type."""
        estimator = TokenEstimator()
        
        # Test image types
        assert estimator.detect_document_type("test.jpg", "image/jpeg") == DocumentType.IMAGE
        assert estimator.detect_document_type("test.png", "image/png") == DocumentType.IMAGE
        
        # Test PDF
        assert estimator.detect_document_type("test.pdf", "application/pdf") == DocumentType.PDF
        
        # Test text
        assert estimator.detect_document_type("test.txt", "text/plain") == DocumentType.TEXT
        
        # Test Word documents
        assert estimator.detect_document_type("test.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document") == DocumentType.WORD
    
    def test_detect_document_type_from_filename(self):
        """Test document type detection from filename extension."""
        estimator = TokenEstimator()
        
        # Test without content type
        assert estimator.detect_document_type("image.jpg") == DocumentType.IMAGE
        assert estimator.detect_document_type("document.pdf") == DocumentType.PDF
        assert estimator.detect_document_type("text.txt") == DocumentType.TEXT
        assert estimator.detect_document_type("doc.docx") == DocumentType.WORD
        assert estimator.detect_document_type("unknown.xyz") == DocumentType.UNKNOWN
    
    def test_estimate_tokens_from_file_size_text(self):
        """Test token estimation for text documents."""
        estimator = TokenEstimator()
        
        # Test small text file
        estimate = estimator.estimate_tokens_from_file_size(1000, DocumentType.TEXT)
        
        assert isinstance(estimate, TokenEstimate)
        assert estimate.document_type == DocumentType.TEXT
        assert estimate.file_size_bytes == 1000
        assert estimate.estimated_tokens > 0
        assert 0 <= estimate.confidence <= 1
        
        # Should include base system tokens
        expected_content_tokens = int(1000 * TokenEstimator.TOKEN_RATIOS[DocumentType.TEXT])
        expected_total = expected_content_tokens + TokenEstimator.BASE_SYSTEM_TOKENS
        assert estimate.estimated_tokens == expected_total
    
    def test_estimate_tokens_from_file_size_image(self):
        """Test token estimation for image documents."""
        estimator = TokenEstimator()
        
        # Test image file
        estimate = estimator.estimate_tokens_from_file_size(500000, DocumentType.IMAGE)  # 500KB
        
        assert estimate.document_type == DocumentType.IMAGE
        assert estimate.file_size_bytes == 500000
        assert estimate.estimated_tokens > TokenEstimator.TOKEN_RATIOS[DocumentType.IMAGE]
        assert estimate.confidence == 0.7
    
    def test_estimate_tokens_from_content(self):
        """Test token estimation from actual content."""
        estimator = TokenEstimator()
        
        content = "This is a test document with some words and punctuation."
        estimate = estimator.estimate_tokens_from_content(content, DocumentType.TEXT)
        
        assert estimate.document_type == DocumentType.TEXT
        assert estimate.estimated_tokens > 0
        assert estimate.confidence == 0.9  # High confidence for content-based estimation
        assert estimate.file_size_bytes == len(content.encode('utf-8'))


class TestModelPricingRegistry:
    """Test model pricing registry."""
    
    def test_get_pricing_known_model(self):
        """Test getting pricing for known models."""
        pricing = ModelPricingRegistry.get_pricing("gpt-4-vision-preview")
        
        assert pricing.input_cost_per_1k_tokens > 0
        assert pricing.output_cost_per_1k_tokens > 0
        assert pricing.max_context_length > 0
        assert pricing.supports_vision is True
    
    def test_get_pricing_unknown_model(self):
        """Test getting pricing for unknown models (should return default)."""
        pricing = ModelPricingRegistry.get_pricing("unknown-model")
        
        assert pricing.input_cost_per_1k_tokens > 0
        assert pricing.output_cost_per_1k_tokens > 0
        assert pricing.max_context_length > 0
    
    def test_is_vision_model(self):
        """Test vision model detection."""
        assert ModelPricingRegistry.is_vision_model("gpt-4-vision-preview") is True
        assert ModelPricingRegistry.is_vision_model("gpt-3.5-turbo") is False
        assert ModelPricingRegistry.is_vision_model("unknown-model") is True  # Default supports vision


class TestCostEstimationService:
    """Test cost estimation service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = CostEstimationService()
    
    def test_estimate_cost_from_file_info(self):
        """Test cost estimation from file information."""
        estimate = self.service.estimate_cost_from_file_info(
            filename="test.pdf",
            file_size_bytes=10000,
            model_name="gpt-4-vision-preview",
            provider="openai",
            content_type="application/pdf"
        )
        
        assert isinstance(estimate, CostEstimate)
        assert estimate.estimated_input_tokens > 0
        assert estimate.estimated_output_tokens > 0
        assert estimate.total_estimated_tokens > 0
        assert estimate.estimated_cost_usd > 0
        assert estimate.max_possible_cost_usd > estimate.estimated_cost_usd
        assert estimate.model_name == "gpt-4-vision-preview"
        assert estimate.provider == "openai"
        assert 0 <= estimate.confidence <= 1
    
    def test_estimate_cost_from_content(self):
        """Test cost estimation from content."""
        content = "This is a test document with multiple sentences. " * 100
        
        estimate = self.service.estimate_cost_from_content(
            content=content,
            model_name="gpt-4",
            provider="openai",
            document_type=DocumentType.TEXT
        )
        
        assert isinstance(estimate, CostEstimate)
        assert estimate.estimated_input_tokens > 0
        assert estimate.estimated_cost_usd > 0
        assert estimate.confidence == 0.9  # High confidence for content-based
    
    def test_validate_cost_limit_no_limit(self):
        """Test cost validation with no limit."""
        estimate = CostEstimate(
            estimated_input_tokens=1000,
            estimated_output_tokens=500,
            total_estimated_tokens=1500,
            estimated_cost_usd=0.05,
            max_possible_cost_usd=0.10,
            model_name="gpt-4",
            provider="openai",
            confidence=0.8
        )
        
        is_valid, error_msg = self.service.validate_cost_limit(estimate, None)
        assert is_valid is True
        assert error_msg is None
    
    def test_validate_cost_limit_within_limit(self):
        """Test cost validation within limit."""
        estimate = CostEstimate(
            estimated_input_tokens=1000,
            estimated_output_tokens=500,
            total_estimated_tokens=1500,
            estimated_cost_usd=0.05,
            max_possible_cost_usd=0.10,
            model_name="gpt-4",
            provider="openai",
            confidence=0.8
        )
        
        is_valid, error_msg = self.service.validate_cost_limit(estimate, 0.20)
        assert is_valid is True
        assert error_msg is None
    
    def test_validate_cost_limit_exceeds_limit(self):
        """Test cost validation exceeding limit."""
        estimate = CostEstimate(
            estimated_input_tokens=10000,
            estimated_output_tokens=5000,
            total_estimated_tokens=15000,
            estimated_cost_usd=0.50,
            max_possible_cost_usd=1.00,
            model_name="gpt-4",
            provider="openai",
            confidence=0.8
        )
        
        is_valid, error_msg = self.service.validate_cost_limit(estimate, 0.20)
        assert is_valid is False
        assert error_msg is not None
        assert "exceeds limit" in error_msg
        assert "$1.0000" in error_msg
        assert "$0.2000" in error_msg
    
    def test_validate_cost_limit_invalid_limit(self):
        """Test cost validation with invalid limit."""
        estimate = CostEstimate(
            estimated_input_tokens=1000,
            estimated_output_tokens=500,
            total_estimated_tokens=1500,
            estimated_cost_usd=0.05,
            max_possible_cost_usd=0.10,
            model_name="gpt-4",
            provider="openai",
            confidence=0.8
        )
        
        is_valid, error_msg = self.service.validate_cost_limit(estimate, 0)
        assert is_valid is False
        assert "must be greater than 0" in error_msg
    
    def test_get_cost_breakdown(self):
        """Test cost breakdown generation."""
        estimate = CostEstimate(
            estimated_input_tokens=1000,
            estimated_output_tokens=500,
            total_estimated_tokens=1500,
            estimated_cost_usd=0.05,
            max_possible_cost_usd=0.10,
            model_name="gpt-4-vision-preview",
            provider="openai",
            confidence=0.8
        )
        
        breakdown = self.service.get_cost_breakdown(estimate)
        
        assert isinstance(breakdown, dict)
        assert breakdown["model_name"] == "gpt-4-vision-preview"
        assert breakdown["provider"] == "openai"
        assert breakdown["estimated_input_tokens"] == 1000
        assert breakdown["estimated_output_tokens"] == 500
        assert breakdown["total_estimated_tokens"] == 1500
        assert breakdown["estimated_cost_usd"] == 0.05
        assert breakdown["max_possible_cost_usd"] == 0.10
        assert breakdown["confidence"] == 0.8
        assert "input_cost_per_1k" in breakdown
        assert "output_cost_per_1k" in breakdown
        assert "supports_vision" in breakdown


class TestEstimateProcessingCost:
    """Test the convenience function."""
    
    def test_estimate_processing_cost_success(self):
        """Test successful cost estimation."""
        estimate, is_valid, error_msg = estimate_processing_cost(
            filename="test.pdf",
            file_size_bytes=5000,
            model_name="gpt-4-vision-preview",
            provider="openai",
            content_type="application/pdf",
            max_cost_limit=1.0
        )
        
        assert isinstance(estimate, CostEstimate)
        assert is_valid is True
        assert error_msg is None
    
    def test_estimate_processing_cost_exceeds_limit(self):
        """Test cost estimation exceeding limit."""
        estimate, is_valid, error_msg = estimate_processing_cost(
            filename="large_document.pdf",
            file_size_bytes=1000000,  # 1MB
            model_name="gpt-4",
            provider="openai",
            content_type="application/pdf",
            max_cost_limit=0.01  # Very low limit
        )
        
        assert isinstance(estimate, CostEstimate)
        assert is_valid is False
        assert error_msg is not None
        assert "exceeds limit" in error_msg
    
    @patch('utils.cost_estimation.cost_estimation_service.estimate_cost_from_file_info')
    def test_estimate_processing_cost_error_handling(self, mock_estimate):
        """Test error handling in cost estimation."""
        mock_estimate.side_effect = Exception("Test error")
        
        estimate, is_valid, error_msg = estimate_processing_cost(
            filename="test.pdf",
            file_size_bytes=5000,
            model_name="gpt-4",
            provider="openai"
        )
        
        assert isinstance(estimate, CostEstimate)
        assert is_valid is False
        assert error_msg is not None
        assert "Cost estimation error" in error_msg
        assert estimate.confidence == 0.1  # Low confidence fallback


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""
    
    def test_small_text_document(self):
        """Test cost estimation for small text document."""
        estimate, is_valid, error_msg = estimate_processing_cost(
            filename="small_doc.txt",
            file_size_bytes=2000,  # 2KB
            model_name="gpt-3.5-turbo",
            provider="openai",
            content_type="text/plain",
            max_cost_limit=0.10
        )
        
        assert is_valid is True
        assert estimate.estimated_cost_usd < 0.05  # Should be very cheap
    
    def test_large_pdf_document(self):
        """Test cost estimation for large PDF document."""
        estimate, is_valid, error_msg = estimate_processing_cost(
            filename="large_report.pdf",
            file_size_bytes=5000000,  # 5MB
            model_name="gpt-4-vision-preview",
            provider="openai",
            content_type="application/pdf",
            max_cost_limit=10.0
        )
        
        assert isinstance(estimate, CostEstimate)
        assert estimate.estimated_cost_usd > 0.1  # Should be more expensive
        # Validation depends on actual cost vs limit
    
    def test_image_document(self):
        """Test cost estimation for image document."""
        estimate, is_valid, error_msg = estimate_processing_cost(
            filename="screenshot.png",
            file_size_bytes=1000000,  # 1MB
            model_name="gpt-4-vision-preview",
            provider="openai",
            content_type="image/png",
            max_cost_limit=1.0
        )
        
        assert isinstance(estimate, CostEstimate)
        assert estimate.estimated_input_tokens >= TokenEstimator.TOKEN_RATIOS[DocumentType.IMAGE]
    
    def test_multiple_file_cost_estimation(self):
        """Test cost estimation for multiple files."""
        files = [
            ("doc1.txt", 1000, "text/plain"),
            ("doc2.pdf", 5000, "application/pdf"),
            ("image.jpg", 500000, "image/jpeg")
        ]
        
        total_estimated_cost = 0
        total_max_cost = 0
        
        for filename, size, content_type in files:
            estimate, is_valid, error_msg = estimate_processing_cost(
                filename=filename,
                file_size_bytes=size,
                model_name="gpt-4-vision-preview",
                provider="openai",
                content_type=content_type
            )
            
            assert isinstance(estimate, CostEstimate)
            total_estimated_cost += estimate.estimated_cost_usd
            total_max_cost += estimate.max_possible_cost_usd
        
        assert total_estimated_cost > 0
        assert total_max_cost > total_estimated_cost
        
        # Test batch validation
        batch_valid, batch_error = CostEstimationService().validate_cost_limit(
            CostEstimate(
                estimated_input_tokens=0,
                estimated_output_tokens=0,
                total_estimated_tokens=0,
                estimated_cost_usd=total_estimated_cost,
                max_possible_cost_usd=total_max_cost,
                model_name="gpt-4-vision-preview",
                provider="openai",
                confidence=0.8
            ),
            max_cost_limit=5.0
        )
        
        # Result depends on actual calculated costs
        assert isinstance(batch_valid, bool)


if __name__ == "__main__":
    pytest.main([__file__])