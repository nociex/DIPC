"""Cost estimation and validation utilities."""

import os
import re
from typing import Dict, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)


class DocumentType(str, Enum):
    """Supported document types for cost estimation."""
    PDF = "pdf"
    IMAGE = "image"
    TEXT = "text"
    WORD = "word"
    UNKNOWN = "unknown"


@dataclass
class ModelPricing:
    """Pricing information for LLM models."""
    input_cost_per_1k_tokens: float
    output_cost_per_1k_tokens: float
    max_context_length: int
    supports_vision: bool = False


@dataclass
class TokenEstimate:
    """Token count estimation for a document."""
    estimated_tokens: int
    document_type: DocumentType
    file_size_bytes: int
    confidence: float  # 0.0 to 1.0


@dataclass
class CostEstimate:
    """Cost estimation result."""
    estimated_input_tokens: int
    estimated_output_tokens: int
    total_estimated_tokens: int
    estimated_cost_usd: float
    max_possible_cost_usd: float
    model_name: str
    provider: str
    confidence: float


class ModelPricingRegistry:
    """Registry of model pricing information."""
    
    # Pricing data (as of 2024, subject to change)
    PRICING_DATA = {
        # OpenAI Models
        "gpt-4-vision-preview": ModelPricing(
            input_cost_per_1k_tokens=0.01,
            output_cost_per_1k_tokens=0.03,
            max_context_length=128000,
            supports_vision=True
        ),
        "gpt-4-turbo": ModelPricing(
            input_cost_per_1k_tokens=0.01,
            output_cost_per_1k_tokens=0.03,
            max_context_length=128000,
            supports_vision=True
        ),
        "gpt-4": ModelPricing(
            input_cost_per_1k_tokens=0.03,
            output_cost_per_1k_tokens=0.06,
            max_context_length=8192,
            supports_vision=False
        ),
        "gpt-3.5-turbo": ModelPricing(
            input_cost_per_1k_tokens=0.0015,
            output_cost_per_1k_tokens=0.002,
            max_context_length=16385,
            supports_vision=False
        ),
        
        # OpenRouter Models (examples)
        "openai/gpt-4-vision-preview": ModelPricing(
            input_cost_per_1k_tokens=0.01,
            output_cost_per_1k_tokens=0.03,
            max_context_length=128000,
            supports_vision=True
        ),
        "anthropic/claude-3-opus": ModelPricing(
            input_cost_per_1k_tokens=0.015,
            output_cost_per_1k_tokens=0.075,
            max_context_length=200000,
            supports_vision=True
        ),
        
        # Default fallback pricing
        "default": ModelPricing(
            input_cost_per_1k_tokens=0.01,
            output_cost_per_1k_tokens=0.03,
            max_context_length=128000,
            supports_vision=True
        )
    }
    
    @classmethod
    def get_pricing(cls, model_name: str) -> ModelPricing:
        """Get pricing information for a model."""
        return cls.PRICING_DATA.get(model_name, cls.PRICING_DATA["default"])
    
    @classmethod
    def is_vision_model(cls, model_name: str) -> bool:
        """Check if a model supports vision/image processing."""
        pricing = cls.get_pricing(model_name)
        return pricing.supports_vision


