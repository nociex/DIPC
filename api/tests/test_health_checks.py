"""Tests for health check endpoints and monitoring utilities."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import aiohttp

from src.main import app
from src.monitoring.health_checks import HealthChecker, get_system_metrics, get_application_metrics


class TestHealthCheckEndpoints:
    """Test health check API endpoints."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_quick_health_check(self):
        """Test quick health check endpoint."""
        response = self.client.get("/v1/health/quick")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "dipc-api"
        assert data["version"] == "1.3.0"
        assert "timestamp" in data
    
    @patch('src.monitoring.health_checks.HealthChecker.get_comprehensive_health')
    def test_detailed_health_check_success(self, mock_health_check):
        """Test detailed health check with all components healthy."""
        mock_health_check.return_value = {
            "status": "healthy",
            "service": "dipc-api",
            "version": "1.3.0",
            "timestamp": 1234567890.0,
            "total_response_time": 0.5,
            "components": {
                "database": {"healthy": True, "response_time": 0.1},
                "redis": {"healthy": True, "response_time": 0.05},
                "storage": {"healthy": True, "response_time": 0.2}
            }
        }
        
        response = self.client.get("/v1/health/detailed")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "components" in data
        assert len(data["components"]) == 3
    
    @patch('src.monitoring.health_checks.HealthChecker.get_comprehensive_health')
    def test_detailed_health_check_failure(self, mock_health_check):
        """Test detailed health check when components are unhealthy."""
        mock_health_check.side_effect = Exception("Health check failed")
        
        response = self.client.get("/v1/health/detailed")
        assert response.status_code == 503
        assert "Health check failed" in response.json()["detail"]
    
    @patch('src.database.connection.get_database_health')
    def test_database_health_check_success(self, mock_db_health):
        """Test database-specific health check success."""
        mock_db_health.return_value = {
            "healthy": True,
            "response_time": 0.1,
            "database": "postgresql"
        }
        
        response = self.client.get("/v1/health/database")
        assert response.status_code == 200
        
        data = response.json()
        assert data["healthy"] is True
        assert data["database"] == "postgresql"
    
    @patch('src.database.connection.get_database_health')
    def test_database_health_check_failure(self, mock_db_health):
        """Test database-specific health check failure."""
        mock_db_health.return_value = {
            "healthy": False,
            "error": "Connection timeout",
            "database": "postgresql"
        }
        
        response = self.client.get("/v1/health/database")
        assert response.status_code == 503
        assert "Database unhealthy" in response.json()["detail"]
    
    @patch('src.monitoring.health_checks.HealthChecker.check_redis')
    def test_redis_health_check_success(self, mock_redis_health):
        """Test Redis-specific health check success."""
        mock_redis_health.return_value = {
            "healthy": True,
            "response_time": 0.05,
            "service": "redis"
        }
        
        response = self.client.get("/v1/health/redis")
        assert response.status_code == 200
        
        data = response.json()
        assert data["healthy"] is True
        assert data["service"] == "redis"
    
    @patch('src.monitoring.health_checks.get_system_metrics')
    def test_system_metrics_endpoint(self, mock_metrics):
        """Test system metrics endpoint."""
        mock_metrics.return_value = {
            "system": {
                "cpu_percent": 25.5,
                "memory": {"percent": 60.0},
                "disk": {"percent": 45.0}
            },
            "process": {
                "cpu_percent": 5.0,
                "num_threads": 10
            },
            "timestamp": 1234567890.0
        }
        
        response = self.client.get("/v1/health/metrics/system")
        assert response.status_code == 200
        
        data = response.json()
        assert "system" in data
        assert "process" in data
        assert data["system"]["cpu_percent"] == 25.5


