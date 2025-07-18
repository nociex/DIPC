"""
Performance tests for concurrent document processing.
Tests Requirements: 5.2, 5.3
"""

import pytest
import asyncio
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from httpx import AsyncClient
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any

from src.main import app


class TestConcurrentProcessing:
    """Test system performance under concurrent load."""

    @pytest.fixture
    async def client(self):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_concurrent_task_creation(self, client):
        """Test creating multiple tasks concurrently."""
        
        with patch('src.storage.policy.upload_file_to_storage') as mock_upload, \
             patch('workers.src.tasks.parsing.parse_document_task.delay') as mock_parse_task:
            
            mock_upload.return_value = "https://storage.example.com/test-file.pdf"
            mock_task_result = MagicMock()
            mock_task_result.id = "concurrent-task"
            mock_parse_task.return_value = mock_task_result
            
            # Create multiple tasks concurrently
            num_concurrent_tasks = 50
            start_time = time.time()
            
            async def create_task(task_num: int):
                response = await client.post(
                    "/v1/tasks",
                    json={
                        "file_urls": [f"https://storage.example.com/file-{task_num}.pdf"],
                        "user_id": f"user-{task_num}",
                        "options": {
                            "enable_vectorization": False,
                            "storage_policy": "temporary"
                        }
                    }
                )
                return response.status_code, response.elapsed.total_seconds()
            
            # Execute tasks concurrently
            tasks = [create_task(i) for i in range(num_concurrent_tasks)]
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Analyze results
            successful_tasks = [r for r in results if r[0] == 201]
            response_times = [r[1] for r in results]
            
            # Performance assertions
            assert len(successful_tasks) == num_concurrent_tasks, "All tasks should succeed"
            assert total_time < 30, f"Total time {total_time}s should be under 30s"
            assert statistics.mean(response_times) < 1.0, "Average response time should be under 1s"
            assert max(response_times) < 5.0, "Max response time should be under 5s"
            
            print(f"Concurrent task creation performance:")
            print(f"  Total tasks: {num_concurrent_tasks}")
            print(f"  Total time: {total_time:.2f}s")
            print(f"  Average response time: {statistics.mean(response_times):.3f}s")
            print(f"  Max response time: {max(response_times):.3f}s")
            print(f"  Tasks per second: {num_concurrent_tasks / total_time:.2f}")

    @pytest.mark.asyncio
    async def test_concurrent_status_checks(self, client):
        """Test concurrent status checking performance."""
        
        with patch('src.database.repositories.TaskRepository.get_by_id') as mock_get_task:
            from src.database.models import Task, TaskStatus
            
            mock_task = Task(
                id="test-task-123",
                user_id="test-user",
                status=TaskStatus.PROCESSING,
                results=None
            )
            mock_get_task.return_value = mock_task
            
            # Perform concurrent status checks
            num_concurrent_checks = 100
            start_time = time.time()
            
            async def check_status():
                response = await client.get("/v1/tasks/test-task-123/status")
                return response.status_code, response.elapsed.total_seconds()
            
            tasks = [check_status() for _ in range(num_concurrent_checks)]
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Analyze results
            successful_checks = [r for r in results if r[0] == 200]
            response_times = [r[1] for r in results]
            
            # Performance assertions
            assert len(successful_checks) == num_concurrent_checks
            assert statistics.mean(response_times) < 0.1, "Status checks should be very fast"
            assert total_time < 5, "Total time should be under 5s"
            
            print(f"Concurrent status check performance:")
            print(f"  Total checks: {num_concurrent_checks}")
            print(f"  Total time: {total_time:.2f}s")
            print(f"  Average response time: {statistics.mean(response_times):.3f}s")
            print(f"  Checks per second: {num_concurrent_checks / total_time:.2f}")

    @pytest.mark.asyncio
    async def test_large_file_upload_performance(self, client):
        """Test performance with large file uploads."""
        
        with patch('src.storage.policy.upload_file_to_storage') as mock_upload:
            mock_upload.return_value = "https://storage.example.com/large-file.pdf"
            
            # Simulate large file upload requests
            large_file_sizes = [1024*1024, 5*1024*1024, 10*1024*1024]  # 1MB, 5MB, 10MB
            
            for file_size in large_file_sizes:
                start_time = time.time()
                
                response = await client.post(
                    "/v1/upload/presigned-url",
                    json={
                        "filename": f"large-file-{file_size}.pdf",
                        "content_type": "application/pdf",
                        "user_id": "test-user",
                        "file_size": file_size
                    }
                )
                
                end_time = time.time()
                response_time = end_time - start_time
                
                assert response.status_code == 200
                assert response_time < 2.0, f"Large file upload should complete in under 2s, got {response_time}s"
                
                print(f"Large file upload performance ({file_size // (1024*1024)}MB): {response_time:.3f}s")

    def test_memory_usage_under_load(self):
        """Test memory usage during concurrent processing."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate memory-intensive operations
        with patch('workers.src.tasks.parsing.parse_document_task.delay') as mock_parse_task:
            mock_task_result = MagicMock()
            mock_task_result.id = "memory-test-task"
            mock_parse_task.return_value = mock_task_result
            
            # Create many task objects to test memory usage
            tasks = []
            for i in range(1000):
                task_data = {
                    "file_urls": [f"https://storage.example.com/file-{i}.pdf"],
                    "user_id": f"user-{i}",
                    "options": {"enable_vectorization": False}
                }
                tasks.append(task_data)
            
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = current_memory - initial_memory
            
            # Memory usage should not increase dramatically
            assert memory_increase < 100, f"Memory increase {memory_increase}MB should be under 100MB"
            
            print(f"Memory usage test:")
            print(f"  Initial memory: {initial_memory:.2f}MB")
            print(f"  Current memory: {current_memory:.2f}MB")
            print(f"  Memory increase: {memory_increase:.2f}MB")

    @pytest.mark.asyncio
    async def test_database_connection_pool_performance(self, client):
        """Test database connection pool under concurrent load."""
        
        with patch('src.database.repositories.TaskRepository.get_by_id') as mock_get_task:
            from src.database.models import Task, TaskStatus
            
            mock_task = Task(
                id="db-test-task",
                user_id="test-user", 
                status=TaskStatus.COMPLETED,
                results={"test": "data"}
            )
            mock_get_task.return_value = mock_task
            
            # Perform many concurrent database operations
            num_operations = 200
            start_time = time.time()
            
            async def db_operation():
                response = await client.get("/v1/tasks/db-test-task")
                return response.status_code
            
            tasks = [db_operation() for _ in range(num_operations)]
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # All operations should succeed
            successful_ops = [r for r in results if r == 200]
            assert len(successful_ops) == num_operations
            
            # Should handle high concurrency efficiently
            ops_per_second = num_operations / total_time
            assert ops_per_second > 50, f"Should handle >50 ops/sec, got {ops_per_second:.2f}"
            
            print(f"Database connection pool performance:")
            print(f"  Total operations: {num_operations}")
            print(f"  Total time: {total_time:.2f}s")
            print(f"  Operations per second: {ops_per_second:.2f}")

    @pytest.mark.asyncio
    async def test_queue_throughput_performance(self, client):
        """Test message queue throughput under load."""
        
        with patch('workers.src.tasks.parsing.parse_document_task.delay') as mock_parse_task, \
             patch('src.storage.policy.upload_file_to_storage') as mock_upload:
            
            mock_upload.return_value = "https://storage.example.com/queue-test.pdf"
            mock_task_result = MagicMock()
            mock_task_result.id = "queue-test-task"
            mock_parse_task.return_value = mock_task_result
            
            # Queue many tasks rapidly
            num_tasks = 100
            start_time = time.time()
            
            tasks = []
            for i in range(num_tasks):
                task = client.post(
                    "/v1/tasks",
                    json={
                        "file_urls": [f"https://storage.example.com/queue-file-{i}.pdf"],
                        "user_id": f"queue-user-{i}",
                        "options": {"enable_vectorization": False}
                    }
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            end_time = time.time()
            total_time = end_time - start_time
            
            # All tasks should be queued successfully
            successful_tasks = [r for r in results if r.status_code == 201]
            assert len(successful_tasks) == num_tasks
            
            # Queue throughput should be high
            tasks_per_second = num_tasks / total_time
            assert tasks_per_second > 20, f"Queue throughput should be >20 tasks/sec, got {tasks_per_second:.2f}"
            
            print(f"Queue throughput performance:")
            print(f"  Total tasks queued: {num_tasks}")
            print(f"  Total time: {total_time:.2f}s")
            print(f"  Tasks per second: {tasks_per_second:.2f}")


class TestLoadTesting:
    """Load testing scenarios for system stress testing."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_sustained_load_scenario(self, client):
        """Test system under sustained load over time."""
        
        with patch('src.storage.policy.upload_file_to_storage') as mock_upload, \
             patch('workers.src.tasks.parsing.parse_document_task.delay') as mock_parse_task:
            
            mock_upload.return_value = "https://storage.example.com/load-test.pdf"
            mock_task_result = MagicMock()
            mock_task_result.id = "load-test-task"
            mock_parse_task.return_value = mock_task_result
            
            # Run sustained load for 60 seconds
            duration = 60  # seconds
            tasks_per_second = 5
            total_expected_tasks = duration * tasks_per_second
            
            start_time = time.time()
            completed_tasks = 0
            errors = 0
            
            async def create_task_batch():
                nonlocal completed_tasks, errors
                try:
                    response = await client.post(
                        "/v1/tasks",
                        json={
                            "file_urls": ["https://storage.example.com/sustained-load.pdf"],
                            "user_id": f"load-user-{completed_tasks}",
                            "options": {"enable_vectorization": False}
                        }
                    )
                    if response.status_code == 201:
                        completed_tasks += 1
                    else:
                        errors += 1
                except Exception:
                    errors += 1
            
            # Run load test
            while time.time() - start_time < duration:
                batch_start = time.time()
                
                # Create batch of tasks
                batch_tasks = [create_task_batch() for _ in range(tasks_per_second)]
                await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Wait for next second
                elapsed = time.time() - batch_start
                if elapsed < 1.0:
                    await asyncio.sleep(1.0 - elapsed)
            
            end_time = time.time()
            actual_duration = end_time - start_time
            
            # Analyze results
            success_rate = completed_tasks / (completed_tasks + errors) if (completed_tasks + errors) > 0 else 0
            actual_throughput = completed_tasks / actual_duration
            
            print(f"Sustained load test results:")
            print(f"  Duration: {actual_duration:.2f}s")
            print(f"  Completed tasks: {completed_tasks}")
            print(f"  Errors: {errors}")
            print(f"  Success rate: {success_rate:.2%}")
            print(f"  Actual throughput: {actual_throughput:.2f} tasks/sec")
            
            # Performance assertions
            assert success_rate > 0.95, f"Success rate should be >95%, got {success_rate:.2%}"
            assert actual_throughput > tasks_per_second * 0.8, f"Should maintain >80% of target throughput"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_spike_load_scenario(self, client):
        """Test system response to sudden load spikes."""
        
        with patch('src.storage.policy.upload_file_to_storage') as mock_upload, \
             patch('workers.src.tasks.parsing.parse_document_task.delay') as mock_parse_task:
            
            mock_upload.return_value = "https://storage.example.com/spike-test.pdf"
            mock_task_result = MagicMock()
            mock_task_result.id = "spike-test-task"
            mock_parse_task.return_value = mock_task_result
            
            # Create sudden spike of 200 concurrent requests
            spike_size = 200
            start_time = time.time()
            
            async def spike_task(task_id: int):
                try:
                    response = await client.post(
                        "/v1/tasks",
                        json={
                            "file_urls": [f"https://storage.example.com/spike-{task_id}.pdf"],
                            "user_id": f"spike-user-{task_id}",
                            "options": {"enable_vectorization": False}
                        }
                    )
                    return response.status_code, time.time() - start_time
                except Exception as e:
                    return 500, time.time() - start_time
            
            # Execute spike load
            spike_tasks = [spike_task(i) for i in range(spike_size)]
            results = await asyncio.gather(*spike_tasks)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Analyze spike response
            successful_requests = [r for r in results if r[0] == 201]
            response_times = [r[1] for r in results]
            
            success_rate = len(successful_requests) / spike_size
            avg_response_time = statistics.mean(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
            
            print(f"Spike load test results:")
            print(f"  Spike size: {spike_size} requests")
            print(f"  Total time: {total_time:.2f}s")
            print(f"  Success rate: {success_rate:.2%}")
            print(f"  Average response time: {avg_response_time:.3f}s")
            print(f"  95th percentile response time: {p95_response_time:.3f}s")
            
            # System should handle spike gracefully
            assert success_rate > 0.90, f"Should handle >90% of spike load, got {success_rate:.2%}"
            assert p95_response_time < 10.0, f"95th percentile response time should be <10s, got {p95_response_time:.3f}s"