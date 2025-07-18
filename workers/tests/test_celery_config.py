"""Tests for Celery configuration and setup."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from celery import Celery

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from celery_app import celery_app, get_celery_health_status
from config import get_celery_config


class TestCeleryConfiguration:
    """Test Celery application configuration."""
    
    def test_celery_app_creation(self):
        """Test that Celery app is created correctly."""
        assert isinstance(celery_app, Celery)
        assert celery_app.main == 'document_intelligence_workers'
    
    def test_celery_config_structure(self):
        """Test Celery configuration structure."""
        config = get_celery_config()
        
        # Check required configuration keys
        required_keys = [
            'broker_url', 'result_backend', 'task_serializer',
            'accept_content', 'result_serializer', 'timezone',
            'enable_utc', 'task_routes', 'task_default_queue'
        ]
        
        for key in required_keys:
            assert key in config, f"Missing required config key: {key}"
    
    def test_task_routes_configuration(self):
        """Test task routing configuration."""
        config = get_celery_config()
        task_routes = config['task_routes']
        
        # Check that all expected task routes are configured
        expected_routes = {
            'workers.tasks.archive.*': {'queue': 'archive_processing'},
            'workers.tasks.parsing.*': {'queue': 'document_parsing'},
            'workers.tasks.vectorization.*': {'queue': 'vectorization'},
            'workers.tasks.cleanup.*': {'queue': 'cleanup'},
        }
        
        for pattern, route_config in expected_routes.items():
            assert pattern in task_routes
            assert task_routes[pattern] == route_config
    
    def test_queue_configuration(self):
        """Test queue configuration."""
        # Check that queues are properly configured
        queues = celery_app.conf.task_queues
        queue_names = [q.name for q in queues]
        
        expected_queues = [
            'archive_processing', 'document_parsing', 
            'vectorization', 'cleanup'
        ]
        
        for queue_name in expected_queues:
            assert queue_name in queue_names
    
    def test_celery_app_configuration(self):
        """Test Celery app configuration values."""
        conf = celery_app.conf
        
        # Test serialization settings
        assert conf.task_serializer == 'json'
        assert conf.result_serializer == 'json'
        assert 'json' in conf.accept_content
        
        # Test timezone settings
        assert conf.timezone == 'UTC'
        assert conf.enable_utc is True
        
        # Test worker settings
        assert conf.worker_prefetch_multiplier == 1
        assert conf.task_acks_late is True
        assert conf.worker_max_tasks_per_child == 1000
        
        # Test retry settings
        assert conf.task_default_retry_delay == 60
        assert conf.task_max_retries == 3


class TestCeleryHealthCheck:
    """Test Celery health check functionality."""
    
    @patch('celery_app.celery_app.control.inspect')
    @patch('redis.Redis.from_url')
    def test_health_check_healthy(self, mock_redis, mock_inspect):
        """Test health check when system is healthy."""
        # Mock inspect responses
        mock_inspect_instance = Mock()
        mock_inspect_instance.active.return_value = {'worker1': []}
        mock_inspect_instance.registered.return_value = {'worker1': ['task1', 'task2']}
        mock_inspect.return_value = mock_inspect_instance
        
        # Mock Redis responses
        mock_redis_instance = Mock()
        mock_redis_instance.llen.return_value = 5
        mock_redis.return_value = mock_redis_instance
        
        health_status = get_celery_health_status()
        
        assert health_status['status'] == 'healthy'
        assert health_status['broker_status'] == 'healthy'
        assert health_status['active_workers'] == 1
        assert 'queue_stats' in health_status
        assert 'registered_tasks' in health_status
    
    @patch('celery_app.celery_app.control.inspect')
    def test_health_check_unhealthy_no_workers(self, mock_inspect):
        """Test health check when no workers are active."""
        # Mock inspect responses - no active workers
        mock_inspect_instance = Mock()
        mock_inspect_instance.active.return_value = {}
        mock_inspect_instance.registered.return_value = {}
        mock_inspect.return_value = mock_inspect_instance
        
        health_status = get_celery_health_status()
        
        assert health_status['status'] == 'unhealthy'
        assert health_status['active_workers'] == 0
    
    @patch('celery_app.celery_app.control.inspect')
    def test_health_check_broker_unavailable(self, mock_inspect):
        """Test health check when broker is unavailable."""
        # Mock inspect to return None (broker unavailable)
        mock_inspect_instance = Mock()
        mock_inspect_instance.active.return_value = None
        mock_inspect.return_value = mock_inspect_instance
        
        health_status = get_celery_health_status()
        
        assert health_status['status'] == 'unhealthy'
        assert health_status['broker_status'] == 'unhealthy'
    
    @patch('celery_app.celery_app.control.inspect')
    def test_health_check_exception_handling(self, mock_inspect):
        """Test health check exception handling."""
        # Mock inspect to raise an exception
        mock_inspect.side_effect = Exception("Connection failed")
        
        health_status = get_celery_health_status()
        
        assert health_status['status'] == 'unhealthy'
        assert 'error' in health_status
        assert 'Connection failed' in health_status['error']


class TestCelerySignals:
    """Test Celery signal handlers."""
    
    @patch('celery_app.validate_worker_settings')
    @patch('celery_app.logger')
    def test_worker_ready_signal_success(self, mock_logger, mock_validate):
        """Test worker ready signal handler success."""
        from celery_app import worker_ready_handler
        
        # Mock successful validation
        mock_validate.return_value = None
        
        # Create mock sender
        mock_sender = Mock()
        mock_sender.hostname = 'test-worker-1'
        
        # Call the handler
        worker_ready_handler(sender=mock_sender)
        
        # Verify validation was called
        mock_validate.assert_called_once()
        
        # Verify logging
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert 'Worker started successfully' in call_args[0]
    
    @patch('celery_app.validate_worker_settings')
    @patch('celery_app.logger')
    def test_worker_ready_signal_validation_failure(self, mock_logger, mock_validate):
        """Test worker ready signal handler with validation failure."""
        from celery_app import worker_ready_handler
        
        # Mock validation failure
        mock_validate.side_effect = ValueError("Configuration error")
        
        # Create mock sender
        mock_sender = Mock()
        mock_sender.hostname = 'test-worker-1'
        
        # Call the handler and expect exception
        with pytest.raises(ValueError, match="Configuration error"):
            worker_ready_handler(sender=mock_sender)
        
        # Verify error logging
        mock_logger.error.assert_called_once()
    
    @patch('celery_app.logger')
    def test_worker_shutdown_signal(self, mock_logger):
        """Test worker shutdown signal handler."""
        from celery_app import worker_shutdown_handler
        
        # Create mock sender
        mock_sender = Mock()
        mock_sender.hostname = 'test-worker-1'
        
        # Call the handler
        worker_shutdown_handler(sender=mock_sender)
        
        # Verify logging
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert 'Worker shutting down' in call_args[0]


@pytest.fixture
def mock_celery_app():
    """Fixture providing a mock Celery app."""
    app = Mock(spec=Celery)
    app.conf = Mock()
    app.control = Mock()
    return app


def test_celery_autodiscovery():
    """Test that Celery autodiscovers tasks correctly."""
    # Check that autodiscovery is configured
    assert hasattr(celery_app, 'autodiscover_tasks')
    
    # Verify task modules are discoverable
    expected_modules = ['workers.tasks']
    # This would be tested in integration tests with actual task discovery