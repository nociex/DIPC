"""
Load testing scenarios for system stress testing.
Tests Requirements: 5.1, 5.2, 5.3, 5.5
"""

import pytest
import asyncio
import time
import statistics
import random
from concurrent.futures import ThreadPoolExecutor
from httpx import AsyncClient
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any, Tuple

from src.main import app


class TestLoadScenarios:
    """Comprehensive load testing scenarios."""

    @pytest.fixture
    async def client(self):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://test", timeout=30.0) as ac:
            yield ac

    @pytest.mark.asyncio
    @pytest.mark.load
    async def test_realistic_user_workflow_load(self, client):
        """Test realistic user workflow under load."""
        
        with patch('src.storage.policy.upload_file_to_storage') as mock_upload, \
             patch('workers.src.tasks.parsing.parse_document_task.delay') as mock_parse_task:
            
            mock_upload.return_value = "https://storage.example.com/workflow-test.pdf"
            mock_task_result = MagicMock()
            mock_task_result.id = "workflow-task"
            mock_parse_task.return_value = mock_task_result
            
            # Simulate realistic user behavior
            num_users = 50
            workflow_duration = 120  # 2 minutes
            
            async def user_workflow(user_id: int):
                """Simulate a complete user workflow."""
                workflow_stats = {
                    "uploads": 0,
                    "tasks_created": 0,
                    "status_checks": 0,
                    "results_retrieved": 0,
                    "errors": 0
                }
                
                start_time = time.time()
                
                try:
                    while time.time() - start_time < workflow_duration:
                        # Step 1: Upload file (30% of time)
                        if random.random() < 0.3:
                            response = await client.post(
                                "/v1/upload/presigned-url",
                                json={
                                    "filename": f"user-{user_id}-doc-{workflow_stats['uploads']}.pdf",
                                    "content_type": "application/pdf",
                                    "user_id": f"load-user-{user_id}"
                                }
                            )
                            if response.status_code == 200:
                                workflow_stats["uploads"] += 1
                            else:
                                workflow_stats["errors"] += 1
                        
                        # Step 2: Create task (20% of time)
                        elif random.random() < 0.5:
                            response = await client.post(
                                "/v1/tasks",
                                json={
                                    "file_urls": [f"https://storage.example.com/user-{user_id}.pdf"],
                                    "user_id": f"load-user-{user_id}",
                                    "options": {
                                        "enable_vectorization": random.choice([True, False]),
                                        "storage_policy": random.choice(["permanent", "temporary"])
                                    }
                                }
                            )
                            if response.status_code == 201:
                                workflow_stats["tasks_created"] += 1
                            else:
                                workflow_stats["errors"] += 1
                        
                        # Step 3: Check status (40% of time)
                        elif random.random() < 0.8:
                            task_id = f"task-{user_id}-{random.randint(1, 10)}"
                            response = await client.get(f"/v1/tasks/{task_id}/status")
                            if response.status_code in [200, 404]:  # 404 is acceptable for non-existent tasks
                                workflow_stats["status_checks"] += 1
                            else:
                                workflow_stats["errors"] += 1
                        
                        # Step 4: Retrieve results (10% of time)
                        else:
                            task_id = f"task-{user_id}-{random.randint(1, 5)}"
                            response = await client.get(f"/v1/tasks/{task_id}/results")
                            if response.status_code in [200, 404]:  # 404 is acceptable
                                workflow_stats["results_retrieved"] += 1
                            else:
                                workflow_stats["errors"] += 1
                        
                        # Random delay between actions (0.1-2 seconds)
                        await asyncio.sleep(random.uniform(0.1, 2.0))
                
                except Exception as e:
                    workflow_stats["errors"] += 1
                
                return workflow_stats
            
            # Run concurrent user workflows
            start_time = time.time()
            user_tasks = [user_workflow(i) for i in range(num_users)]
            results = await asyncio.gather(*user_tasks, return_exceptions=True)
            end_time = time.time()
            
            # Analyze results
            successful_results = [r for r in results if isinstance(r, dict)]
            total_operations = sum(
                r["uploads"] + r["tasks_created"] + r["status_checks"] + r["results_retrieved"]
                for r in successful_results
            )
            total_errors = sum(r["errors"] for r in successful_results)
            
            error_rate = total_errors / (total_operations + total_errors) if (total_operations + total_errors) > 0 else 0
            operations_per_second = total_operations / (end_time - start_time)
            
            print(f"Realistic user workflow load test:")
            print(f"  Concurrent users: {num_users}")
            print(f"  Duration: {end_time - start_time:.2f}s")
            print(f"  Total operations: {total_operations}")
            print(f"  Total errors: {total_errors}")
            print(f"  Error rate: {error_rate:.2%}")
            print(f"  Operations per second: {operations_per_second:.2f}")
            
            # Performance assertions
            assert len(successful_results) >= num_users * 0.9, "At least 90% of users should complete workflows"
            assert error_rate < 0.05, f"Error rate should be <5%, got {error_rate:.2%}"
            assert operations_per_second > 10, f"Should handle >10 ops/sec, got {operations_per_second:.2f}"

    @pytest.mark.asyncio
    @pytest.mark.load
    async def test_batch_processing_load(self, client):
        """Test system under batch processing load."""
        
        with patch('src.storage.policy.upload_file_to_storage') as mock_upload, \
             patch('workers.src.tasks.archive.process_archive_task.delay') as mock_archive_task:
            
            mock_upload.return_value = "https://storage.example.com/batch-archive.zip"
            mock_task_result = MagicMock()
            mock_task_result.id = "batch-task"
            mock_archive_task.return_value = mock_task_result
            
            # Simulate multiple large batch uploads
            num_batches = 20
            files_per_batch = 50
            
            async def create_batch(batch_id: int):
                """Create a batch processing task."""
                try:
                    start_time = time.time()
                    
                    response = await client.post(
                        "/v1/tasks",
                        json={
                            "file_urls": [f"https://storage.example.com/batch-{batch_id}.zip"],
                            "user_id": f"batch-user-{batch_id}",
                            "options": {
                                "enable_vectorization": batch_id % 2 == 0,  # Alternate vectorization
                                "storage_policy": "temporary"
                            }
                        }
                    )
                    
                    end_time = time.time()
                    return {
                        "batch_id": batch_id,
                        "status_code": response.status_code,
                        "response_time": end_time - start_time,
                        "success": response.status_code == 201
                    }
                except Exception as e:
                    return {
                        "batch_id": batch_id,
                        "status_code": 500,
                        "response_time": 0,
                        "success": False,
                        "error": str(e)
                    }
            
            # Execute batch creation concurrently
            start_time = time.time()
            batch_tasks = [create_batch(i) for i in range(num_batches)]
            results = await asyncio.gather(*batch_tasks)
            end_time = time.time()
            
            # Analyze batch processing performance
            successful_batches = [r for r in results if r["success"]]
            response_times = [r["response_time"] for r in results if r["response_time"] > 0]
            
            success_rate = len(successful_batches) / num_batches
            avg_response_time = statistics.mean(response_times) if response_times else 0
            total_time = end_time - start_time
            
            print(f"Batch processing load test:")
            print(f"  Number of batches: {num_batches}")
            print(f"  Files per batch: {files_per_batch}")
            print(f"  Total processing time: {total_time:.2f}s")
            print(f"  Success rate: {success_rate:.2%}")
            print(f"  Average response time: {avg_response_time:.3f}s")
            print(f"  Batches per second: {num_batches / total_time:.2f}")
            
            # Performance assertions
            assert success_rate > 0.95, f"Batch success rate should be >95%, got {success_rate:.2%}"
            assert avg_response_time < 5.0, f"Average response time should be <5s, got {avg_response_time:.3f}s"

    @pytest.mark.asyncio
    @pytest.mark.load
    async def test_mixed_workload_stress(self, client):
        """Test system under mixed workload stress."""
        
        with patch('src.storage.policy.upload_file_to_storage') as mock_upload, \
             patch('workers.src.tasks.parsing.parse_document_task.delay') as mock_parse_task, \
             patch('workers.src.tasks.archive.process_archive_task.delay') as mock_archive_task:
            
            mock_upload.return_value = "https://storage.example.com/mixed-test.pdf"
            mock_task_result = MagicMock()
            mock_task_result.id = "mixed-task"
            mock_parse_task.return_value = mock_task_result
            mock_archive_task.return_value = mock_task_result
            
            # Define different workload types
            workload_types = [
                {"type": "single_doc", "weight": 0.6},
                {"type": "archive", "weight": 0.2},
                {"type": "status_check", "weight": 0.15},
                {"type": "result_retrieval", "weight": 0.05}
            ]
            
            total_operations = 500
            stress_duration = 180  # 3 minutes
            
            async def execute_operation(op_type: str, op_id: int):
                """Execute a single operation based on type."""
                try:
                    start_time = time.time()
                    
                    if op_type == "single_doc":
                        response = await client.post(
                            "/v1/tasks",
                            json={
                                "file_urls": [f"https://storage.example.com/doc-{op_id}.pdf"],
                                "user_id": f"stress-user-{op_id % 20}",  # 20 different users
                                "options": {
                                    "enable_vectorization": op_id % 3 == 0,
                                    "storage_policy": "temporary" if op_id % 2 == 0 else "permanent"
                                }
                            }
                        )
                    
                    elif op_type == "archive":
                        response = await client.post(
                            "/v1/tasks",
                            json={
                                "file_urls": [f"https://storage.example.com/archive-{op_id}.zip"],
                                "user_id": f"stress-user-{op_id % 20}",
                                "options": {"enable_vectorization": False, "storage_policy": "temporary"}
                            }
                        )
                    
                    elif op_type == "status_check":
                        task_id = f"task-{random.randint(1, 100)}"
                        response = await client.get(f"/v1/tasks/{task_id}/status")
                    
                    else:  # result_retrieval
                        task_id = f"task-{random.randint(1, 50)}"
                        response = await client.get(f"/v1/tasks/{task_id}/results")
                    
                    end_time = time.time()
                    return {
                        "type": op_type,
                        "success": response.status_code in [200, 201, 404],  # 404 acceptable for non-existent resources
                        "response_time": end_time - start_time,
                        "status_code": response.status_code
                    }
                
                except Exception as e:
                    return {
                        "type": op_type,
                        "success": False,
                        "response_time": 0,
                        "error": str(e)
                    }
            
            # Generate mixed workload
            operations = []
            for i in range(total_operations):
                # Select operation type based on weights
                rand_val = random.random()
                cumulative_weight = 0
                selected_type = "single_doc"
                
                for workload in workload_types:
                    cumulative_weight += workload["weight"]
                    if rand_val <= cumulative_weight:
                        selected_type = workload["type"]
                        break
                
                operations.append((selected_type, i))
            
            # Execute mixed workload with controlled rate
            start_time = time.time()
            results = []
            
            # Execute operations in batches to control load
            batch_size = 20
            for i in range(0, len(operations), batch_size):
                batch = operations[i:i + batch_size]
                batch_tasks = [execute_operation(op_type, op_id) for op_type, op_id in batch]
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                results.extend([r for r in batch_results if isinstance(r, dict)])
                
                # Small delay between batches
                await asyncio.sleep(0.1)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Analyze mixed workload results
            successful_ops = [r for r in results if r["success"]]
            failed_ops = [r for r in results if not r["success"]]
            
            # Group by operation type
            type_stats = {}
            for result in results:
                op_type = result["type"]
                if op_type not in type_stats:
                    type_stats[op_type] = {"count": 0, "success": 0, "response_times": []}
                
                type_stats[op_type]["count"] += 1
                if result["success"]:
                    type_stats[op_type]["success"] += 1
                if result["response_time"] > 0:
                    type_stats[op_type]["response_times"].append(result["response_time"])
            
            overall_success_rate = len(successful_ops) / len(results) if results else 0
            overall_throughput = len(results) / total_time
            
            print(f"Mixed workload stress test:")
            print(f"  Total operations: {len(results)}")
            print(f"  Duration: {total_time:.2f}s")
            print(f"  Overall success rate: {overall_success_rate:.2%}")
            print(f"  Overall throughput: {overall_throughput:.2f} ops/sec")
            print(f"  Failed operations: {len(failed_ops)}")
            
            for op_type, stats in type_stats.items():
                success_rate = stats["success"] / stats["count"] if stats["count"] > 0 else 0
                avg_response_time = statistics.mean(stats["response_times"]) if stats["response_times"] else 0
                print(f"  {op_type}: {stats['count']} ops, {success_rate:.2%} success, {avg_response_time:.3f}s avg")
            
            # Performance assertions
            assert overall_success_rate > 0.90, f"Overall success rate should be >90%, got {overall_success_rate:.2%}"
            assert overall_throughput > 5, f"Should handle >5 ops/sec, got {overall_throughput:.2f}"
            
            # Type-specific assertions
            for op_type, stats in type_stats.items():
                type_success_rate = stats["success"] / stats["count"] if stats["count"] > 0 else 0
                assert type_success_rate > 0.85, f"{op_type} success rate should be >85%, got {type_success_rate:.2%}"

    @pytest.mark.asyncio
    @pytest.mark.load
    async def test_memory_pressure_load(self, client):
        """Test system behavior under memory pressure."""
        
        with patch('src.storage.policy.upload_file_to_storage') as mock_upload, \
             patch('workers.src.tasks.parsing.parse_document_task.delay') as mock_parse_task:
            
            mock_upload.return_value = "https://storage.example.com/memory-test.pdf"
            mock_task_result = MagicMock()
            mock_task_result.id = "memory-task"
            mock_parse_task.return_value = mock_task_result
            
            # Create memory-intensive operations
            large_payload_size = 1000  # Large number of files per request
            num_requests = 50
            
            async def memory_intensive_request(request_id: int):
                """Create request with large payload."""
                try:
                    # Create large file list
                    file_urls = [f"https://storage.example.com/large-{request_id}-{i}.pdf" 
                                for i in range(large_payload_size)]
                    
                    start_time = time.time()
                    response = await client.post(
                        "/v1/tasks",
                        json={
                            "file_urls": file_urls,
                            "user_id": f"memory-user-{request_id}",
                            "options": {"enable_vectorization": False, "storage_policy": "temporary"}
                        }
                    )
                    end_time = time.time()
                    
                    return {
                        "request_id": request_id,
                        "success": response.status_code in [201, 400],  # 400 acceptable for oversized requests
                        "response_time": end_time - start_time,
                        "status_code": response.status_code
                    }
                
                except Exception as e:
                    return {
                        "request_id": request_id,
                        "success": False,
                        "response_time": 0,
                        "error": str(e)
                    }
            
            # Monitor memory usage
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Execute memory-intensive requests
            start_time = time.time()
            memory_tasks = [memory_intensive_request(i) for i in range(num_requests)]
            results = await asyncio.gather(*memory_tasks, return_exceptions=True)
            end_time = time.time()
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            # Analyze results
            successful_results = [r for r in results if isinstance(r, dict) and r["success"]]
            response_times = [r["response_time"] for r in successful_results if r["response_time"] > 0]
            
            success_rate = len(successful_results) / num_requests
            avg_response_time = statistics.mean(response_times) if response_times else 0
            
            print(f"Memory pressure load test:")
            print(f"  Large requests: {num_requests}")
            print(f"  Files per request: {large_payload_size}")
            print(f"  Success rate: {success_rate:.2%}")
            print(f"  Average response time: {avg_response_time:.3f}s")
            print(f"  Initial memory: {initial_memory:.2f}MB")
            print(f"  Final memory: {final_memory:.2f}MB")
            print(f"  Memory increase: {memory_increase:.2f}MB")
            
            # Memory and performance assertions
            assert memory_increase < 500, f"Memory increase should be <500MB, got {memory_increase:.2f}MB"
            assert success_rate > 0.80, f"Success rate should be >80% under memory pressure, got {success_rate:.2%}"
            
            # System should either handle large requests or reject them gracefully
            if avg_response_time > 0:
                assert avg_response_time < 30, f"Response time should be reasonable even under pressure, got {avg_response_time:.3f}s"

    @pytest.mark.asyncio
    @pytest.mark.load
    async def test_sustained_high_throughput(self, client):
        """Test sustained high throughput over extended period."""
        
        with patch('src.storage.policy.upload_file_to_storage') as mock_upload, \
             patch('workers.src.tasks.parsing.parse_document_task.delay') as mock_parse_task:
            
            mock_upload.return_value = "https://storage.example.com/throughput-test.pdf"
            mock_task_result = MagicMock()
            mock_task_result.id = "throughput-task"
            mock_parse_task.return_value = mock_task_result
            
            # Sustained load parameters
            target_rps = 10  # requests per second
            duration = 300   # 5 minutes
            total_expected = target_rps * duration
            
            completed_requests = 0
            failed_requests = 0
            response_times = []
            
            async def sustained_request_generator():
                """Generate requests at sustained rate."""
                nonlocal completed_requests, failed_requests
                
                request_id = 0
                start_time = time.time()
                
                while time.time() - start_time < duration:
                    batch_start = time.time()
                    
                    # Create batch of requests for this second
                    batch_tasks = []
                    for _ in range(target_rps):
                        request_id += 1
                        task = self.create_sustained_request(client, request_id)
                        batch_tasks.append(task)
                    
                    # Execute batch
                    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    
                    # Process results
                    for result in batch_results:
                        if isinstance(result, dict):
                            if result["success"]:
                                completed_requests += 1
                                response_times.append(result["response_time"])
                            else:
                                failed_requests += 1
                        else:
                            failed_requests += 1
                    
                    # Wait for next second
                    elapsed = time.time() - batch_start
                    if elapsed < 1.0:
                        await asyncio.sleep(1.0 - elapsed)
            
            # Run sustained load test
            await sustained_request_generator()
            
            # Calculate metrics
            total_requests = completed_requests + failed_requests
            success_rate = completed_requests / total_requests if total_requests > 0 else 0
            actual_rps = completed_requests / duration
            avg_response_time = statistics.mean(response_times) if response_times else 0
            p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else 0
            
            print(f"Sustained high throughput test:")
            print(f"  Target RPS: {target_rps}")
            print(f"  Duration: {duration}s")
            print(f"  Total requests: {total_requests}")
            print(f"  Completed requests: {completed_requests}")
            print(f"  Failed requests: {failed_requests}")
            print(f"  Success rate: {success_rate:.2%}")
            print(f"  Actual RPS: {actual_rps:.2f}")
            print(f"  Average response time: {avg_response_time:.3f}s")
            print(f"  95th percentile response time: {p95_response_time:.3f}s")
            
            # Performance assertions for sustained load
            assert success_rate > 0.95, f"Sustained success rate should be >95%, got {success_rate:.2%}"
            assert actual_rps > target_rps * 0.8, f"Should maintain >80% of target RPS, got {actual_rps:.2f}/{target_rps}"
            assert avg_response_time < 2.0, f"Average response time should be <2s under sustained load, got {avg_response_time:.3f}s"
            assert p95_response_time < 5.0, f"95th percentile should be <5s, got {p95_response_time:.3f}s"

    async def create_sustained_request(self, client, request_id: int):
        """Helper method to create individual sustained requests."""
        try:
            start_time = time.time()
            response = await client.post(
                "/v1/tasks",
                json={
                    "file_urls": [f"https://storage.example.com/sustained-{request_id}.pdf"],
                    "user_id": f"sustained-user-{request_id % 10}",
                    "options": {"enable_vectorization": request_id % 4 == 0, "storage_policy": "temporary"}
                }
            )
            end_time = time.time()
            
            return {
                "success": response.status_code == 201,
                "response_time": end_time - start_time,
                "status_code": response.status_code
            }
        except Exception:
            return {"success": False, "response_time": 0}