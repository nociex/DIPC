"""API layer cost estimation utilities."""

import asyncio
import aiohttp
from typing import Tuple, Optional
from urllib.parse import urlparse
import structlog

logger = structlog.get_logger(__name__)


class CostEstimate:
    """Simple cost estimate data class for API layer."""
    
    def __init__(
        self,
        estimated_input_tokens: int,
        estimated_output_tokens: int,
        total_estimated_tokens: int,
        estimated_cost_usd: float,
        max_possible_cost_usd: float,
        model_name: str,
        provider: str,
        confidence: float
    ):
        self.estimated_input_tokens = estimated_input_tokens
        self.estimated_output_tokens = estimated_output_tokens
        self.total_estimated_tokens = total_estimated_tokens
        self.estimated_cost_usd = estimated_cost_usd
        self.max_possible_cost_usd = max_possible_cost_usd
        self.model_name = model_name
        self.provider = provider
        self.confidence = confidence


async def get_file_info_async(file_url: str) -> Tuple[str, int, str]:
    """
    Asynchronously get file information for cost estimation.
    
    Args:
        file_url: URL of the file
        
    Returns:
        Tuple of (filename, file_size_bytes, content_type)
    """
    try:
        async with aiohttp.ClientSession() as session:
            # Try HEAD request first
            async with session.head(file_url, timeout=30) as response:
                response.raise_for_status()
                
                content_length = response.headers.get('content-length')
                content_type = response.headers.get('content-type', 'application/octet-stream')
                
                if content_length:
                    file_size = int(content_length)
                else:
                    # If HEAD doesn't provide size, make GET request
                    async with session.get(file_url, timeout=60) as get_response:
                        get_response.raise_for_status()
                        content = await get_response.read()
                        file_size = len(content)
                
                # Extract filename from URL
                parsed_url = urlparse(file_url)
                filename = parsed_url.path.split('/')[-1] or "unknown_file"
                
                return filename, file_size, content_type
                
    except Exception as e:
        logger.error("Failed to get file info", file_url=file_url, error=str(e))
        # Return conservative estimates
        return "unknown_file", 1024 * 1024, "application/octet-stream"  # 1MB default


def estimate_cost_from_file_info(
    filename: str,
    file_size_bytes: int,
    model_name: str,
    provider: str = "openai",
    content_type: str = None
) -> CostEstimate:
    """
    Estimate processing cost from file information (synchronous version for API).
    
    This is a simplified version of the worker cost estimation logic.
    """
    # Import the worker utilities
    try:
        import sys
        import os
        
        # Add workers src to path temporarily
        workers_src_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'workers', 'src')
        if workers_src_path not in sys.path:
            sys.path.insert(0, workers_src_path)
        
        from utils.cost_estimation import cost_estimation_service
        
        # Use the worker service
        cost_estimate = cost_estimation_service.estimate_cost_from_file_info(
            filename=filename,
            file_size_bytes=file_size_bytes,
            model_name=model_name,
            provider=provider,
            content_type=content_type
        )
        
        # Convert to API CostEstimate
        return CostEstimate(
            estimated_input_tokens=cost_estimate.estimated_input_tokens,
            estimated_output_tokens=cost_estimate.estimated_output_tokens,
            total_estimated_tokens=cost_estimate.total_estimated_tokens,
            estimated_cost_usd=cost_estimate.estimated_cost_usd,
            max_possible_cost_usd=cost_estimate.max_possible_cost_usd,
            model_name=cost_estimate.model_name,
            provider=cost_estimate.provider,
            confidence=cost_estimate.confidence
        )
        
    except Exception as e:
        logger.error("Cost estimation failed", error=str(e))
        # Return conservative fallback estimate
        return CostEstimate(
            estimated_input_tokens=10000,
            estimated_output_tokens=1000,
            total_estimated_tokens=11000,
            estimated_cost_usd=1.0,
            max_possible_cost_usd=2.0,
            model_name=model_name,
            provider=provider,
            confidence=0.1
        )


def validate_cost_limit(cost_estimate: CostEstimate, max_cost_limit: Optional[float]) -> Tuple[bool, Optional[str]]:
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


async def estimate_task_cost(
    file_url: str,
    model_name: str,
    provider: str = "openai",
    max_cost_limit: Optional[float] = None
) -> Tuple[CostEstimate, bool, Optional[str]]:
    """
    Asynchronously estimate processing cost for a task.
    
    Args:
        file_url: URL of the file to process
        model_name: LLM model to use
        provider: LLM provider
        max_cost_limit: Maximum allowed cost in USD
        
    Returns:
        Tuple of (cost_estimate, is_valid, error_message)
    """
    try:
        # Get file information asynchronously
        filename, file_size, content_type = await get_file_info_async(file_url)
        
        # Estimate cost
        cost_estimate = estimate_cost_from_file_info(
            filename=filename,
            file_size_bytes=file_size,
            model_name=model_name,
            provider=provider,
            content_type=content_type
        )
        
        # Validate cost limit
        is_valid, error_message = validate_cost_limit(cost_estimate, max_cost_limit)
        
        logger.info(
            "Task cost estimation completed",
            file_url=file_url,
            filename=filename,
            file_size=file_size,
            model_name=model_name,
            estimated_cost=cost_estimate.estimated_cost_usd,
            max_cost=cost_estimate.max_possible_cost_usd,
            is_valid=is_valid,
            error_message=error_message
        )
        
        return cost_estimate, is_valid, error_message
        
    except Exception as e:
        error_msg = f"Cost estimation failed: {str(e)}"
        logger.error("Task cost estimation error", file_url=file_url, error=error_msg)
        
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
        return fallback_estimate, False, error_msg


async def estimate_batch_cost(
    file_urls: list[str],
    model_name: str,
    provider: str = "openai",
    max_cost_limit: Optional[float] = None
) -> Tuple[float, list[str]]:
    """
    Estimate cost for multiple files in batch.
    
    Args:
        file_urls: List of file URLs to process
        model_name: LLM model to use
        provider: LLM provider
        max_cost_limit: Maximum allowed cost in USD per file
        
    Returns:
        Tuple of (total_estimated_cost, list_of_errors)
    """
    total_cost = 0.0
    errors = []
    
    # Process files concurrently
    tasks = [
        estimate_task_cost(file_url, model_name, provider, max_cost_limit)
        for file_url in file_urls
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            errors.append(f"File {file_urls[i]}: {str(result)}")
        else:
            cost_estimate, is_valid, error_message = result
            if not is_valid:
                errors.append(f"File {file_urls[i]}: {error_message}")
            else:
                total_cost += cost_estimate.estimated_cost_usd
    
    return total_cost, errors