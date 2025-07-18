"""Health check endpoints."""

import time
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import HealthResponse
from ...database.connection import get_db_session, get_database_health
from ...monitoring.health_checks import HealthChecker, get_system_metrics, get_application_metrics
from ...config import settings

router = APIRouter()


@router.get("/detailed", response_model=HealthResponse)
async def detailed_health_check():
    """Detailed health check including all system components."""
    try:
        async with HealthChecker() as health_checker:
            health_status = await health_checker.get_comprehensive_health()
            return HealthResponse(**health_status)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Health check failed: {str(e)}"
        )


@router.get("/quick")
async def quick_health_check():
    """Quick health check for load balancer."""
    return {
        "status": "healthy",
        "service": "dipc-api",
        "version": "1.3.0",
        "timestamp": time.time()
    }


@router.get("/database")
async def database_health_check():
    """Database-specific health check."""
    db_health = await get_database_health()
    if not db_health["healthy"]:
        raise HTTPException(
            status_code=503,
            detail=f"Database unhealthy: {db_health.get('error', 'Unknown error')}"
        )
    return db_health


@router.get("/redis")
async def redis_health_check():
    """Redis-specific health check."""
    try:
        async with HealthChecker() as health_checker:
            redis_health = await health_checker.check_redis()
            if not redis_health["healthy"]:
                raise HTTPException(
                    status_code=503,
                    detail=f"Redis unhealthy: {redis_health.get('error', 'Unknown error')}"
                )
            return redis_health
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Redis health check failed: {str(e)}"
        )


@router.get("/storage")
async def storage_health_check():
    """Storage-specific health check."""
    try:
        async with HealthChecker() as health_checker:
            storage_health = await health_checker.check_storage()
            if not storage_health["healthy"]:
                raise HTTPException(
                    status_code=503,
                    detail=f"Storage unhealthy: {storage_health.get('error', 'Unknown error')}"
                )
            return storage_health
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Storage health check failed: {str(e)}"
        )


@router.get("/queues")
async def queues_health_check():
    """Message queue health check."""
    try:
        async with HealthChecker() as health_checker:
            queue_health = await health_checker.check_celery_queues()
            if not queue_health["healthy"]:
                raise HTTPException(
                    status_code=503,
                    detail=f"Queues unhealthy: {queue_health.get('error', 'Unknown error')}"
                )
            return queue_health
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Queue health check failed: {str(e)}"
        )


@router.get("/llm-providers")
async def llm_providers_health_check():
    """LLM providers health check."""
    try:
        async with HealthChecker() as health_checker:
            llm_health = await health_checker.check_llm_providers()
            if not llm_health["healthy"]:
                raise HTTPException(
                    status_code=503,
                    detail=f"LLM providers unhealthy: {llm_health.get('error', 'No providers available')}"
                )
            return llm_health
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"LLM provider health check failed: {str(e)}"
        )


@router.get("/vector-db")
async def vector_db_health_check():
    """Vector database health check."""
    try:
        async with HealthChecker() as health_checker:
            vector_health = await health_checker.check_vector_database()
            if not vector_health["healthy"]:
                raise HTTPException(
                    status_code=503,
                    detail=f"Vector database unhealthy: {vector_health.get('error', 'Unknown error')}"
                )
            return vector_health
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Vector database health check failed: {str(e)}"
        )


@router.get("/metrics/system")
async def system_metrics():
    """Get system performance metrics."""
    try:
        return await get_system_metrics()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get system metrics: {str(e)}"
        )


@router.get("/metrics/application")
async def application_metrics():
    """Get application-specific metrics."""
    try:
        return await get_application_metrics()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get application metrics: {str(e)}"
        )