class TestHealthChecker:
    """Test HealthChecker class functionality."""
    
    @pytest.fixture
    async def health_checker(self):
        """Create HealthChecker instance for testing."""
        checker = HealthChecker()
        await checker.__aenter__()
        yield checker
        await checker.__aexit__(None, None, None)
    
    @pytest.mark.asyncio
    async def test_check_database_success(self):
        """Test database health check success."""
        with patch('src.monitoring.health_checks.get_database_health') as mock_db_health:
            mock_db_health.return_value = {
                "healthy": True,
                "response_time": 0.1,
                "database": "postgresql"
            }
            
            checker = HealthChecker()
            result = await checker.check_database()
            
            assert result["healthy"] is True
            assert result["database"] == "postgresql"
    
    @pytest.mark.asyncio
    async def test_check_redis_success(self, health_checker):
        """Test Redis health check success."""
        # Mock Redis client
        health_checker.redis_client = AsyncMock()
        health_checker.redis_client.ping.return_value = True
        health_checker.redis_client.info.return_value = {
            "connected_clients": 5,
            "used_memory_human": "1.2M",
            "redis_version": "7.0.0",
            "uptime_in_seconds": 3600
        }
        health_checker.redis_client.set.return_value = True
        health_checker.redis_client.get.return_value = b"test_value"
        health_checker.redis_client.delete.return_value = True
        
        result = await health_checker.check_redis()
        
        assert result["healthy"] is True
        assert result["service"] == "redis"
        assert "connection_info" in result
        assert result["connection_info"]["connected_clients"] == 5
    
    @pytest.mark.asyncio
    async def test_check_redis_failure(self, health_checker):
        """Test Redis health check failure."""
        # Mock Redis client to raise exception
        health_checker.redis_client = AsyncMock()
        health_checker.redis_client.ping.side_effect = Exception("Connection failed")
        
        result = await health_checker.check_redis()
        
        assert result["healthy"] is False
        assert "Connection failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_check_celery_queues_success(self, health_checker):
        """Test Celery queue health check success."""
        # Mock Redis client for queue length checks
        health_checker.redis_client = AsyncMock()
        health_checker.redis_client.llen.return_value = 5
        
        result = await health_checker.check_celery_queues()
        
        assert result["healthy"] is True
        assert result["service"] == "celery_queues"
        assert "queue_stats" in result
        assert len(result["queue_stats"]) == 4  # Four queues
    
    @pytest.mark.asyncio
    async def test_check_storage_success(self, health_checker):
        """Test S3 storage health check success."""
        with patch('boto3.client') as mock_boto3:
            mock_s3_client = MagicMock()
            mock_boto3.return_value = mock_s3_client
            
            # Mock successful S3 operations
            mock_s3_client.head_bucket.return_value = {}
            mock_s3_client.get_bucket_location.return_value = {'LocationConstraint': 'us-west-2'}
            mock_s3_client.put_object.return_value = {}
            mock_s3_client.get_object.return_value = {'Body': MagicMock()}
            mock_s3_client.get_object.return_value['Body'].read.return_value = b"health check test"
            mock_s3_client.delete_object.return_value = {}
            
            result = await health_checker.check_storage()
            
            assert result["healthy"] is True
            assert result["service"] == "s3_storage"
            assert "bucket_info" in result
    
    @pytest.mark.asyncio
    async def test_check_vector_database_success(self, health_checker):
        """Test vector database health check success."""
        # Mock HTTP session
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"result": {"status": "ok"}}
        
        health_checker.http_session = AsyncMock()
        health_checker.http_session.get.return_value.__aenter__.return_value = mock_response
        
        result = await health_checker.check_vector_database()
        
        assert result["healthy"] is True
        assert result["service"] == "qdrant"
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_success(self, health_checker):
        """Test LLM providers health check success."""
        with patch('src.monitoring.health_checks.get_llm_provider_config') as mock_config:
            mock_config.return_value = {
                "openai": {
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "test-key"
                }
            }
            
            # Mock HTTP response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {"data": [{"id": "gpt-3.5-turbo"}]}
            
            health_checker.http_session = AsyncMock()
            health_checker.http_session.get.return_value.__aenter__.return_value = mock_response
            
            result = await health_checker.check_llm_providers()
            
            assert result["healthy"] is True
            assert result["service"] == "llm_providers"
            assert "openai" in result["providers"]
            assert result["providers"]["openai"]["healthy"] is True
    
    @pytest.mark.asyncio
    async def test_get_comprehensive_health_success(self, health_checker):
        """Test comprehensive health check with all components healthy."""
        # Mock all individual health checks
        health_checker.check_database = AsyncMock(return_value={"healthy": True})
        health_checker.check_redis = AsyncMock(return_value={"healthy": True})
        health_checker.check_celery_queues = AsyncMock(return_value={"healthy": True})
        health_checker.check_storage = AsyncMock(return_value={"healthy": True})
        health_checker.check_vector_database = AsyncMock(return_value={"healthy": True})
        health_checker.check_llm_providers = AsyncMock(return_value={"healthy": True})
        
        result = await health_checker.get_comprehensive_health()
        
        assert result["status"] == "healthy"
        assert result["service"] == "dipc-api"
        assert "components" in result
        assert len(result["components"]) == 6
        assert all(comp["healthy"] for comp in result["components"].values())
    
    @pytest.mark.asyncio
    async def test_get_comprehensive_health_partial_failure(self, health_checker):
        """Test comprehensive health check with some components unhealthy."""
        # Mock mixed health check results
        health_checker.check_database = AsyncMock(return_value={"healthy": True})
        health_checker.check_redis = AsyncMock(return_value={"healthy": False, "error": "Connection failed"})
        health_checker.check_celery_queues = AsyncMock(return_value={"healthy": True})
        health_checker.check_storage = AsyncMock(return_value={"healthy": True})
        health_checker.check_vector_database = AsyncMock(return_value={"healthy": True})
        health_checker.check_llm_providers = AsyncMock(return_value={"healthy": True})
        
        result = await health_checker.get_comprehensive_health()
        
        assert result["status"] == "unhealthy"
        assert result["components"]["redis"]["healthy"] is False
        assert "Connection failed" in result["components"]["redis"]["error"]


