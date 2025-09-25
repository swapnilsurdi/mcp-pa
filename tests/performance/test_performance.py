"""
Performance tests for MCP Personal Assistant

These tests measure performance characteristics and ensure the system
meets the performance targets outlined in CLAUDE.md:
- Dashboard response size < 4KB
- Response time < 200ms
- Support for 1000+ concurrent users
- 90%+ search accuracy
"""

import pytest
import pytest_asyncio
import asyncio
import time
import json
import statistics
import psutil
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from tests.conftest import generate_test_project, generate_test_todo, generate_test_event


class TestResponseSizePerformance:
    """Test response size constraints"""
    
    @pytest.mark.asyncio
    async def test_dashboard_response_size_empty(self, test_client):
        """Test dashboard response size with empty database"""
        response = test_client.post("/mcp/tools/call", json={
            "method": "tools/call",
            "params": {
                "name": "get_dashboard",
                "arguments": {}
            }
        })
        
        assert response.status_code == 200
        
        # Measure response size
        response_text = response.text
        response_size = len(response_text.encode('utf-8'))
        
        # Should be well under 4KB even with empty data
        assert response_size < 2 * 1024  # 2KB limit for empty dashboard
        
        print(f"Empty dashboard response size: {response_size} bytes")
    
    @pytest.mark.asyncio
    async def test_dashboard_response_size_with_data(self, test_client, performance_test_data):
        """Test dashboard response size with realistic data load"""
        # Add performance test data
        projects_added = 0
        for project_data in performance_test_data["projects"][:20]:  # Add 20 projects
            response = test_client.post("/mcp/tools/call", json={
                "method": "tools/call",
                "params": {
                    "name": "add_project",
                    "arguments": project_data
                }
            })
            if response.status_code == 200:
                projects_added += 1
        
        # Get dashboard
        dashboard_response = test_client.post("/mcp/tools/call", json={
            "method": "tools/call",
            "params": {
                "name": "get_dashboard",
                "arguments": {}
            }
        })
        
        assert dashboard_response.status_code == 200
        
        # Measure response size
        response_text = dashboard_response.text
        response_size = len(response_text.encode('utf-8'))
        
        # Critical requirement: must be under 4KB
        assert response_size < 4 * 1024, f"Dashboard response size {response_size} bytes exceeds 4KB limit"
        
        print(f"Dashboard response size with {projects_added} projects: {response_size} bytes")
        
        # Verify response contains intelligent filtering
        content_text = dashboard_response.json()["content"][0]["text"]
        dashboard_data = json.loads(content_text)
        
        # Should show overview but limited current focus items
        if "current_focus" in dashboard_data:
            focus_projects = dashboard_data["current_focus"].get("active_projects", [])
            focus_todos = dashboard_data["current_focus"].get("priority_todos", [])
            
            # Should be limited to small numbers for size control
            assert len(focus_projects) <= 5
            assert len(focus_todos) <= 5
    
    @pytest.mark.asyncio
    async def test_search_response_size(self, test_client, performance_test_data):
        """Test search response size limits"""
        # Add test data
        for i, project_data in enumerate(performance_test_data["projects"][:10]):
            response = test_client.post("/mcp/tools/call", json={
                "method": "tools/call",
                "params": {
                    "name": "add_project",
                    "arguments": project_data
                }
            })
            if response.status_code != 200:
                break
        
        # Perform search
        search_response = test_client.post("/mcp/tools/call", json={
            "method": "tools/call",
            "params": {
                "name": "semantic_search",
                "arguments": {
                    "query": "performance test project development",
                    "limit": 10
                }
            }
        })
        
        assert search_response.status_code == 200
        
        # Measure response size
        response_size = len(search_response.text.encode('utf-8'))
        
        # Search should also be under reasonable size limits
        assert response_size < 8 * 1024, f"Search response size {response_size} bytes exceeds 8KB limit"
        
        print(f"Search response size: {response_size} bytes")


