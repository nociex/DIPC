"""Document parsing tasks."""

from typing import Dict, Any, Optional
import structlog
import os
from urllib.parse import urlparse
import requests
import tempfile
from pathlib import Path
from dataclasses import asdict

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from celery_app import celery_app
from tasks.base import BaseTask, TaskStatus, create_task_result, validate_task_input
from utils.cost_estimation import estimate_processing_cost, CostEstimate
from llm.factory import LLMClientFactory, LLMProvider

logger = structlog.get_logger(__name__)


def calculate_actual_cost(token_usage, model_name: str, provider: str) -> float:
    """
    Calculate actual cost based on token usage and model pricing.
    
    Args:
        token_usage: TokenUsage object with prompt/completion tokens
        model_name: Name of the model used
        provider: LLM provider name
        
    Returns:
        Actual cost in USD
    """
    try:
        # Import cost calculation utilities
        from utils.cost_estimation import get_model_pricing
        
        pricing = get_model_pricing(model_name, provider)
        if not pricing:
            logger.warning(
                "No pricing info found for model",
                model_name=model_name,
                provider=provider
            )
            return 0.0
        
        # Calculate cost based on token usage
        prompt_cost = (token_usage.prompt_tokens / 1000) * pricing.get('input_cost_per_1k', 0)
        completion_cost = (token_usage.completion_tokens / 1000) * pricing.get('output_cost_per_1k', 0)
        
        total_cost = prompt_cost + completion_cost
        
        logger.debug(
            "Calculated actual cost",
            model_name=model_name,
            provider=provider,
            prompt_tokens=token_usage.prompt_tokens,
            completion_tokens=token_usage.completion_tokens,
            prompt_cost=prompt_cost,
            completion_cost=completion_cost,
            total_cost=total_cost
        )
        
        return round(total_cost, 4)
        
    except Exception as e:
        logger.error(
            "Failed to calculate actual cost",
            error=str(e),
            model_name=model_name,
            provider=provider
        )
        return 0.0


def store_parsing_results(task_id: str, result_data: Dict[str, Any], actual_cost: float) -> None:
    """
    Store parsing results in the database.
    
    Args:
        task_id: Task UUID
        result_data: Complete result data to store
        actual_cost: Calculated actual cost
    """
    try:
        # Import database utilities
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
        from api.src.database.repositories import TaskRepository
        from api.src.database.models import TaskStatusEnum
        from uuid import UUID
        
        task_repo = TaskRepository()
        
        # Update task with results and cost
        update_data = {
            'status': TaskStatusEnum.COMPLETED.value,
            'results': result_data,
            'actual_cost': actual_cost,
            'completed_at': result_data.get('metadata', {}).get('processing_timestamp')
        }
        
        task_repo.update_task(UUID(task_id), update_data)
        
        logger.info(
            "Parsing results stored successfully",
            task_id=task_id,
            actual_cost=actual_cost
        )
        
    except Exception as e:
        logger.error(
            "Failed to store parsing results in database",
            task_id=task_id,
            error=str(e)
        )
        # Re-raise to be handled by caller
        raise


def cleanup_temporary_resources(temp_files: list, storage_paths: list, task_id: str) -> None:
    """
    Clean up temporary files and resources created during processing.
    
    Args:
        temp_files: List of temporary file paths to clean up
        storage_paths: List of storage paths to clean up
        task_id: Task ID for logging
    """
    try:
        # Clean up temporary files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.debug("Cleaned up temporary file", file_path=temp_file, task_id=task_id)
            except Exception as e:
                logger.warning(
                    "Failed to clean up temporary file",
                    file_path=temp_file,
                    task_id=task_id,
                    error=str(e)
                )
        
        # Clean up storage paths if needed
        for storage_path in storage_paths:
            try:
                if os.path.exists(storage_path):
                    if os.path.isdir(storage_path):
                        import shutil
                        shutil.rmtree(storage_path)
                    else:
                        os.remove(storage_path)
                    logger.debug("Cleaned up storage path", path=storage_path, task_id=task_id)
            except Exception as e:
                logger.warning(
                    "Failed to clean up storage path",
                    path=storage_path,
                    task_id=task_id,
                    error=str(e)
                )
        
        if temp_files or storage_paths:
            logger.info(
                "Cleanup completed",
                task_id=task_id,
                temp_files_count=len(temp_files),
                storage_paths_count=len(storage_paths)
            )
            
    except Exception as e:
        logger.error(
            "Cleanup process failed",
            task_id=task_id,
            error=str(e)
        )