class TestMetrics:
    """Test metrics collection functionality."""
    
    @pytest.mark.asyncio
    async def test_get_system_metrics(self):
        """Test system metrics collection."""
        with patch('psutil.cpu_percent') as mock_cpu, \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk, \
             patch('psutil.Process') as mock_process:
            
            # Mock system metrics
            mock_cpu.return_value = 25.5
            mock_memory.return_value = MagicMock(
                total=8000000000,
                available=4000000000,
                percent=50.0,
                used=4000000000,
                free=4000000000
            )
            mock_disk.return_value = MagicMock(
                total=100000000000,
                used=50000000000,
                free=50000000000
            )
            
            # Mock process metrics
            mock_process_instance = MagicMock()
            mock_process_instance.memory_info.return_value = MagicMock(
                rss=100000000,
                vms=200000000
            )
            mock_process_instance.cpu_percent.return_value = 5.0
            mock_process_instance.num_threads.return_value = 10
            mock_process_instance.create_time.return_value = 1234567890.0
            mock_process.return_value = mock_process_instance
            
            result = await get_system_metrics()
            
            assert "system" in result
            assert "process" in result
            assert result["system"]["cpu_percent"] == 25.5
            assert result["system"]["memory"]["percent"] == 50.0
            assert result["process"]["cpu_percent"] == 5.0
            assert result["process"]["num_threads"] == 10
    
    @pytest.mark.asyncio
    async def test_get_application_metrics_success(self):
        """Test application metrics collection success."""
        with patch('src.monitoring.health_checks.AsyncSessionLocal') as mock_session:
            # Mock database session and queries
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Mock task statistics query result
            task_stats_result = [
                MagicMock(status='completed', count=100, avg_processing_time=30.5),
                MagicMock(status='pending', count=10, avg_processing_time=None),
                MagicMock(status='failed', count=5, avg_processing_time=15.2)
            ]
            
            # Mock database statistics query result
            db_stats_result = MagicMock(
                total_tasks=1000,
                tasks_last_hour=50,
                tasks_last_day=500
            )
            
            mock_session_instance.execute.side_effect = [
                MagicMock(fetchall=lambda: task_stats_result),
                MagicMock(fetchone=lambda: db_stats_result)
            ]
            
            result = await get_application_metrics()
            
            assert "tasks" in result
            assert "database" in result
            assert result["tasks"]["completed"]["count"] == 100
            assert result["tasks"]["completed"]["avg_processing_time"] == 30.5
            assert result["database"]["total_tasks"] == 1000
            assert result["database"]["tasks_last_hour"] == 50
    
    @pytest.mark.asyncio
    async def test_get_application_metrics_failure(self):
        """Test application metrics collection failure."""
        with patch('src.monitoring.health_checks.AsyncSessionLocal') as mock_session:
            mock_session.side_effect = Exception("Database connection failed")
            
            result = await get_application_metrics()
            
            assert result["error"] == "Database connection failed"
            assert "timestamp" in result


if __name__ == "__main__":
    pytest.main([__file__])