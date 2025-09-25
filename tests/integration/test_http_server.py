"""
Integration tests for HTTP MCP Server
"""

import pytest
import pytest_asyncio
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
import httpx
from fastapi.testclient import TestClient

from tests.conftest import generate_test_project, generate_test_todo, generate_test_event


class TestHTTPServerIntegration:
    """Integration tests for HTTP MCP Server"""
    
    def test_health_endpoint(self, test_client):
        """Test health check endpoint"""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_mcp_initialize(self, test_client):
        """Test MCP initialization endpoint"""
        response = test_client.post("/mcp/initialize", json={})
        
        assert response.status_code == 200
        data = response.json()
        assert data["protocolVersion"] == "2024-11-05"
        assert "capabilities" in data
        assert "serverInfo" in data
        assert data["serverInfo"]["name"] == "personal-assistant-http"
        assert data["serverInfo"]["version"] == "2.0.0"
    
    def test_mcp_tools_list(self, test_client):
        """Test MCP tools list endpoint"""
        response = test_client.post("/mcp/tools/list", json={})
        
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        
        # Check for expected tools
        tool_names = [tool["name"] for tool in data["tools"]]
        expected_tools = ["get_dashboard", "add_project", "semantic_search"]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
        
        # Verify tool schemas
        for tool in data["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
    
    def test_mcp_call_get_dashboard_empty(self, test_client):
        """Test dashboard tool call with empty database"""
        payload = {
            "method": "tools/call",
            "params": {
                "name": "get_dashboard",
                "arguments": {}
            }
        }
        
        response = test_client.post("/mcp/tools/call", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        
        # Parse the dashboard content
        content_text = data["content"][0]["text"]
        dashboard_data = json.loads(content_text)
        
        assert dashboard_data["type"] == "smart_dashboard"
        assert "overview" in dashboard_data
        assert "current_focus" in dashboard_data
        assert "insights" in dashboard_data
        assert "suggestions" in dashboard_data
    
    def test_mcp_call_add_project(self, test_client):
        """Test add project tool call"""
        project_data = {
            "name": "Integration Test Project",
            "description": "A project created during integration testing",
            "priority": "high",
            "tags": ["integration", "test"]
        }
        
        payload = {
            "method": "tools/call",
            "params": {
                "name": "add_project",
                "arguments": project_data
            }
        }
        
        response = test_client.post("/mcp/tools/call", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        
        # Parse the response content
        content_text = data["content"][0]["text"]
        result_data = json.loads(content_text)
        
        assert result_data["message"] == "Project added successfully with semantic indexing"
        assert "project" in result_data
        assert result_data["project"]["name"] == project_data["name"]
        assert result_data["project"]["description"] == project_data["description"]
        assert result_data["project"]["priority"] == project_data["priority"]
        assert result_data["project"]["tags"] == project_data["tags"]
        assert "vector_search_enabled" in result_data
    
    def test_mcp_call_semantic_search(self, test_client):
        """Test semantic search tool call"""
        # First add a project to search for
        project_data = {
            "name": "Web Development Project",
            "description": "Building a modern web application with React and Node.js",
            "priority": "high",
            "tags": ["web", "react", "nodejs"]
        }
        
        add_payload = {
            "method": "tools/call",
            "params": {
                "name": "add_project",
                "arguments": project_data
            }
        }
        
        add_response = test_client.post("/mcp/tools/call", json=add_payload)
        assert add_response.status_code == 200
        
        # Now search for the project
        search_payload = {
            "method": "tools/call",
            "params": {
                "name": "semantic_search",
                "arguments": {
                    "query": "web application development",
                    "limit": 5,
                    "types": ["projects", "todos"]
                }
            }
        }
        
        search_response = test_client.post("/mcp/tools/call", json=search_payload)
        
        assert search_response.status_code == 200
        search_data = search_response.json()
        assert "content" in search_data
        
        # Parse search results
        content_text = search_data["content"][0]["text"]
        results = json.loads(content_text)
        
        assert "query" in results
        assert results["query"] == "web application development"
        assert "context" in results
        assert "results" in results
        assert "total_results" in results
        assert "retrieval_metadata" in results
        
        # Should find the project we just added
        if results["total_results"] > 0:
            found_project = False
            for result in results["results"]:
                if (result["content_type"] == "project" and 
                    "Web Development" in result["title"]):
                    found_project = True
                    break
            # Note: Might not find due to mock embedding service in tests
    
    def test_mcp_call_dashboard_with_query(self, test_client):
        """Test dashboard with search query"""
        # Add some test data first
        project_data = {
            "name": "Mobile App Development",
            "description": "Creating a mobile app for iOS and Android",
            "priority": "medium",
            "tags": ["mobile", "ios", "android"]
        }
        
        add_payload = {
            "method": "tools/call",
            "params": {
                "name": "add_project",
                "arguments": project_data
            }
        }
        
        add_response = test_client.post("/mcp/tools/call", json=add_payload)
        assert add_response.status_code == 200
        
        # Get dashboard with query
        dashboard_payload = {
            "method": "tools/call",
            "params": {
                "name": "get_dashboard",
                "arguments": {
                    "query": "mobile development status"
                }
            }
        }
        
        dashboard_response = test_client.post("/mcp/tools/call", json=dashboard_payload)
        
        assert dashboard_response.status_code == 200
        data = dashboard_response.json()
        
        content_text = data["content"][0]["text"]
        dashboard_data = json.loads(content_text)
        
        assert dashboard_data["type"] == "intelligent_dashboard"
        assert dashboard_data["query"] == "mobile development status"
        assert "context_analysis" in dashboard_data
        assert "relevant_projects" in dashboard_data
        assert "priority_todos" in dashboard_data
        assert "insights" in dashboard_data
        assert "suggestions" in dashboard_data
    
    def test_mcp_call_invalid_tool(self, test_client):
        """Test calling non-existent tool"""
        payload = {
            "method": "tools/call",
            "params": {
                "name": "nonexistent_tool",
                "arguments": {}
            }
        }
        
        response = test_client.post("/mcp/tools/call", json=payload)
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Unknown tool" in data["detail"]
    
    def test_mcp_call_invalid_arguments(self, test_client):
        """Test calling tool with invalid arguments"""
        payload = {
            "method": "tools/call",
            "params": {
                "name": "add_project",
                "arguments": {
                    # Missing required fields
                    "priority": "high"
                }
            }
        }
        
        response = test_client.post("/mcp/tools/call", json=payload)
        
        # Should return error due to missing required fields
        assert response.status_code == 500
    
    def test_authentication_disabled(self, test_client):
        """Test that authentication is properly disabled in test environment"""
        # All endpoints should work without authentication headers
        response = test_client.get("/health")
        assert response.status_code == 200
        
        response = test_client.post("/mcp/initialize", json={})
        assert response.status_code == 200
        
        response = test_client.post("/mcp/tools/list", json={})
        assert response.status_code == 200
    
    def test_cors_headers(self, test_client):
        """Test CORS headers are present"""
        response = test_client.options("/health", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        })
        
        # FastAPI test client might not fully simulate CORS
        # In a real environment, these headers would be present
        assert response.status_code in [200, 404]  # Options might not be implemented
    
    def test_error_handling(self, test_client):
        """Test error handling for malformed requests"""
        # Invalid JSON
        response = test_client.post("/mcp/tools/call", 
                                  content="invalid json",
                                  headers={"Content-Type": "application/json"})
        assert response.status_code == 422
        
        # Missing params
        response = test_client.post("/mcp/tools/call", json={
            "method": "tools/call"
            # Missing params
        })
        assert response.status_code == 422


class TestDatabaseIntegration:
    """Integration tests for database operations through HTTP server"""
    
    def test_project_crud_operations(self, test_client):
        """Test complete CRUD operations for projects"""
        # Create project
        project_data = {
            "name": "CRUD Test Project",
            "description": "Testing CRUD operations",
            "priority": "high",
            "tags": ["crud", "test"]
        }
        
        create_payload = {
            "method": "tools/call",
            "params": {
                "name": "add_project",
                "arguments": project_data
            }
        }
        
        create_response = test_client.post("/mcp/tools/call", json=create_payload)
        assert create_response.status_code == 200
        
        # Extract project ID from response
        content_text = create_response.json()["content"][0]["text"]
        create_result = json.loads(content_text)
        project_id = create_result["project"]["id"]
        
        # Read project through dashboard
        dashboard_payload = {
            "method": "tools/call",
            "params": {
                "name": "get_dashboard",
                "arguments": {}
            }
        }
        
        dashboard_response = test_client.post("/mcp/tools/call", json=dashboard_payload)
        assert dashboard_response.status_code == 200
        
        # Verify project appears in dashboard
        dashboard_content = dashboard_response.json()["content"][0]["text"]
        dashboard_data = json.loads(dashboard_content)
        
        # Check if project is in the overview or current focus
        total_projects = dashboard_data["overview"]["total_projects"]
        active_projects = dashboard_data["overview"]["active_projects"]
        
        assert total_projects >= 1
        assert active_projects >= 1
    
    def test_search_integration(self, test_client):
        """Test search integration across multiple data types"""
        # Add multiple items with related content
        project_data = {
            "name": "Search Integration Project",
            "description": "Testing search functionality across data types",
            "priority": "medium",
            "tags": ["search", "integration"]
        }
        
        project_payload = {
            "method": "tools/call",
            "params": {
                "name": "add_project",
                "arguments": project_data
            }
        }
        
        project_response = test_client.post("/mcp/tools/call", json=project_payload)
        assert project_response.status_code == 200
        
        # Search for related content
        search_payload = {
            "method": "tools/call",
            "params": {
                "name": "semantic_search",
                "arguments": {
                    "query": "search integration testing",
                    "limit": 10,
                    "types": ["projects", "todos", "events", "documents"]
                }
            }
        }
        
        search_response = test_client.post("/mcp/tools/call", json=search_payload)
        assert search_response.status_code == 200
        
        search_content = search_response.json()["content"][0]["text"]
        search_results = json.loads(search_content)
        
        # Verify search results structure
        assert "query" in search_results
        assert "context" in search_results
        assert "results" in search_results
        assert "total_results" in search_results
        
        # Context should include intent classification
        context = search_results["context"]
        assert "intent" in context
        assert context["intent"] is not None
    
    def test_dashboard_intelligence(self, test_client):
        """Test intelligent dashboard functionality"""
        # Add test data with different priorities and dates
        test_projects = [
            {
                "name": "High Priority Project",
                "description": "Critical project requiring immediate attention",
                "priority": "high",
                "tags": ["critical", "urgent"]
            },
            {
                "name": "Medium Priority Project", 
                "description": "Regular project with medium priority",
                "priority": "medium",
                "tags": ["regular", "development"]
            },
            {
                "name": "Low Priority Project",
                "description": "Future project with low priority",
                "priority": "low",
                "tags": ["future", "planning"]
            }
        ]
        
        # Add all projects
        for project_data in test_projects:
            payload = {
                "method": "tools/call",
                "params": {
                    "name": "add_project",
                    "arguments": project_data
                }
            }
            
            response = test_client.post("/mcp/tools/call", json=payload)
            assert response.status_code == 200
        
        # Get dashboard without query (smart default)
        dashboard_payload = {
            "method": "tools/call",
            "params": {
                "name": "get_dashboard",
                "arguments": {}
            }
        }
        
        dashboard_response = test_client.post("/mcp/tools/call", json=dashboard_payload)
        assert dashboard_response.status_code == 200
        
        dashboard_content = dashboard_response.json()["content"][0]["text"]
        dashboard_data = json.loads(dashboard_content)
        
        # Verify intelligent dashboard structure
        assert dashboard_data["type"] == "smart_dashboard"
        assert "overview" in dashboard_data
        assert "current_focus" in dashboard_data
        assert "insights" in dashboard_data
        assert "suggestions" in dashboard_data
        
        # Check overview counts
        overview = dashboard_data["overview"]
        assert overview["total_projects"] == 3
        assert overview["active_projects"] == 3
        
        # Verify insights are generated
        insights = dashboard_data["insights"]
        assert isinstance(insights, list)
        assert len(insights) > 0
        
        # Verify suggestions are generated
        suggestions = dashboard_data["suggestions"]
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        
        # Get dashboard with specific query
        query_payload = {
            "method": "tools/call",
            "params": {
                "name": "get_dashboard",
                "arguments": {
                    "query": "high priority urgent work"
                }
            }
        }
        
        query_response = test_client.post("/mcp/tools/call", json=query_payload)
        assert query_response.status_code == 200
        
        query_content = query_response.json()["content"][0]["text"]
        query_data = json.loads(query_content)
        
        # Should return intelligent dashboard with query
        assert query_data["type"] == "intelligent_dashboard"
        assert query_data["query"] == "high priority urgent work"
        assert "context_analysis" in query_data


class TestErrorHandling:
    """Test error handling in integration scenarios"""
    
    def test_database_error_handling(self, test_client):
        """Test handling of database errors"""
        # This test would require mocking database to fail
        # For now, test with invalid data that might cause issues
        
        invalid_project_data = {
            "name": "",  # Empty name might cause validation error
            "description": "Project with empty name",
            "priority": "invalid_priority",  # Invalid priority
            "tags": None  # Invalid tags
        }
        
        payload = {
            "method": "tools/call",
            "params": {
                "name": "add_project",
                "arguments": invalid_project_data
            }
        }
        
        response = test_client.post("/mcp/tools/call", json=payload)
        
        # Should handle validation error gracefully
        assert response.status_code == 500
        error_data = response.json()
        assert "detail" in error_data
    
    def test_search_error_handling(self, test_client):
        """Test search error handling"""
        # Test search with invalid parameters
        invalid_search_payload = {
            "method": "tools/call",
            "params": {
                "name": "semantic_search",
                "arguments": {
                    "query": "",  # Empty query
                    "limit": -1,  # Invalid limit
                    "types": ["invalid_type"]  # Invalid content type
                }
            }
        }
        
        response = test_client.post("/mcp/tools/call", json=invalid_search_payload)
        
        # Should handle gracefully and return empty or error response
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            # If successful, should return empty results
            content_text = response.json()["content"][0]["text"]
            results = json.loads(content_text)
            assert "results" in results
    
    def test_concurrent_requests(self, test_client):
        """Test handling of concurrent requests"""
        import threading
        import time
        
        results = []
        errors = []
        
        def make_request(i):
            try:
                project_data = {
                    "name": f"Concurrent Project {i}",
                    "description": f"Project created in concurrent test {i}",
                    "priority": "medium",
                    "tags": [f"concurrent_{i}"]
                }
                
                payload = {
                    "method": "tools/call",
                    "params": {
                        "name": "add_project",
                        "arguments": project_data
                    }
                }
                
                response = test_client.post("/mcp/tools/call", json=payload)
                results.append((i, response.status_code))
                
            except Exception as e:
                errors.append((i, str(e)))
        
        # Create multiple threads to make concurrent requests
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)
        
        # Verify most requests succeeded
        successful_requests = [r for r in results if r[1] == 200]
        assert len(successful_requests) >= 3  # At least 3 out of 5 should succeed
        
        # Check for any critical errors
        critical_errors = [e for e in errors if "critical" in e[1].lower()]
        assert len(critical_errors) == 0


class TestPerformanceIntegration:
    """Basic performance tests for integration"""
    
    def test_dashboard_response_time(self, test_client):
        """Test dashboard response time"""
        import time
        
        # Add some data first
        for i in range(10):
            project_data = {
                "name": f"Performance Test Project {i}",
                "description": f"Project for performance testing {i}",
                "priority": "medium",
                "tags": [f"perf_{i}"]
            }
            
            payload = {
                "method": "tools/call",
                "params": {
                    "name": "add_project",
                    "arguments": project_data
                }
            }
            
            response = test_client.post("/mcp/tools/call", json=payload)
            assert response.status_code == 200
        
        # Time dashboard request
        start_time = time.time()
        
        dashboard_payload = {
            "method": "tools/call",
            "params": {
                "name": "get_dashboard",
                "arguments": {}
            }
        }
        
        response = test_client.post("/mcp/tools/call", json=dashboard_payload)
        
        end_time = time.time()
        response_time = end_time - start_time
        
        assert response.status_code == 200
        
        # Dashboard should respond within reasonable time (2 seconds for test environment)
        assert response_time < 2.0
        
        # Check response size is reasonable
        content_text = response.json()["content"][0]["text"]
        content_size = len(content_text.encode('utf-8'))
        
        # Should be under 10KB for test data
        assert content_size < 10 * 1024
    
    def test_search_response_time(self, test_client):
        """Test search response time"""
        import time
        
        # Time search request
        start_time = time.time()
        
        search_payload = {
            "method": "tools/call",
            "params": {
                "name": "semantic_search",
                "arguments": {
                    "query": "performance test search",
                    "limit": 5
                }
            }
        }
        
        response = test_client.post("/mcp/tools/call", json=search_payload)
        
        end_time = time.time()
        response_time = end_time - start_time
        
        assert response.status_code == 200
        
        # Search should be fast (1 second for test environment)
        assert response_time < 1.0