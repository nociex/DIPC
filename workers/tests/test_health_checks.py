"""Tests for worker health check functionality."""

import pytest
import time
import requests
from unittest.mock import MagicMock, patch, Mock
import threading

from src.monitoring.health_checks import (
    get_worker_health_status,
    get_worker_metrics,
    check_worker_readiness,
    _get_worker_info,
    _get_system_metrics,
    _get_celery_status,
    _check_dependencies
)
from src.health_endpoint import HealthCheckServer, start_health_server, stop_health_server


class TestWorkerHealthChecks:
    """Test worker health check functions."""
    
    def test_get_worker_info(self):
        """Test worker information collection."""
        with patch('socket.gethostname') as mock_hostname, \
             patch('os.getpid') as mock_pid:
            
            mock_hostname.return_value = "test-worker"
            mock_pid.return_value = 12345
            
            info = _get_worker_info()
            
            assert info["hostname"] == "test-worker"
            assert info["process_id"] == 12345
            assert info["worker_id"] == "test-worker-12345"
            assert "supported_formats" in info
            assert len(info["supported_formats"]) > 0
    
    def test_get_system_metrics(self):
        """Test system metrics collection."""
        with patch('psutil.cpu_percent') as mock_cpu, \
             patch('psutil.cpu_count') as mock_cpu_count, \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk, \
             patch('psutil.Process') as mock_process:
            
            # Mock system metrics
            mock_cpu.return_value = 25.5
            mock_cpu_count.return_value = 4
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
            
            metrics = _get_system_metrics()
            
            assert "cpu" in metrics
            assert "memory" in metrics
            assert "disk" in metrics
            assert "process" in metrics
            assert metrics["cpu"]["percent"] == 25.5
            assert metrics["memory"]["percent"] == 50.0
            assert metrics["memory_available"] is True  # 50% < 90%
            assert metrics["disk_available"] is True    # 50% > 10%
    
    def test_get_celery_status_success(self):
        """Test Celery status check success."""
        with patch('celery.current_app') as mock_app:
            # Mock Celery app
            mock_connection = MagicMock()
            mock_connection.ensure_connection = MagicMock()
            mock_app.connection.return_value.__enter__.return_value = mock_connection
            
            # Mock inspect
            mock_inspect = MagicMock()
            mock_inspect.active.return_value = {"worker1": []}
            mock_inspect.reserved.return_value = {"worker1": []}
            mock_inspect.stats.return_value = {"worker1": {"total": 100}}
            mock_app.control.inspect.return_value = mock_inspect
            
            status = _get_celery_status()
            
            assert status["broker_healthy"] is True
            assert "active_tasks" in status
            assert "reserved_tasks" in status
            assert "queues" in status
            assert len(status["queues"]) == 4
    
    def test_get_celery_status_failure(self):
        """Test Celery status check failure."""
        with patch('celery.current_app') as mock_app:
            # Mock connection failure
            mock_app.connection.side_effect = Exception("Connection failed")
            
            status = _get_celery_status()
            
            assert status["broker_healthy"] is False
            assert "error" in status
    
    def test_check_dependencies_redis_success(self):
        """Test Redis dependency check success."""
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = MagicMock()
            mock_redis.ping.return_value = True
            mock_redis.info.return_value = {
                "redis_version": "7.0.0",
                "connected_clients": 5,
                "used_memory_human": "1.2M"
            }
            mock_redis_class.from_url.return_value = mock_redis
            
            deps = _check_dependencies()
            
            assert deps["redis_healthy"] is True
            assert "redis_info" in deps
            assert deps["redis_info"]["version"] == "7.0.0"
    
    def test_check_dependencies_redis_failure(self):
        """Test Redis dependency check failure."""
        with patch('redis.Redis') as mock_redis_class:
            mock_redis_class.from_url.side_effect = Exception("Connection failed")
            
            deps = _check_dependencies()
            
            assert deps["redis_healthy"] is False
            assert "redis_error" in deps
    
    def test_check_dependencies_llm_providers(self):
        """Test LLM provider dependency checks."""
        with patch('requests.get') as mock_get, \
             patch('src.monitoring.health_checks.worker_settings') as mock_settings:
            
            # Mock settings
            mock_settings.openai_api_key = "test-key"
            mock_settings.openrouter_api_key = "test-key-2"
            
            # Mock successful response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            deps = _check_dependencies()
            
            assert "llm_providers" in deps
            assert "openai" in deps["llm_providers"]
            assert "openrouter" in deps["llm_providers"]
            assert deps["llm_providers"]["openai"]["healthy"] is True
            assert deps["llm_providers"]["openrouter"]["healthy"] is True
    
    def test_get_worker_health_status_healthy(self):
        """Test overall worker health status when healthy."""
        with patch('src.monitoring.health_checks._get_worker_info') as mock_info, \
             patch('src.monitoring.health_checks._get_system_metrics') as mock_metrics, \
             patch('src.monitoring.health_checks._get_celery_status') as mock_celery, \
             patch('src.monitoring.health_checks._check_dependencies') as mock_deps:
            
            # Mock all components as healthy
            mock_info.return_value = {"hostname": "test-worker"}
            mock_metrics.return_value = {
                "memory_available": True,
                "disk_available": True,
                "cpu": {"percent": 25.0}
            }
            mock_celery.return_value = {"broker_healthy": True}
            mock_deps.return_value = {"redis_healthy": True}
            
            health = get_worker_health_status()
            
            assert health["status"] == "healthy"
            assert health["service"] == "dipc-worker"
            assert "worker_info" in health
            assert "system_metrics" in health
            assert "celery_status" in health
            assert "dependencies" in health
    
    def test_get_worker_health_status_unhealthy(self):
        """Test overall worker health status when unhealthy."""
        with patch('src.monitoring.health_checks._get_worker_info') as mock_info, \
             patch('src.monitoring.health_checks._get_system_metrics') as mock_metrics, \
             patch('src.monitoring.health_checks._get_celery_status') as mock_celery, \
             patch('src.monitoring.health_checks._check_dependencies') as mock_deps:
            
            # Mock some components as unhealthy
            mock_info.return_value = {"hostname": "test-worker"}
            mock_metrics.return_value = {
                "memory_available": False,  # Unhealthy
                "disk_available": True,
                "cpu": {"percent": 95.0}
            }
            mock_celery.return_value = {"broker_healthy": False}  # Unhealthy
            mock_deps.return_value = {"redis_healthy": True}
            
            health = get_worker_health_status()
            
            assert health["status"] == "unhealthy"
    
    def test_get_worker_metrics(self):
        """Test worker metrics collection."""
        with patch('src.monitoring.health_checks._get_system_metrics') as mock_metrics, \
             patch('src.monitoring.health_checks._get_celery_status') as mock_celery, \
             patch('src.monitoring.health_checks._get_task_history') as mock_history, \
             patch('src.monitoring.health_checks._get_error_rates') as mock_errors:
            
            mock_metrics.return_value = {"cpu": {"percent": 25.0}}
            mock_celery.return_value = {"broker_healthy": True}
            mock_history.return_value = {"last_hour": {"completed": 10}}
            mock_errors.return_value = {"error_rate_percent": 2.5}
            
            metrics = get_worker_metrics()
            
            assert "timestamp" in metrics
            assert "system" in metrics
            assert "celery" in metrics
            assert "task_history" in metrics
            assert "error_rates" in metrics
    
    def test_check_worker_readiness_ready(self):
        """Test worker readiness check when ready."""
        with patch('src.monitoring.health_checks.get_worker_health_status') as mock_health:
            mock_health.return_value = {"status": "healthy"}
            
            ready = check_worker_readiness()
            
            assert ready is True
    
    def test_check_worker_readiness_not_ready(self):
        """Test worker readiness check when not ready."""
        with patch('src.monitoring.health_checks.get_worker_health_status') as mock_health:
            mock_health.return_value = {"status": "unhealthy"}
            
            ready = check_worker_readiness()
            
            assert ready is False
    
    def test_check_worker_readiness_exception(self):
        """Test worker readiness check with exception."""
        with patch('src.monitoring.health_checks.get_worker_health_status') as mock_health:
            mock_health.side_effect = Exception("Health check failed")
            
            ready = check_worker_readiness()
            
            assert ready is False