def download_file_for_analysis(file_url: str) -> tuple[str, int, str]:
    """
    Download file to get size and content type for cost estimation.
    
    Args:
        file_url: URL of the file to download
        
    Returns:
        Tuple of (filename, file_size_bytes, content_type)
    """
    try:
        # Make HEAD request first to get metadata
        head_response = requests.head(file_url, timeout=30)
        head_response.raise_for_status()
        
        content_length = head_response.headers.get('content-length')
        content_type = head_response.headers.get('content-type', 'application/octet-stream')
        
        if content_length:
            file_size = int(content_length)
        else:
            # If HEAD doesn't provide size, make GET request
            response = requests.get(file_url, timeout=60)
            response.raise_for_status()
            file_size = len(response.content)
        
        # Extract filename from URL
        parsed_url = urlparse(file_url)
        filename = os.path.basename(parsed_url.path) or "unknown_file"
        
        return filename, file_size, content_type
        
    except Exception as e:
        logger.error("Failed to download file for analysis", file_url=file_url, error=str(e))
        # Return conservative estimates
        return "unknown_file", 1024 * 1024, "application/octet-stream"  # 1MB default


def validate_processing_cost(
    task_data: Dict[str, Any]
) -> tuple[bool, Optional[str], Optional[CostEstimate]]:
    """
    Validate processing cost before starting document parsing.
    
    Args:
        task_data: Task data containing file info and options
        
    Returns:
        Tuple of (is_valid, error_message, cost_estimate)
    """
    try:
        file_url = task_data['file_url']
        options = task_data.get('options', {})
        
        # Get file information
        filename, file_size, content_type = download_file_for_analysis(file_url)
        
        # Determine model and provider
        model_name = options.get('model_name', 'gpt-4-vision-preview')
        provider = options.get('llm_provider', 'openai')
        max_cost_limit = options.get('max_cost_limit')
        
        # Estimate cost
        cost_estimate, is_valid, error_message = estimate_processing_cost(
            filename=filename,
            file_size_bytes=file_size,
            model_name=model_name,
            provider=provider,
            content_type=content_type,
            max_cost_limit=max_cost_limit
        )
        
        logger.info(
            "Cost validation completed",
            task_id=task_data['task_id'],
            filename=filename,
            file_size=file_size,
            estimated_cost=cost_estimate.estimated_cost_usd,
            max_cost=cost_estimate.max_possible_cost_usd,
            cost_limit=max_cost_limit,
            is_valid=is_valid,
            error_message=error_message
        )
        
        return is_valid, error_message, cost_estimate
        
    except Exception as e:
        error_msg = f"Cost validation failed: {str(e)}"
        logger.error("Cost validation error", task_id=task_data.get('task_id'), error=error_msg)
        return False, error_msg, None


