"""
Test configuration and fixtures for MCP Personal Assistant tests
"""

import asyncio
import os
import tempfile
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock
import uuid
import json

# Import test dependencies
import httpx
from fastapi.testclient import TestClient

# Import application modules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.http_config import Config
from src.http_server import PersonalAssistantHTTPServer
from src.auth_service import UserContext, AuthService
from src.embedding_service import EmbeddingService
from src.intelligent_retrieval import IntelligentRetrievalService
from src.database_factory import DatabaseFactory
from src.models import Project, Todo, CalendarEvent, StatusEntry, PersonalData

# Test configuration
TEST_DATABASE_URL = "sqlite:///:memory:"
TEST_EMBEDDING_DIMENSION = 384

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def test_config(temp_dir):
    """Create test configuration."""
    return Config(
        database_type="sqlite",
        database_path=os.path.join(temp_dir, "test.db"),
        environment="testing",
        debug=True,
        auth=Config.AuthConfig(enabled=False),
        vector_search=Config.VectorSearchConfig(
            enabled=True,
            provider="local",
            model="all-MiniLM-L6-v2",
            dimension=TEST_EMBEDDING_DIMENSION
        ),
        server=Config.ServerConfig(
            host="127.0.0.1",
            port=8001
        )
    )

@pytest.fixture
def test_user_context():
    """Create test user context."""
    return UserContext(
        user_id="test_user_123",
        email="test@example.com",
        tenant_id="test_tenant",
        permissions=["read", "write", "admin"],
        metadata={"test": True}
    )

@pytest_asyncio.fixture
async def mock_embedding_service():
    """Create mock embedding service for testing."""
    service = MagicMock(spec=EmbeddingService)
    service.dimension = TEST_EMBEDDING_DIMENSION
    
    # Mock embedding generation
    def generate_mock_embedding(text: str):
        # Generate deterministic embedding based on text hash
        import hashlib
        hash_obj = hashlib.md5(text.encode())
        seed = int(hash_obj.hexdigest()[:8], 16)
        import random
        random.seed(seed)
        return [random.random() for _ in range(TEST_EMBEDDING_DIMENSION)]
    
    service.generate_embedding = AsyncMock(side_effect=generate_mock_embedding)
    service.generate_embeddings_batch = AsyncMock(
        side_effect=lambda texts, batch_size=100: [generate_mock_embedding(t) for t in texts]
    )
    service.cosine_similarity = MagicMock(
        side_effect=lambda a, b: 0.85 if a[:10] == b[:10] else 0.3
    )
    
    return service

@pytest_asyncio.fixture
async def test_database(test_config):
    """Create test database with sample data."""
    db = await DatabaseFactory.create_database(test_config)
    
    # Add sample data
    sample_projects = [
        Project(
            id="project_1",
            name="Website Development",
            description="Building a new company website with React",
            status="active",
            priority="high",
            tags=["web", "react", "development"],
            created_date=datetime.now() - timedelta(days=5),
            updated_date=datetime.now() - timedelta(hours=2)
        ),
        Project(
            id="project_2", 
            name="Mobile App",
            description="iOS and Android app for customer service",
            status="active",
            priority="medium",
            tags=["mobile", "ios", "android"],
            created_date=datetime.now() - timedelta(days=10),
            updated_date=datetime.now() - timedelta(days=1)
        ),
        Project(
            id="project_3",
            name="Database Migration",
            description="Migrate legacy database to PostgreSQL",
            status="completed",
            priority="low",
            tags=["database", "postgresql", "migration"],
            created_date=datetime.now() - timedelta(days=30),
            updated_date=datetime.now() - timedelta(days=20)
        )
    ]
    
    sample_todos = [
        Todo(
            id="todo_1",
            title="Design homepage mockup",
            description="Create wireframes and mockups for the new homepage",
            completed=False,
            priority="high",
            project_id="project_1",
            due_date=datetime.now() + timedelta(days=2),
            created_date=datetime.now() - timedelta(days=3),
            updated_date=datetime.now() - timedelta(hours=1)
        ),
        Todo(
            id="todo_2",
            title="Set up development environment",
            description="Configure React development environment with testing",
            completed=True,
            priority="medium",
            project_id="project_1",
            created_date=datetime.now() - timedelta(days=4),
            updated_date=datetime.now() - timedelta(days=3)
        ),
        Todo(
            id="todo_3",
            title="Research mobile frameworks",
            description="Compare React Native vs Flutter for mobile development",
            completed=False,
            priority="medium",
            project_id="project_2",
            due_date=datetime.now() + timedelta(days=7),
            created_date=datetime.now() - timedelta(days=2),
            updated_date=datetime.now() - timedelta(hours=6)
        )
    ]
    
    sample_events = [
        CalendarEvent(
            id="event_1",
            title="Client Meeting",
            description="Review website mockups with client",
            start_time=datetime.now() + timedelta(hours=2),
            end_time=datetime.now() + timedelta(hours=3),
            location="Conference Room A",
            attendees=["client@example.com", "designer@company.com"],
            created_date=datetime.now() - timedelta(days=1),
            updated_date=datetime.now() - timedelta(hours=1)
        ),
        CalendarEvent(
            id="event_2",
            title="Team Standup",
            description="Daily team synchronization meeting",
            start_time=datetime.now() + timedelta(days=1, hours=9),
            end_time=datetime.now() + timedelta(days=1, hours=9, minutes=30),
            location="Virtual",
            attendees=["team@company.com"],
            created_date=datetime.now() - timedelta(days=7),
            updated_date=datetime.now() - timedelta(days=7)
        )
    ]
    
    # Insert sample data
    for project in sample_projects:
        await db.add_project(project)
    
    for todo in sample_todos:
        await db.add_todo(todo)
    
    for event in sample_events:
        await db.add_calendar_event(event)
    
    # Set sample status
    status = StatusEntry(
        id="status_1",
        status="working",
        message="Working on website development",
        emoji="💻",
        created_date=datetime.now()
    )
    await db.set_status(status)
    
    # Set sample personal data
    personal_data = PersonalData(
        key="work_hours",
        value={"start": "09:00", "end": "17:00", "timezone": "UTC"},
        data_type="json",
        created_date=datetime.now(),
        updated_date=datetime.now()
    )
    await db.set_personal_data(personal_data)
    
    yield db
    
    await db.close()