class TestHealthCheckServer:
    """Test health check HTTP server."""
    
    def setup_method(self):
        """Set up test environment."""
        self.test_port = 8081  # Use different port for testing
    
    def teardown_method(self):
        """Clean up after tests."""
        stop_health_server()
    
    def test_health_check_server_start_stop(self):
        """Test starting and stopping health check server."""
        server = HealthCheckServer(self.test_port)
        
        # Start server
        server.start()
        assert server.running is True
        assert server.thread is not None
        
        # Give server time to start
        time.sleep(0.1)
        
        # Stop server
        server.stop()
        assert server.running is False
    
    def test_health_endpoints(self):
        """Test health check endpoints."""
        server = HealthCheckServer(self.test_port)
        server.start()
        
        try:
            # Give server time to start
            time.sleep(0.2)
            
            # Test basic health endpoint
            response = requests.get(f"http://localhost:{self.test_port}/health", timeout=5)
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "dipc-worker"
            
            # Test readiness endpoint
            response = requests.get(f"http://localhost:{self.test_port}/health/ready", timeout=5)
            assert response.status_code in [200, 503]  # Depends on actual system state
            
            data = response.json()
            assert "ready" in data
            assert "timestamp" in data
            
        finally:
            server.stop()
    
    def test_health_endpoints_detailed(self):
        """Test detailed health endpoint."""
        with patch('src.monitoring.health_checks.get_worker_health_status') as mock_health:
            mock_health.return_value = {
                "status": "healthy",
                "service": "dipc-worker",
                "version": "1.3.0",
                "timestamp": time.time(),
                "worker_info": {"hostname": "test"},
                "system_metrics": {"cpu": {"percent": 25.0}},
                "celery_status": {"broker_healthy": True},
                "dependencies": {"redis_healthy": True}
            }
            
            server = HealthCheckServer(self.test_port)
            server.start()
            
            try:
                # Give server time to start
                time.sleep(0.2)
                
                response = requests.get(f"http://localhost:{self.test_port}/health/detailed", timeout=5)
                assert response.status_code == 200
                
                data = response.json()
                assert data["status"] == "healthy"
                assert "worker_info" in data
                assert "system_metrics" in data
                
            finally:
                server.stop()
    
    def test_health_endpoints_metrics(self):
        """Test metrics endpoint."""
        with patch('src.monitoring.health_checks.get_worker_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "timestamp": time.time(),
                "system": {"cpu": {"percent": 25.0}},
                "celery": {"broker_healthy": True},
                "task_history": {"last_hour": {"completed": 10}},
                "error_rates": {"error_rate_percent": 2.5}
            }
            
            server = HealthCheckServer(self.test_port)
            server.start()
            
            try:
                # Give server time to start
                time.sleep(0.2)
                
                response = requests.get(f"http://localhost:{self.test_port}/health/metrics", timeout=5)
                assert response.status_code == 200
                
                data = response.json()
                assert "timestamp" in data
                assert "system" in data
                assert "celery" in data
                
            finally:
                server.stop()
    
    def test_health_endpoint_not_found(self):
        """Test 404 for unknown endpoints."""
        server = HealthCheckServer(self.test_port)
        server.start()
        
        try:
            # Give server time to start
            time.sleep(0.2)
            
            response = requests.get(f"http://localhost:{self.test_port}/unknown", timeout=5)
            assert response.status_code == 404
            
        finally:
            server.stop()
    
    def test_global_health_server_functions(self):
        """Test global health server start/stop functions."""
        # Start global server
        start_health_server(self.test_port)
        
        # Give server time to start
        time.sleep(0.2)
        
        # Test endpoint
        response = requests.get(f"http://localhost:{self.test_port}/health", timeout=5)
        assert response.status_code == 200
        
        # Stop global server
        stop_health_server()
        
        # Server should be stopped
        with pytest.raises(requests.exceptions.ConnectionError):
            requests.get(f"http://localhost:{self.test_port}/health", timeout=1)


if __name__ == "__main__":
    pytest.main([__file__])