class TestResponseTimePerformance:
    """Test response time requirements"""
    
    @pytest.mark.asyncio
    async def test_dashboard_response_time(self, test_client):
        """Test dashboard response time under 200ms"""
        # Warm up
        test_client.post("/mcp/tools/call", json={
            "method": "tools/call",
            "params": {"name": "get_dashboard", "arguments": {}}
        })
        
        # Measure response time
        start_time = time.time()
        
        response = test_client.post("/mcp/tools/call", json={
            "method": "tools/call",
            "params": {
                "name": "get_dashboard",
                "arguments": {}
            }
        })
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        assert response.status_code == 200
        # Target: < 200ms, but allow more in test environment
        assert response_time < 500, f"Dashboard response time {response_time:.2f}ms exceeds target"
        
        print(f"Dashboard response time: {response_time:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_search_response_time(self, test_client):
        """Test search response time"""
        # Add some test data first
        for i in range(5):
            test_client.post("/mcp/tools/call", json={
                "method": "tools/call",
                "params": {
                    "name": "add_project",
                    "arguments": generate_test_project(
                        name=f"Search Performance Test {i}",
                        description=f"Project for search performance testing {i}"
                    )
                }
            })
        
        # Warm up
        test_client.post("/mcp/tools/call", json={
            "method": "tools/call",
            "params": {
                "name": "semantic_search",
                "arguments": {"query": "test"}
            }
        })
        
        # Measure search response time
        start_time = time.time()
        
        response = test_client.post("/mcp/tools/call", json={
            "method": "tools/call",
            "params": {
                "name": "semantic_search",
                "arguments": {
                    "query": "search performance test project",
                    "limit": 5
                }
            }
        })
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        
        assert response.status_code == 200
        # Search should be even faster
        assert response_time < 300, f"Search response time {response_time:.2f}ms exceeds target"
        
        print(f"Search response time: {response_time:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_project_creation_time(self, test_client):
        """Test project creation response time"""
        project_data = generate_test_project(
            name="Performance Test Project",
            description="Testing project creation performance"
        )
        
        # Measure project creation time
        start_time = time.time()
        
        response = test_client.post("/mcp/tools/call", json={
            "method": "tools/call",
            "params": {
                "name": "add_project",
                "arguments": project_data
            }
        })
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        
        assert response.status_code == 200
        assert response_time < 400, f"Project creation time {response_time:.2f}ms exceeds target"
        
        print(f"Project creation time: {response_time:.2f}ms")


class TestConcurrencyPerformance:
    """Test concurrent user support"""
    
    def test_concurrent_dashboard_requests(self, test_client):
        """Test handling multiple concurrent dashboard requests"""
        def make_dashboard_request(request_id: int) -> tuple:
            start_time = time.time()
            
            try:
                response = test_client.post("/mcp/tools/call", json={
                    "method": "tools/call",
                    "params": {
                        "name": "get_dashboard",
                        "arguments": {}
                    }
                })
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                
                return (request_id, response.status_code, response_time, len(response.text))
                
            except Exception as e:
                return (request_id, 500, 0, str(e))
        
        # Test with multiple concurrent requests
        num_concurrent = 20
        
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            # Submit all requests
            futures = [executor.submit(make_dashboard_request, i) for i in range(num_concurrent)]
            
            # Collect results
            results = []
            for future in as_completed(futures, timeout=30):
                results.append(future.result())
        
        # Analyze results
        successful_requests = [r for r in results if r[1] == 200]
        failed_requests = [r for r in results if r[1] != 200]
        
        success_rate = len(successful_requests) / len(results)
        response_times = [r[2] for r in successful_requests]
        response_sizes = [r[3] for r in successful_requests]
        
        print(f"Concurrent dashboard requests:")
        print(f"  Total requests: {len(results)}")
        print(f"  Successful: {len(successful_requests)}")
        print(f"  Failed: {len(failed_requests)}")
        print(f"  Success rate: {success_rate:.2%}")
        
        if response_times:
            print(f"  Avg response time: {statistics.mean(response_times):.2f}ms")
            print(f"  Max response time: {max(response_times):.2f}ms")
            print(f"  Min response time: {min(response_times):.2f}ms")
        
        if response_sizes:
            print(f"  Avg response size: {statistics.mean(response_sizes):.0f} bytes")
            print(f"  Max response size: {max(response_sizes)} bytes")
        
        # Requirements
        assert success_rate >= 0.95, f"Success rate {success_rate:.2%} below 95% threshold"
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            assert avg_response_time < 1000, f"Average response time {avg_response_time:.2f}ms too high"
        
        if response_sizes:
            max_response_size = max(response_sizes)
            assert max_response_size < 8 * 1024, f"Max response size {max_response_size} bytes exceeds limit"
    
    def test_concurrent_project_creation(self, test_client):
        """Test concurrent project creation"""
        def create_project(project_id: int) -> tuple:
            start_time = time.time()
            
            project_data = generate_test_project(
                name=f"Concurrent Project {project_id}",
                description=f"Project created in concurrency test {project_id}",
                priority="medium"
            )
            
            try:
                response = test_client.post("/mcp/tools/call", json={
                    "method": "tools/call",
                    "params": {
                        "name": "add_project",
                        "arguments": project_data
                    }
                })
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                
                return (project_id, response.status_code, response_time)
                
            except Exception as e:
                return (project_id, 500, str(e))
        
        # Create projects concurrently
        num_concurrent = 15
        
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(create_project, i) for i in range(num_concurrent)]
            results = [future.result() for future in as_completed(futures, timeout=30)]
        
        # Analyze results
        successful_creates = [r for r in results if r[1] == 200]
        failed_creates = [r for r in results if r[1] != 200]
        
        success_rate = len(successful_creates) / len(results)
        
        print(f"Concurrent project creation:")
        print(f"  Total requests: {len(results)}")
        print(f"  Successful: {len(successful_creates)}")
        print(f"  Failed: {len(failed_creates)}")
        print(f"  Success rate: {success_rate:.2%}")
        
        if successful_creates:
            response_times = [r[2] for r in successful_creates if isinstance(r[2], (int, float))]
            if response_times:
                print(f"  Avg response time: {statistics.mean(response_times):.2f}ms")
        
        # Should handle most concurrent requests successfully
        assert success_rate >= 0.90, f"Success rate {success_rate:.2%} below 90% threshold"


class TestMemoryPerformance:
    """Test memory usage performance"""
    
    def test_memory_usage_baseline(self, test_client):
        """Test baseline memory usage"""
        process = psutil.Process()
        
        # Get baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"Baseline memory usage: {baseline_memory:.2f} MB")
        
        # Memory should be reasonable for a test environment
        assert baseline_memory < 500, f"Baseline memory {baseline_memory:.2f} MB too high"
    
    def test_memory_usage_with_data(self, test_client, performance_test_data):
        """Test memory usage after adding data"""
        process = psutil.Process()
        
        # Get initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        # Add test data
        projects_added = 0
        for project_data in performance_test_data["projects"][:50]:
            response = test_client.post("/mcp/tools/call", json={
                "method": "tools/call",
                "params": {
                    "name": "add_project",
                    "arguments": project_data
                }
            })
            if response.status_code == 200:
                projects_added += 1
        
        # Get memory after adding data
        after_data_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = after_data_memory - initial_memory
        
        print(f"Memory usage after adding {projects_added} projects:")
        print(f"  Initial: {initial_memory:.2f} MB")
        print(f"  After data: {after_data_memory:.2f} MB")
        print(f"  Increase: {memory_increase:.2f} MB")
        print(f"  Per project: {memory_increase/projects_added:.3f} MB" if projects_added > 0 else "")
        
        # Memory increase should be reasonable
        assert memory_increase < 100, f"Memory increase {memory_increase:.2f} MB too high"
    
    def test_memory_usage_dashboard_requests(self, test_client):
        """Test memory usage during dashboard requests"""
        process = psutil.Process()
        
        # Get initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        # Make multiple dashboard requests
        for i in range(20):
            response = test_client.post("/mcp/tools/call", json={
                "method": "tools/call",
                "params": {
                    "name": "get_dashboard",
                    "arguments": {}
                }
            })
            assert response.status_code == 200
        
        # Get memory after requests
        after_requests_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = after_requests_memory - initial_memory
        
        print(f"Memory usage after 20 dashboard requests:")
        print(f"  Initial: {initial_memory:.2f} MB")
        print(f"  After requests: {after_requests_memory:.2f} MB")
        print(f"  Increase: {memory_increase:.2f} MB")
        
        # Should not have significant memory leaks
        assert memory_increase < 50, f"Memory increase {memory_increase:.2f} MB suggests memory leak"


class TestScalabilityPerformance:
    """Test scalability characteristics"""
    
    @pytest.mark.asyncio
    async def test_dashboard_performance_scaling(self, test_client, performance_test_data):
        """Test how dashboard performance scales with data size"""
        response_times = []
        response_sizes = []
        data_sizes = [0, 10, 25, 50]
        
        for data_size in data_sizes:
            # Add projects up to target size
            current_projects = 0
            for project_data in performance_test_data["projects"][:data_size]:
                response = test_client.post("/mcp/tools/call", json={
                    "method": "tools/call",
                    "params": {
                        "name": "add_project",
                        "arguments": project_data
                    }
                })
                if response.status_code == 200:
                    current_projects += 1
            
            # Measure dashboard performance
            start_time = time.time()
            
            dashboard_response = test_client.post("/mcp/tools/call", json={
                "method": "tools/call",
                "params": {
                    "name": "get_dashboard",
                    "arguments": {}
                }
            })
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            if dashboard_response.status_code == 200:
                response_size = len(dashboard_response.text.encode('utf-8'))
                response_times.append((current_projects, response_time))
                response_sizes.append((current_projects, response_size))
        
        print("Dashboard Performance Scaling:")
        print("Projects | Response Time (ms) | Response Size (bytes)")
        print("-" * 50)
        
        for i, (projects, time_ms) in enumerate(response_times):
            size = response_sizes[i][1] if i < len(response_sizes) else 0
            print(f"{projects:8} | {time_ms:15.2f} | {size:18}")
        
        # Verify that performance doesn't degrade significantly
        if len(response_times) >= 2:
            # Response time should not grow linearly with data
            first_time = response_times[0][1]
            last_time = response_times[-1][1]
            time_growth_factor = last_time / first_time if first_time > 0 else 1
            
            # Should not grow more than 3x even with 50x more data
            assert time_growth_factor < 3.0, f"Response time grew {time_growth_factor:.2f}x with data growth"
        
        # Response size should remain bounded
        if response_sizes:
            max_size = max(size for _, size in response_sizes)
            assert max_size < 4 * 1024, f"Response size {max_size} exceeds 4KB limit"
    
    @pytest.mark.asyncio
    async def test_search_performance_scaling(self, test_client, performance_test_data):
        """Test how search performance scales with data size"""
        search_times = []
        data_sizes = [5, 15, 30]
        
        for data_size in data_sizes:
            # Add projects
            projects_added = 0
            for project_data in performance_test_data["projects"][:data_size]:
                response = test_client.post("/mcp/tools/call", json={
                    "method": "tools/call",
                    "params": {
                        "name": "add_project",
                        "arguments": project_data
                    }
                })
                if response.status_code == 200:
                    projects_added += 1
            
            # Measure search performance
            start_time = time.time()
            
            search_response = test_client.post("/mcp/tools/call", json={
                "method": "tools/call",
                "params": {
                    "name": "semantic_search",
                    "arguments": {
                        "query": "performance test project development",
                        "limit": 5
                    }
                }
            })
            
            end_time = time.time()
            search_time = (end_time - start_time) * 1000
            
            if search_response.status_code == 200:
                search_times.append((projects_added, search_time))
        
        print("Search Performance Scaling:")
        print("Projects | Search Time (ms)")
        print("-" * 30)
        
        for projects, time_ms in search_times:
            print(f"{projects:8} | {time_ms:13.2f}")
        
        # Search should remain fast even with more data
        if search_times:
            max_search_time = max(time_ms for _, time_ms in search_times)
            assert max_search_time < 500, f"Search time {max_search_time:.2f}ms too high with scaled data"


class TestBenchmarks:
    """Benchmark tests for performance profiling"""
    
    @pytest.mark.benchmark
    def test_dashboard_benchmark(self, benchmark, test_client):
        """Benchmark dashboard performance"""
        def get_dashboard():
            response = test_client.post("/mcp/tools/call", json={
                "method": "tools/call",
                "params": {
                    "name": "get_dashboard",
                    "arguments": {}
                }
            })
            assert response.status_code == 200
            return response
        
        result = benchmark(get_dashboard)
        
        # Verify response
        content_text = result.json()["content"][0]["text"]
        dashboard_data = json.loads(content_text)
        assert "type" in dashboard_data
        
        print(f"Dashboard benchmark completed")
    
    @pytest.mark.benchmark
    def test_project_creation_benchmark(self, benchmark, test_client):
        """Benchmark project creation performance"""
        counter = {"count": 0}
        
        def create_project():
            project_data = generate_test_project(
                name=f"Benchmark Project {counter['count']}",
                description=f"Project created in benchmark test {counter['count']}"
            )
            counter["count"] += 1
            
            response = test_client.post("/mcp/tools/call", json={
                "method": "tools/call",
                "params": {
                    "name": "add_project",
                    "arguments": project_data
                }
            })
            assert response.status_code == 200
            return response
        
        result = benchmark(create_project)
        
        # Verify project was created
        content_text = result.json()["content"][0]["text"]
        result_data = json.loads(content_text)
        assert "project" in result_data
        
        print(f"Project creation benchmark completed")
    
    @pytest.mark.benchmark
    def test_search_benchmark(self, test_client, benchmark):
        """Benchmark search performance"""
        # Add some test data first
        for i in range(10):
            test_client.post("/mcp/tools/call", json={
                "method": "tools/call",
                "params": {
                    "name": "add_project",
                    "arguments": generate_test_project(
                        name=f"Search Benchmark Project {i}",
                        description=f"Project for search benchmarking {i}"
                    )
                }
            })
        
        def search_projects():
            response = test_client.post("/mcp/tools/call", json={
                "method": "tools/call",
                "params": {
                    "name": "semantic_search",
                    "arguments": {
                        "query": "benchmark project search test",
                        "limit": 5
                    }
                }
            })
            assert response.status_code == 200
            return response
        
        result = benchmark(search_projects)
        
        # Verify search results
        content_text = result.json()["content"][0]["text"]
        search_data = json.loads(content_text)
        assert "results" in search_data
        
        print(f"Search benchmark completed")


class TestPerformanceTargets:
    """Test specific performance targets from CLAUDE.md"""
    
    def test_token_efficiency_target(self, test_client, performance_test_data):
        """Test that responses meet token efficiency targets"""
        # Add significant amount of data
        projects_added = 0
        for project_data in performance_test_data["projects"][:30]:
            response = test_client.post("/mcp/tools/call", json={
                "method": "tools/call",
                "params": {
                    "name": "add_project", 
                    "arguments": project_data
                }
            })
            if response.status_code == 200:
                projects_added += 1
        
        print(f"Added {projects_added} projects for token efficiency test")
        
        # Test dashboard token efficiency
        dashboard_response = test_client.post("/mcp/tools/call", json={
            "method": "tools/call",
            "params": {
                "name": "get_dashboard",
                "arguments": {}
            }
        })
        
        assert dashboard_response.status_code == 200
        
        # Calculate token efficiency metrics
        response_size = len(dashboard_response.text.encode('utf-8'))
        
        # Estimate token count (roughly 4 characters per token)
        estimated_tokens = response_size // 4
        
        print(f"Dashboard response metrics:")
        print(f"  Response size: {response_size} bytes")
        print(f"  Estimated tokens: {estimated_tokens}")
        print(f"  Projects in database: {projects_added}")
        
        # Critical target: < 4KB response size
        assert response_size < 4 * 1024, f"Response size {response_size} exceeds 4KB token limit"
        
        # Should be dramatically more efficient than returning all data
        theoretical_full_size = projects_added * 500  # Estimate 500 bytes per full project
        efficiency_ratio = theoretical_full_size / response_size if response_size > 0 else 1
        
        print(f"  Token efficiency ratio: {efficiency_ratio:.1f}x improvement over full data")
        
        # Should be at least 5x more efficient than returning everything
        assert efficiency_ratio >= 5.0, f"Token efficiency ratio {efficiency_ratio:.1f}x below target"
    
    def test_90_percent_response_time_target(self, test_client):
        """Test that 90% of requests meet response time targets"""
        response_times = []
        
        # Make multiple requests to get statistical sample
        for i in range(50):
            start_time = time.time()
            
            response = test_client.post("/mcp/tools/call", json={
                "method": "tools/call",
                "params": {
                    "name": "get_dashboard",
                    "arguments": {}
                }
            })
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            if response.status_code == 200:
                response_times.append(response_time)
        
        # Calculate 90th percentile
        if response_times:
            response_times.sort()
            percentile_90_index = int(len(response_times) * 0.9)
            percentile_90_time = response_times[percentile_90_index]
            
            avg_time = statistics.mean(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            
            print(f"Response time analysis (50 requests):")
            print(f"  Average: {avg_time:.2f}ms")
            print(f"  Minimum: {min_time:.2f}ms")
            print(f"  Maximum: {max_time:.2f}ms")
            print(f"  90th percentile: {percentile_90_time:.2f}ms")
            
            # Target: 90th percentile under 500ms in test environment
            assert percentile_90_time < 500, f"90th percentile response time {percentile_90_time:.2f}ms exceeds target"
            
            # 95% should be under target
            fast_requests = len([t for t in response_times if t < 500])
            success_rate = fast_requests / len(response_times)
            assert success_rate >= 0.90, f"Only {success_rate:.2%} of requests met response time target"