class TokenEstimator:
    """Estimates token count for different document types."""
    
    # Rough token-to-character ratios for different content types
    TOKEN_RATIOS = {
        DocumentType.TEXT: 0.25,      # ~4 characters per token for English text
        DocumentType.PDF: 0.3,        # Slightly higher due to formatting
        DocumentType.WORD: 0.3,       # Similar to PDF
        DocumentType.IMAGE: 1000,     # Base tokens for image processing
        DocumentType.UNKNOWN: 0.35    # Conservative estimate
    }
    
    # Additional tokens for system prompts and formatting
    BASE_SYSTEM_TOKENS = 500
    OUTPUT_TOKENS_ESTIMATE = 1000  # Conservative estimate for structured output
    
    @classmethod
    def detect_document_type(cls, filename: str, content_type: str = None) -> DocumentType:
        """Detect document type from filename and content type."""
        filename_lower = filename.lower()
        
        if content_type:
            if content_type.startswith('image/'):
                return DocumentType.IMAGE
            elif content_type == 'application/pdf':
                return DocumentType.PDF
            elif content_type in ['text/plain', 'text/csv']:
                return DocumentType.TEXT
            elif 'word' in content_type or 'document' in content_type:
                return DocumentType.WORD
        
        # Fallback to filename extension
        if filename_lower.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')):
            return DocumentType.IMAGE
        elif filename_lower.endswith('.pdf'):
            return DocumentType.PDF
        elif filename_lower.endswith(('.txt', '.csv', '.md')):
            return DocumentType.TEXT
        elif filename_lower.endswith(('.doc', '.docx')):
            return DocumentType.WORD
        
        return DocumentType.UNKNOWN
    
    @classmethod
    def estimate_tokens_from_file_size(cls, file_size_bytes: int, document_type: DocumentType) -> TokenEstimate:
        """
        Estimate token count based on file size and document type.
        
        Args:
            file_size_bytes: Size of the file in bytes
            document_type: Type of document
            
        Returns:
            TokenEstimate with estimated token count
        """
        if document_type == DocumentType.IMAGE:
            # For images, token count is mostly fixed (vision model processing)
            # Plus some variable amount based on image complexity/size
            base_tokens = cls.TOKEN_RATIOS[DocumentType.IMAGE]
            size_factor = min(file_size_bytes / (1024 * 1024), 10)  # Cap at 10MB equivalent
            estimated_tokens = int(base_tokens + (size_factor * 200))
            confidence = 0.7  # Medium confidence for image token estimation
        else:
            # For text-based documents, estimate based on character count
            # Rough estimate: file_size_bytes ≈ character count for text files
            estimated_chars = file_size_bytes
            token_ratio = cls.TOKEN_RATIOS[document_type]
            estimated_tokens = int(estimated_chars * token_ratio)
            confidence = 0.8 if document_type != DocumentType.UNKNOWN else 0.6
        
        # Add base system tokens
        estimated_tokens += cls.BASE_SYSTEM_TOKENS
        
        return TokenEstimate(
            estimated_tokens=estimated_tokens,
            document_type=document_type,
            file_size_bytes=file_size_bytes,
            confidence=confidence
        )
    
    @classmethod
    def estimate_tokens_from_content(cls, content: str, document_type: DocumentType = DocumentType.TEXT) -> TokenEstimate:
        """
        Estimate token count from actual content.
        
        Args:
            content: Document content as string
            document_type: Type of document
            
        Returns:
            TokenEstimate with estimated token count
        """
        # Simple token estimation based on whitespace and punctuation
        # This is a rough approximation - actual tokenization would be more accurate
        words = len(re.findall(r'\b\w+\b', content))
        chars = len(content)
        
        # Use multiple estimation methods and take average
        word_based_tokens = int(words * 1.3)  # ~1.3 tokens per word on average
        char_based_tokens = int(chars * cls.TOKEN_RATIOS[document_type])
        
        estimated_tokens = (word_based_tokens + char_based_tokens) // 2
        estimated_tokens += cls.BASE_SYSTEM_TOKENS
        
        return TokenEstimate(
            estimated_tokens=estimated_tokens,
            document_type=document_type,
            file_size_bytes=len(content.encode('utf-8')),
            confidence=0.9  # High confidence when we have actual content
        )