@pytest_asyncio.fixture
async def test_server(test_config, mock_embedding_service):
    """Create test HTTP server."""
    # Override embedding service
    import src.embedding_service
    original_get_service = src.embedding_service.get_embedding_service
    src.embedding_service.get_embedding_service = lambda *args, **kwargs: mock_embedding_service
    
    server = PersonalAssistantHTTPServer(test_config)
    yield server
    
    # Cleanup
    for db in server.db_interfaces.values():
        await db.close()
    
    # Restore original service
    src.embedding_service.get_embedding_service = original_get_service

@pytest.fixture
def test_client(test_server):
    """Create test client for HTTP server."""
    return TestClient(test_server.app)

@pytest_asyncio.fixture
async def authenticated_client(test_client, test_user_context):
    """Create authenticated test client."""
    # Mock authentication middleware
    async def mock_auth(request, call_next):
        request.state.user = test_user_context
        return await call_next(request)
    
    # Override middleware
    test_client.app.middleware_stack = None
    test_client.app.user_middleware.clear()
    test_client.app.add_middleware(
        type("MockAuthMiddleware", (), {"dispatch": mock_auth})
    )
    test_client.app.build_middleware_stack()
    
    return test_client

# Test data generators
def generate_test_project(**overrides) -> Dict[str, Any]:
    """Generate test project data."""
    base_data = {
        "id": str(uuid.uuid4()),
        "name": "Test Project",
        "description": "A test project for unit testing",
        "status": "active",
        "priority": "medium",
        "tags": ["test", "project"],
        "created_date": datetime.now(),
        "updated_date": datetime.now()
    }
    base_data.update(overrides)
    return base_data

def generate_test_todo(**overrides) -> Dict[str, Any]:
    """Generate test todo data."""
    base_data = {
        "id": str(uuid.uuid4()),
        "title": "Test Todo",
        "description": "A test todo item",
        "completed": False,
        "priority": "medium",
        "project_id": None,
        "due_date": datetime.now() + timedelta(days=7),
        "created_date": datetime.now(),
        "updated_date": datetime.now()
    }
    base_data.update(overrides)
    return base_data

def generate_test_event(**overrides) -> Dict[str, Any]:
    """Generate test event data."""
    start_time = datetime.now() + timedelta(hours=2)
    base_data = {
        "id": str(uuid.uuid4()),
        "title": "Test Event",
        "description": "A test calendar event",
        "start_time": start_time,
        "end_time": start_time + timedelta(hours=1),
        "location": "Test Location",
        "attendees": ["test@example.com"],
        "created_date": datetime.now(),
        "updated_date": datetime.now()
    }
    base_data.update(overrides)
    return base_data

# Performance test fixtures
@pytest.fixture
def performance_test_data():
    """Generate large dataset for performance testing."""
    projects = [generate_test_project(
        name=f"Performance Test Project {i}",
        description=f"This is performance test project number {i} for load testing"
    ) for i in range(100)]
    
    todos = [generate_test_todo(
        title=f"Performance Test Todo {i}",
        description=f"This is performance test todo number {i} for load testing",
        project_id=projects[i % len(projects)]["id"] if i < len(projects) else None
    ) for i in range(500)]
    
    events = [generate_test_event(
        title=f"Performance Test Event {i}",
        description=f"This is performance test event number {i} for load testing",
        start_time=datetime.now() + timedelta(hours=i, minutes=30)
    ) for i in range(50)]
    
    return {
        "projects": projects,
        "todos": todos,
        "events": events
    }

@pytest.fixture(autouse=True)
def reset_test_environment():
    """Reset test environment before each test."""
    # Clear any cached instances
    import src.embedding_service
    src.embedding_service._embedding_service = None
    
    # Reset environment variables
    test_env_vars = {
        "ENVIRONMENT": "testing",
        "LOG_LEVEL": "DEBUG",
        "AUTH_ENABLED": "false",
        "VECTOR_SEARCH_ENABLED": "true"
    }
    
    original_env = {}
    for key, value in test_env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # Restore original environment
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value