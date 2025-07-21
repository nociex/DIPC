"""Task management endpoints."""

import time
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from ..models import (
    TaskCreateRequest,
    TaskResponse,
    TaskStatusResponse,
    TaskListResponse,
    TaskStatus,
    TaskType,
    TokenUsage,
    DocumentMetadata
)
from ...database.connection import get_db_session
from ...database.models import Task as TaskModel
from ...database.repositories import TaskRepository

router = APIRouter()


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    request: TaskCreateRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new document processing task with cost validation."""
    try:
        # Create task repository
        task_repo = TaskRepository(db)
        
        # Determine task type based on file URLs
        task_type = TaskType.ARCHIVE_PROCESSING if any(
            url.lower().endswith('.zip') for url in request.file_urls
        ) else TaskType.DOCUMENT_PARSING
        
        # Perform cost estimation for non-archive tasks
        estimated_cost = None
        if task_type == TaskType.DOCUMENT_PARSING and request.options.max_cost_limit is not None:
            try:
                from ...utils.cost_estimation_api import estimate_task_cost
                
                # Estimate cost for all files
                total_estimated_cost = 0.0
                cost_validation_errors = []
                
                for file_url in request.file_urls:
                    try:
                        cost_estimate, is_valid, error_msg = await estimate_task_cost(
                            file_url=file_url,
                            model_name=request.options.model_name or 'gpt-4-vision-preview',
                            provider=request.options.llm_provider or 'openai',
                            max_cost_limit=request.options.max_cost_limit
                        )
                        
                        if not is_valid:
                            cost_validation_errors.append(f"File {file_url}: {error_msg}")
                        else:
                            total_estimated_cost += cost_estimate.estimated_cost_usd
                            
                    except Exception as e:
                        cost_validation_errors.append(f"File {file_url}: Cost estimation failed - {str(e)}")
                
                # Check if any cost validation failed
                if cost_validation_errors:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error_code": "COST_VALIDATION_FAILED",
                            "error_message": "One or more files exceed cost limits",
                            "details": {
                                "errors": cost_validation_errors,
                                "max_cost_limit": request.options.max_cost_limit
                            }
                        }
                    )
                
                estimated_cost = total_estimated_cost
                
            except HTTPException:
                raise
            except Exception as e:
                # Log error but don't fail task creation for cost estimation errors
                import logging
                logging.warning(f"Cost estimation failed for task creation: {str(e)}")
        
        # Create task data
        task_data = {
            "user_id": request.user_id,
            "task_type": task_type.value,
            "file_urls": request.file_urls,
            "options": request.options.model_dump(),
            "status": TaskStatus.PENDING.value,
            "estimated_cost": estimated_cost,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Create the task
        task = await task_repo.create(task_data)
        
        # Convert to response model
        return TaskResponse(
            task_id=task.id,
            user_id=task.user_id,
            parent_task_id=task.parent_task_id,
            status=TaskStatus(task.status),
            task_type=TaskType(task.task_type),
            file_url=request.file_urls[0] if request.file_urls else None,
            options=request.options,
            estimated_cost=task.estimated_cost,
            actual_cost=task.actual_cost,
            results=task.results,
            error_message=task.error_message,
            created_at=task.created_at,
            updated_at=task.updated_at,
            completed_at=task.completed_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create task: {str(e)}"
        )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Retrieve task information by ID."""
    try:
        task_repo = TaskRepository(db)
        task = await task_repo.get_by_id(task_id)
        
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"Task with ID {task_id} not found"
            )
        
        # Convert options from JSON to TaskOptions model
        from ..models import TaskOptions
        options = TaskOptions(**task.options) if task.options else TaskOptions()
        
        # Convert token usage if available
        token_usage = None
        if task.token_usage:
            token_usage = TokenUsage(**task.token_usage)
        
        # Convert metadata if available
        metadata = None
        if task.metadata:
            metadata = DocumentMetadata(**task.metadata)
        
        return TaskResponse(
            task_id=task.id,
            user_id=task.user_id,
            parent_task_id=task.parent_task_id,
            status=TaskStatus(task.status),
            task_type=TaskType(task.task_type),
            file_url=task.file_url,
            options=options,
            estimated_cost=task.estimated_cost,
            actual_cost=task.actual_cost,
            results=task.results,
            error_message=task.error_message,
            created_at=task.created_at,
            updated_at=task.updated_at,
            completed_at=task.completed_at,
            token_usage=token_usage,
            metadata=metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve task: {str(e)}"
        )


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get task status information."""
    try:
        task_repo = TaskRepository(db)
        task = await task_repo.get_by_id(task_id)
        
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"Task with ID {task_id} not found"
            )
        
        # Calculate progress based on status
        progress = None
        if task.status == TaskStatus.PENDING.value:
            progress = 0.0
        elif task.status == TaskStatus.PROCESSING.value:
            progress = 50.0  # Rough estimate
        elif task.status == TaskStatus.COMPLETED.value:
            progress = 100.0
        elif task.status == TaskStatus.FAILED.value:
            progress = 0.0
        
        # Estimate completion time (placeholder logic)
        estimated_completion_time = None
        if task.status == TaskStatus.PROCESSING.value:
            # Rough estimate: 2 minutes from now
            estimated_completion_time = datetime.utcnow().replace(
                minute=datetime.utcnow().minute + 2
            )
        
        return TaskStatusResponse(
            task_id=task.id,
            status=TaskStatus(task.status),
            progress=progress,
            estimated_completion_time=estimated_completion_time,
            error_message=task.error_message,
            updated_at=task.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get task status: {str(e)}"
        )


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status: Optional[str] = Query(None, description="Filter by task status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db_session)
):
    """List tasks with optional filtering and pagination."""
    try:
        task_repo = TaskRepository(db)
        
        # Build filters
        filters = {}
        if user_id:
            filters["user_id"] = user_id
        if status:
            # Validate status
            try:
                TaskStatus(status)
                filters["status"] = status
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}"
                )
        
        # Get tasks with pagination
        tasks, total_count = await task_repo.list_with_pagination(
            filters=filters,
            page=page,
            page_size=page_size
        )
        
        # Convert to response models
        task_responses = []
        for task in tasks:
            # Convert options from JSON to TaskOptions model
            from ..models import TaskOptions
            options = TaskOptions(**task.options) if task.options else TaskOptions()
            
            # Convert token usage if available
            token_usage = None
            if task.token_usage:
                token_usage = TokenUsage(**task.token_usage)
            
            # Convert metadata if available
            metadata = None
            if task.metadata:
                metadata = DocumentMetadata(**task.metadata)
            
            task_responses.append(TaskResponse(
                task_id=task.id,
                user_id=task.user_id,
                parent_task_id=task.parent_task_id,
                status=TaskStatus(task.status),
                task_type=TaskType(task.task_type),
                file_url=task.file_url,
                options=options,
                estimated_cost=task.estimated_cost,
                actual_cost=task.actual_cost,
                results=task.results,
                error_message=task.error_message,
                created_at=task.created_at,
                updated_at=task.updated_at,
                completed_at=task.completed_at,
                token_usage=token_usage,
                metadata=metadata
            ))
        
        # Calculate pagination info
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page < total_pages
        
        return TaskListResponse(
            tasks=task_responses,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next=has_next
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list tasks: {str(e)}"
        )


@router.get("/{task_id}/download", response_class=Response)
async def download_task_results(
    task_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Download task results as a markdown file."""
    try:
        task_repo = TaskRepository(db)
        task = await task_repo.get_by_id(task_id)
        
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"Task with ID {task_id} not found"
            )
        
        # Check if task is completed
        if task.status != TaskStatus.COMPLETED.value:
            raise HTTPException(
                status_code=400,
                detail=f"Task is not completed. Current status: {task.status}"
            )
        
        # Check if results exist
        if not task.results:
            raise HTTPException(
                status_code=404,
                detail="No results available for this task"
            )
        
        # Get markdown content from results
        markdown_content = task.results.get("markdown", "")
        if not markdown_content:
            # If no markdown, try to get text content
            markdown_content = task.results.get("text", "")
        
        if not markdown_content:
            raise HTTPException(
                status_code=404,
                detail="No content available for download"
            )
        
        # Create filename
        filename = f"dipc-results-{task_id[:8]}.md"
        
        # Return as downloadable file
        return Response(
            content=markdown_content,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download task results: {str(e)}"
        )