class CostEstimationService:
    """Service for estimating and validating processing costs."""
    
    def __init__(self):
        self.token_estimator = TokenEstimator()
        self.pricing_registry = ModelPricingRegistry()
    
    def estimate_cost_from_file_info(
        self,
        filename: str,
        file_size_bytes: int,
        model_name: str,
        provider: str = "openai",
        content_type: str = None
    ) -> CostEstimate:
        """
        Estimate processing cost from file information.
        
        Args:
            filename: Name of the file
            file_size_bytes: Size of the file in bytes
            model_name: LLM model to use
            provider: LLM provider
            content_type: MIME type of the file
            
        Returns:
            CostEstimate with detailed cost breakdown
        """
        # Detect document type
        doc_type = self.token_estimator.detect_document_type(filename, content_type)
        
        # Estimate tokens
        token_estimate = self.token_estimator.estimate_tokens_from_file_size(
            file_size_bytes, doc_type
        )
        
        # Get model pricing
        pricing = self.pricing_registry.get_pricing(model_name)
        
        # Calculate costs
        input_tokens = token_estimate.estimated_tokens
        output_tokens = self.token_estimator.OUTPUT_TOKENS_ESTIMATE
        total_tokens = input_tokens + output_tokens
        
        # Calculate cost in USD
        input_cost = (input_tokens / 1000) * pricing.input_cost_per_1k_tokens
        output_cost = (output_tokens / 1000) * pricing.output_cost_per_1k_tokens
        estimated_cost = input_cost + output_cost
        
        # Calculate maximum possible cost (with safety margin)
        safety_multiplier = 2.0  # 100% safety margin
        max_cost = estimated_cost * safety_multiplier
        
        return CostEstimate(
            estimated_input_tokens=input_tokens,
            estimated_output_tokens=output_tokens,
            total_estimated_tokens=total_tokens,
            estimated_cost_usd=estimated_cost,
            max_possible_cost_usd=max_cost,
            model_name=model_name,
            provider=provider,
            confidence=token_estimate.confidence
        )
    
    def estimate_cost_from_content(
        self,
        content: str,
        model_name: str,
        provider: str = "openai",
        document_type: DocumentType = DocumentType.TEXT
    ) -> CostEstimate:
        """
        Estimate processing cost from actual content.
        
        Args:
            content: Document content
            model_name: LLM model to use
            provider: LLM provider
            document_type: Type of document
            
        Returns:
            CostEstimate with detailed cost breakdown
        """
        # Estimate tokens from content
        token_estimate = self.token_estimator.estimate_tokens_from_content(content, document_type)
        
        # Get model pricing
        pricing = self.pricing_registry.get_pricing(model_name)
        
        # Calculate costs
        input_tokens = token_estimate.estimated_tokens
        output_tokens = self.token_estimator.OUTPUT_TOKENS_ESTIMATE
        total_tokens = input_tokens + output_tokens
        
        # Calculate cost in USD
        input_cost = (input_tokens / 1000) * pricing.input_cost_per_1k_tokens
        output_cost = (output_tokens / 1000) * pricing.output_cost_per_1k_tokens
        estimated_cost = input_cost + output_cost
        
        # Calculate maximum possible cost (with safety margin)
        safety_multiplier = 1.5  # 50% safety margin for content-based estimation
        max_cost = estimated_cost * safety_multiplier
        
        return CostEstimate(
            estimated_input_tokens=input_tokens,
            estimated_output_tokens=output_tokens,
            total_estimated_tokens=total_tokens,
            estimated_cost_usd=estimated_cost,
            max_possible_cost_usd=max_cost,
            model_name=model_name,
            provider=provider,
            confidence=token_estimate.confidence
        )
    
    def validate_cost_limit(
        self,
        cost_estimate: CostEstimate,
        max_cost_limit: Optional[float]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that estimated cost is within the specified limit.
        
        Args:
            cost_estimate: Cost estimation result
            max_cost_limit: Maximum allowed cost in USD (None means no limit)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if max_cost_limit is None:
            return True, None
        
        if max_cost_limit <= 0:
            return False, "Cost limit must be greater than 0"
        
        # Use maximum possible cost for validation (conservative approach)
        if cost_estimate.max_possible_cost_usd > max_cost_limit:
            error_msg = (
                f"Estimated processing cost (${cost_estimate.max_possible_cost_usd:.4f}) "
                f"exceeds limit (${max_cost_limit:.4f}). "
                f"Estimated tokens: {cost_estimate.total_estimated_tokens}, "
                f"Model: {cost_estimate.model_name}"
            )
            return False, error_msg
        
        return True, None
    
    def get_cost_breakdown(self, cost_estimate: CostEstimate) -> Dict[str, Any]:
        """
        Get detailed cost breakdown for logging/debugging.
        
        Args:
            cost_estimate: Cost estimation result
            
        Returns:
            Dictionary with detailed cost information
        """
        pricing = self.pricing_registry.get_pricing(cost_estimate.model_name)
        
        return {
            "model_name": cost_estimate.model_name,
            "provider": cost_estimate.provider,
            "estimated_input_tokens": cost_estimate.estimated_input_tokens,
            "estimated_output_tokens": cost_estimate.estimated_output_tokens,
            "total_estimated_tokens": cost_estimate.total_estimated_tokens,
            "input_cost_per_1k": pricing.input_cost_per_1k_tokens,
            "output_cost_per_1k": pricing.output_cost_per_1k_tokens,
            "estimated_cost_usd": cost_estimate.estimated_cost_usd,
            "max_possible_cost_usd": cost_estimate.max_possible_cost_usd,
            "confidence": cost_estimate.confidence,
            "supports_vision": pricing.supports_vision
        }


# Global service instance
cost_estimation_service = CostEstimationService()


def estimate_processing_cost(
    filename: str,
    file_size_bytes: int,
    model_name: str,
    provider: str = "openai",
    content_type: str = None,
    max_cost_limit: Optional[float] = None
) -> Tuple[CostEstimate, bool, Optional[str]]:
    """
    Convenience function to estimate cost and validate limits.
    
    Args:
        filename: Name of the file
        file_size_bytes: Size of the file in bytes
        model_name: LLM model to use
        provider: LLM provider
        content_type: MIME type of the file
        max_cost_limit: Maximum allowed cost in USD
        
    Returns:
        Tuple of (cost_estimate, is_valid, error_message)
    """
    try:
        # Estimate cost
        cost_estimate = cost_estimation_service.estimate_cost_from_file_info(
            filename=filename,
            file_size_bytes=file_size_bytes,
            model_name=model_name,
            provider=provider,
            content_type=content_type
        )
        
        # Validate cost limit
        is_valid, error_message = cost_estimation_service.validate_cost_limit(
            cost_estimate, max_cost_limit
        )
        
        # Log cost estimation
        logger.info(
            "Cost estimation completed",
            filename=filename,
            file_size_bytes=file_size_bytes,
            model_name=model_name,
            estimated_cost=cost_estimate.estimated_cost_usd,
            max_cost=cost_estimate.max_possible_cost_usd,
            is_valid=is_valid,
            error_message=error_message
        )
        
        return cost_estimate, is_valid, error_message
        
    except Exception as e:
        logger.error(
            "Cost estimation failed",
            filename=filename,
            error=str(e)
        )
        # Return conservative estimate on error
        fallback_estimate = CostEstimate(
            estimated_input_tokens=10000,
            estimated_output_tokens=1000,
            total_estimated_tokens=11000,
            estimated_cost_usd=1.0,
            max_possible_cost_usd=2.0,
            model_name=model_name,
            provider=provider,
            confidence=0.1
        )
        return fallback_estimate, False, f"Cost estimation error: {str(e)}"