@celery_app.task(bind=True, base=BaseTask, name='workers.tasks.parsing.parse_document_task')
def parse_document_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse individual documents using LLM with full processing pipeline.
    
    This task implements the complete document parsing workflow including:
    - Cost validation and estimation
    - Document preprocessing and format detection
    - LLM-based content extraction
    - Result storage and metadata management
    - Error handling and recovery mechanisms
    - Optional vectorization integration
    
    Args:
        task_data: Dictionary containing task information
            - task_id: UUID of the task
            - file_url: URL of the document file
            - user_id: ID of the user who submitted the task
            - options: Processing options including cost limits, extraction mode, etc.
    
    Returns:
        Dict containing parsing results and metadata
    """
    # Validate input
    validate_task_input(task_data, ['task_id', 'file_url', 'user_id'])
    
    task_id = task_data['task_id']
    file_url = task_data['file_url']
    user_id = task_data['user_id']
    options = task_data.get('options', {})
    
    logger.info(
        "Starting document parsing task with full processing pipeline",
        task_id=task_id,
        file_url=file_url,
        user_id=user_id,
        options=options
    )
    
    # Initialize variables for cleanup
    temp_files = []
    storage_paths = []
    
    try:
        # Step 1: Validate processing cost
        is_cost_valid, cost_error, cost_estimate = validate_processing_cost(task_data)
        
        if not is_cost_valid:
            logger.warning(
                "Task rejected due to cost validation failure",
                task_id=task_id,
                error=cost_error
            )
            
            result = create_task_result(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error_message=cost_error,
                result={
                    "error_code": "COST_LIMIT_EXCEEDED",
                    "error_message": cost_error,
                    "cost_estimate": asdict(cost_estimate) if cost_estimate else None,
                    "processing_stage": "cost_validation"
                }
            )
            return result.dict()
        
        # Step 2: Log cost estimate for successful validation
        if cost_estimate:
            logger.info(
                "Cost validation passed, proceeding with processing",
                task_id=task_id,
                estimated_cost=cost_estimate.estimated_cost_usd,
                max_cost=cost_estimate.max_possible_cost_usd,
                estimated_tokens=cost_estimate.total_estimated_tokens
            )
        
        # Step 3: Initialize document parsing service
        from document.parser import DocumentParsingService, ExtractionMode
        from llm.factory import LLMProvider
        
        try:
            # Get parsing options
            extraction_mode = options.get('extraction_mode', 'structured')
            custom_prompt = options.get('custom_prompt')
            llm_provider_name = options.get('llm_provider', 'openai')
            model_name = options.get('model_name')
            enable_vectorization = options.get('enable_vectorization', True)
            storage_policy = options.get('storage_policy', 'temporary')
            
            # Convert string to enum
            if isinstance(extraction_mode, str):
                extraction_mode = ExtractionMode(extraction_mode.lower())
            
            if isinstance(llm_provider_name, str):
                llm_provider = LLMProvider(llm_provider_name.lower())
            else:
                llm_provider = llm_provider_name
            
            logger.info(
                "Initializing parsing service",
                task_id=task_id,
                extraction_mode=extraction_mode.value,
                llm_provider=llm_provider.value,
                model_name=model_name,
                enable_vectorization=enable_vectorization
            )
            
            # Initialize parsing service
            parsing_service = DocumentParsingService(
                llm_provider=llm_provider,
                model_name=model_name
            )
            
        except Exception as init_error:
            error_message = f"Failed to initialize parsing service: {str(init_error)}"
            logger.error(
                "Parsing service initialization failed",
                task_id=task_id,
                error=error_message,
                exc_info=True
            )
            
            result = create_task_result(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error_message=error_message,
                result={
                    "error_code": "INITIALIZATION_ERROR",
                    "error_message": error_message,
                    "processing_stage": "service_initialization"
                }
            )
            return result.dict()
        
        # Step 4: Parse document with full pipeline
        try:
            logger.info(
                "Starting document parsing",
                task_id=task_id,
                processing_stage="document_parsing"
            )
            
            # Parse document
            parsing_result = parsing_service.parse_from_url(
                file_url=file_url,
                task_id=task_id,
                extraction_mode=extraction_mode,
                custom_prompt=custom_prompt
            )
            
            # Check if parsing was successful
            if parsing_result.error_message:
                logger.error(
                    "Document parsing failed",
                    task_id=task_id,
                    error=parsing_result.error_message,
                    processing_time=parsing_result.processing_time
                )
                
                result = create_task_result(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    error_message=parsing_result.error_message,
                    result={
                        "error_code": "PARSING_ERROR",
                        "error_message": parsing_result.error_message,
                        "cost_estimate": asdict(cost_estimate) if cost_estimate else None,
                        "processing_time": parsing_result.processing_time,
                        "processing_stage": "document_parsing",
                        "metadata": parsing_result.metadata
                    }
                )
                return result.dict()
            
            logger.info(
                "Document parsing completed successfully",
                task_id=task_id,
                confidence_score=parsing_result.confidence_score,
                processing_time=parsing_result.processing_time,
                total_tokens=parsing_result.token_usage.total_tokens
            )
            
        except Exception as parsing_error:
            error_message = f"Document parsing failed: {str(parsing_error)}"
            logger.error(
                "Document parsing error",
                task_id=task_id,
                error=error_message,
                exc_info=True
            )
            
            result = create_task_result(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error_message=error_message,
                result={
                    "error_code": "PARSING_SERVICE_ERROR",
                    "error_message": error_message,
                    "cost_estimate": asdict(cost_estimate) if cost_estimate else None,
                    "processing_stage": "document_parsing"
                }
            )
            return result.dict()
        
        # Step 5: Store results and manage metadata
        try:
            logger.info(
                "Storing parsing results",
                task_id=task_id,
                processing_stage="result_storage"
            )
            
            # Calculate actual cost based on token usage
            actual_cost = calculate_actual_cost(
                parsing_result.token_usage,
                model_name or "gpt-4-vision-preview",
                llm_provider.value
            )
            
            # Update token usage with actual cost
            actual_token_usage = {
                "prompt_tokens": parsing_result.token_usage.prompt_tokens,
                "completion_tokens": parsing_result.token_usage.completion_tokens,
                "total_tokens": parsing_result.token_usage.total_tokens,
                "estimated_cost": actual_cost
            }
            
            # Prepare comprehensive result data
            result_data = {
                "extracted_content": parsing_result.extracted_content,
                "confidence_score": parsing_result.confidence_score,
                "processing_time": parsing_result.processing_time,
                "cost_estimate": asdict(cost_estimate) if cost_estimate else None,
                "token_usage": actual_token_usage,
                "metadata": {
                    **parsing_result.metadata,
                    "extraction_mode": extraction_mode.value,
                    "llm_provider": llm_provider.value,
                    "model_name": model_name,
                    "storage_policy": storage_policy,
                    "vectorization_enabled": enable_vectorization,
                    "processing_stages_completed": [
                        "cost_validation",
                        "service_initialization", 
                        "document_parsing",
                        "result_storage"
                    ]
                }
            }
            
            # Store results in database
            store_parsing_results(task_id, result_data, actual_cost)
            
        except Exception as storage_error:
            error_message = f"Failed to store parsing results: {str(storage_error)}"
            logger.error(
                "Result storage failed",
                task_id=task_id,
                error=error_message,
                exc_info=True
            )
            
            # Still return the parsing results even if storage fails
            result_data = {
                "extracted_content": parsing_result.extracted_content,
                "confidence_score": parsing_result.confidence_score,
                "processing_time": parsing_result.processing_time,
                "token_usage": actual_token_usage,
                "metadata": parsing_result.metadata,
                "storage_warning": error_message
            }
        
        # Step 6: Trigger vectorization if enabled
        if enable_vectorization and parsing_result.extracted_content:
            try:
                logger.info(
                    "Triggering vectorization task",
                    task_id=task_id,
                    processing_stage="vectorization_trigger"
                )
                
                # Import vectorization task
                from tasks.vectorization import vectorize_content_task
                
                # Prepare vectorization data
                vectorization_data = {
                    'task_id': task_id,
                    'content': parsing_result.extracted_content,
                    'metadata': {
                        'original_filename': parsing_result.metadata.get('original_filename'),
                        'document_type': parsing_result.extracted_content.get('document_type'),
                        'confidence_score': parsing_result.confidence_score
                    },
                    'user_id': user_id
                }
                
                # Submit vectorization task asynchronously
                vectorization_task = vectorize_content_task.apply_async(
                    args=[vectorization_data],
                    queue='vectorization'
                )
                
                # Add vectorization task info to metadata
                result_data['metadata']['vectorization_task_id'] = vectorization_task.id
                result_data['metadata']['processing_stages_completed'].append('vectorization_trigger')
                
                logger.info(
                    "Vectorization task submitted",
                    task_id=task_id,
                    vectorization_task_id=vectorization_task.id
                )
                
            except Exception as vectorization_error:
                logger.warning(
                    "Failed to trigger vectorization",
                    task_id=task_id,
                    error=str(vectorization_error)
                )
                # Don't fail the main task if vectorization fails
                result_data['metadata']['vectorization_error'] = str(vectorization_error)
        
        # Step 7: Create final result
        result = create_task_result(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            result=result_data
        )
        
        logger.info(
            "Document parsing task completed successfully",
            task_id=task_id,
            confidence_score=parsing_result.confidence_score,
            processing_time=parsing_result.processing_time,
            total_tokens=parsing_result.token_usage.total_tokens,
            actual_cost=actual_cost,
            vectorization_enabled=enable_vectorization
        )
        
        return result.dict()
        
    except Exception as e:
        error_message = f"Document parsing task failed: {str(e)}"
        logger.error(
            "Document parsing task failed",
            task_id=task_id,
            error=error_message,
            exc_info=True
        )
        
        result = create_task_result(
            task_id=task_id,
            status=TaskStatus.FAILED,
            error_message=error_message,
            result={
                "error_code": "PROCESSING_ERROR",
                "error_message": error_message,
                "processing_stage": "unknown"
            }
        )
        
        return result.dict()
    
    finally:
        # Cleanup temporary files
        cleanup_temporary_resources(temp_files, storage_paths, task_id)