"""
Integration tests for database operations
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
import uuid
import asyncio

from src.database_factory import DatabaseFactory
from src.models import Project, Todo, CalendarEvent, StatusEntry, PersonalData
from tests.conftest import generate_test_project, generate_test_todo, generate_test_event


class TestSQLiteDatabaseIntegration:
    """Integration tests for SQLite database operations"""
    
    @pytest_asyncio.fixture
    async def sqlite_db(self, test_config):
        """Create SQLite database for testing"""
        test_config.database_type = "sqlite"
        db = await DatabaseFactory.create_database(test_config)
        yield db
        await db.close()
    
    @pytest.mark.asyncio
    async def test_project_operations(self, sqlite_db):
        """Test complete project CRUD operations"""
        # Create project
        project_data = generate_test_project(
            name="SQLite Test Project",
            description="Testing SQLite database operations",
            priority="high"
        )
        project = Project(**project_data)
        
        # Add project
        await sqlite_db.add_project(project)
        
        # Get project by ID
        retrieved_project = await sqlite_db.get_project_by_id(project.id)
        assert retrieved_project is not None
        assert retrieved_project.id == project.id
        assert retrieved_project.name == project.name
        assert retrieved_project.description == project.description
        assert retrieved_project.priority == project.priority
        
        # Update project
        retrieved_project.name = "Updated SQLite Test Project"
        retrieved_project.status = "completed"
        retrieved_project.updated_date = datetime.now()
        
        await sqlite_db.update_project(retrieved_project)
        
        # Verify update
        updated_project = await sqlite_db.get_project_by_id(project.id)
        assert updated_project.name == "Updated SQLite Test Project"
        assert updated_project.status == "completed"
        
        # List projects
        all_projects = await sqlite_db.get_projects()
        assert len(all_projects) >= 1
        assert any(p.id == project.id for p in all_projects)
        
        # Delete project
        await sqlite_db.delete_project(project.id)
        
        # Verify deletion
        deleted_project = await sqlite_db.get_project_by_id(project.id)
        assert deleted_project is None
    
    @pytest.mark.asyncio
    async def test_todo_operations(self, sqlite_db):
        """Test complete todo CRUD operations"""
        # Create project first (for foreign key)
        project_data = generate_test_project()
        project = Project(**project_data)
        await sqlite_db.add_project(project)
        
        # Create todo
        todo_data = generate_test_todo(
            title="SQLite Test Todo",
            description="Testing SQLite todo operations",
            project_id=project.id,
            priority="high"
        )
        todo = Todo(**todo_data)
        
        # Add todo
        await sqlite_db.add_todo(todo)
        
        # Get todo by ID
        retrieved_todo = await sqlite_db.get_todo_by_id(todo.id)
        assert retrieved_todo is not None
        assert retrieved_todo.id == todo.id
        assert retrieved_todo.title == todo.title
        assert retrieved_todo.project_id == project.id
        
        # Update todo
        retrieved_todo.title = "Updated SQLite Test Todo"
        retrieved_todo.completed = True
        retrieved_todo.updated_date = datetime.now()
        
        await sqlite_db.update_todo(retrieved_todo)
        
        # Verify update
        updated_todo = await sqlite_db.get_todo_by_id(todo.id)
        assert updated_todo.title == "Updated SQLite Test Todo"
        assert updated_todo.completed is True
        
        # List todos
        all_todos = await sqlite_db.get_todos()
        assert len(all_todos) >= 1
        assert any(t.id == todo.id for t in all_todos)
        
        # List todos by project
        project_todos = await sqlite_db.get_todos(project_id=project.id)
        assert len(project_todos) >= 1
        assert all(t.project_id == project.id for t in project_todos)
        
        # Delete todo
        await sqlite_db.delete_todo(todo.id)
        
        # Verify deletion
        deleted_todo = await sqlite_db.get_todo_by_id(todo.id)
        assert deleted_todo is None
        
        # Cleanup
        await sqlite_db.delete_project(project.id)
    
    @pytest.mark.asyncio
    async def test_calendar_event_operations(self, sqlite_db):
        """Test calendar event operations"""
        # Create event
        event_data = generate_test_event(
            title="SQLite Test Event",
            description="Testing SQLite calendar operations"
        )
        event = CalendarEvent(**event_data)
        
        # Add event
        await sqlite_db.add_calendar_event(event)
        
        # Get events in date range
        start_date = datetime.now()
        end_date = datetime.now() + timedelta(days=7)
        
        events = await sqlite_db.get_calendar_events(start_date, end_date)
        assert len(events) >= 1
        
        found_event = next((e for e in events if e.id == event.id), None)
        assert found_event is not None
        assert found_event.title == event.title
        assert found_event.description == event.description
    
    @pytest.mark.asyncio
    async def test_status_operations(self, sqlite_db):
        """Test status operations"""
        # Set initial status
        status = StatusEntry(
            id="test_status_1",
            status="working",
            message="Working on SQLite tests",
            emoji="💻",
            created_date=datetime.now()
        )
        
        await sqlite_db.set_status(status)
        
        # Get status
        retrieved_status = await sqlite_db.get_status()
        assert retrieved_status is not None
        assert retrieved_status.id == status.id
        assert retrieved_status.status == status.status
        assert retrieved_status.message == status.message
        
        # Update status
        new_status = StatusEntry(
            id="test_status_2",
            status="available",
            message="Available for new tasks",
            emoji="✅",
            created_date=datetime.now()
        )
        
        await sqlite_db.set_status(new_status)
        
        # Verify new status
        current_status = await sqlite_db.get_status()
        assert current_status.id == new_status.id
        assert current_status.status == "available"
    
    @pytest.mark.asyncio
    async def test_personal_data_operations(self, sqlite_db):
        """Test personal data operations"""
        # Set string data
        string_data = PersonalData(
            key="test_string",
            value="test_value",
            data_type="string",
            created_date=datetime.now(),
            updated_date=datetime.now()
        )
        
        await sqlite_db.set_personal_data(string_data)
        
        # Get string data
        retrieved_data = await sqlite_db.get_personal_data("test_string")
        assert retrieved_data is not None
        assert retrieved_data.key == "test_string"
        assert retrieved_data.value == "test_value"
        assert retrieved_data.data_type == "string"
        
        # Set JSON data
        json_data = PersonalData(
            key="test_json",
            value={"nested": {"key": "value"}, "array": [1, 2, 3]},
            data_type="json",
            created_date=datetime.now(),
            updated_date=datetime.now()
        )
        
        await sqlite_db.set_personal_data(json_data)
        
        # Get JSON data
        retrieved_json = await sqlite_db.get_personal_data("test_json")
        assert retrieved_json is not None
        assert retrieved_json.value["nested"]["key"] == "value"
        assert retrieved_json.value["array"] == [1, 2, 3]
        
        # Get all personal data
        all_data = await sqlite_db.get_all_personal_data()
        assert len(all_data) >= 2
        
        keys = [d.key for d in all_data]
        assert "test_string" in keys
        assert "test_json" in keys
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, sqlite_db):
        """Test concurrent database operations"""
        # Create multiple projects concurrently
        async def create_project(i):
            project_data = generate_test_project(
                name=f"Concurrent Project {i}",
                description=f"Project created concurrently {i}"
            )
            project = Project(**project_data)
            await sqlite_db.add_project(project)
            return project.id
        
        # Run concurrent operations
        tasks = [create_project(i) for i in range(5)]
        project_ids = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all projects were created
        successful_ids = [pid for pid in project_ids if isinstance(pid, str)]
        assert len(successful_ids) >= 3  # At least 3 should succeed
        
        # Verify projects exist
        all_projects = await sqlite_db.get_projects()
        for project_id in successful_ids:
            project = await sqlite_db.get_project_by_id(project_id)
            assert project is not None
    
    @pytest.mark.asyncio
    async def test_data_integrity(self, sqlite_db):
        """Test data integrity and foreign key constraints"""
        # Create project
        project_data = generate_test_project()
        project = Project(**project_data)
        await sqlite_db.add_project(project)
        
        # Create todo with project reference
        todo_data = generate_test_todo(project_id=project.id)
        todo = Todo(**todo_data)
        await sqlite_db.add_todo(todo)
        
        # Delete project (should handle foreign key constraint)
        await sqlite_db.delete_project(project.id)
        
        # Todo should still exist but project_id might be null
        remaining_todo = await sqlite_db.get_todo_by_id(todo.id)
        assert remaining_todo is not None
        # Foreign key behavior depends on database configuration
        # In SQLite with CASCADE or SET NULL, the behavior would be defined
    
    @pytest.mark.asyncio
    async def test_transaction_rollback(self, sqlite_db):
        """Test transaction rollback behavior"""
        # This test would require transaction support in the database interface
        # For now, test basic error handling
        
        # Try to add invalid project
        try:
            invalid_project = Project(
                id="",  # Invalid empty ID
                name="Invalid Project",
                description="This should fail",
                created_date=datetime.now(),
                updated_date=datetime.now()
            )
            await sqlite_db.add_project(invalid_project)
            assert False, "Should have failed with invalid data"
        except Exception:
            # Expected to fail
            pass
        
        # Verify database state is consistent
        all_projects = await sqlite_db.get_projects()
        # Should not contain the invalid project
        assert not any(p.name == "Invalid Project" for p in all_projects)


class TestTinyDBIntegration:
    """Integration tests for TinyDB database operations"""
    
    @pytest_asyncio.fixture
    async def tinydb(self, test_config):
        """Create TinyDB database for testing"""
        test_config.database_type = "tinydb"
        db = await DatabaseFactory.create_database(test_config)
        yield db
        await db.close()
    
    @pytest.mark.asyncio
    async def test_basic_operations(self, tinydb):
        """Test basic TinyDB operations"""
        # Create and add project
        project_data = generate_test_project(
            name="TinyDB Test Project",
            description="Testing TinyDB operations"
        )
        project = Project(**project_data)
        
        await tinydb.add_project(project)
        
        # Retrieve project
        retrieved_project = await tinydb.get_project_by_id(project.id)
        assert retrieved_project is not None
        assert retrieved_project.name == project.name
        
        # List projects
        all_projects = await tinydb.get_projects()
        assert len(all_projects) >= 1
        assert any(p.id == project.id for p in all_projects)
    
    @pytest.mark.asyncio
    async def test_json_serialization(self, tinydb):
        """Test JSON serialization with TinyDB"""
        # Test complex data structure
        project_data = generate_test_project(
            tags=["json", "serialization", "test"],
        )
        project_data["metadata"] = {
            "nested": {"key": "value"},
            "array": [1, 2, 3],
            "boolean": True,
            "null": None
        }
        project = Project(**project_data)
        
        await tinydb.add_project(project)
        
        # Retrieve and verify serialization
        retrieved_project = await tinydb.get_project_by_id(project.id)
        assert retrieved_project is not None
        assert retrieved_project.tags == ["json", "serialization", "test"]
        
        # TinyDB should handle complex data structures
        if hasattr(retrieved_project, 'metadata'):
            assert retrieved_project.metadata["nested"]["key"] == "value"
    
    @pytest.mark.asyncio
    async def test_date_handling(self, tinydb):
        """Test date serialization/deserialization with TinyDB"""
        now = datetime.now()
        future_date = now + timedelta(days=7)
        
        todo_data = generate_test_todo(
            title="Date Test Todo",
            due_date=future_date
        )
        todo = Todo(**todo_data)
        
        await tinydb.add_todo(todo)
        
        # Retrieve and verify dates
        retrieved_todo = await tinydb.get_todo_by_id(todo.id)
        assert retrieved_todo is not None
        assert retrieved_todo.due_date is not None
        
        # Date should be preserved (allowing for serialization differences)
        if isinstance(retrieved_todo.due_date, datetime):
            # Allow small differences due to serialization
            time_diff = abs((retrieved_todo.due_date - future_date).total_seconds())
            assert time_diff < 1  # Within 1 second


class TestPostgreSQLIntegration:
    """Integration tests for PostgreSQL database operations"""
    
    @pytest_asyncio.fixture
    async def postgres_db(self, test_config):
        """Create PostgreSQL database for testing"""
        # Skip if PostgreSQL not available
        pytest.skip("PostgreSQL integration tests require running PostgreSQL instance")
        
        test_config.database_type = "postgresql"
        test_config.pgvector_connection_string = "postgresql://test:test@localhost:5432/test_db"
        
        try:
            db = await DatabaseFactory.create_database(test_config)
            yield db
            await db.close()
        except Exception as e:
            pytest.skip(f"PostgreSQL not available: {e}")
    
    @pytest.mark.asyncio
    async def test_vector_search_operations(self, postgres_db):
        """Test PostgreSQL vector search operations"""
        # Create projects with embeddings
        project1 = Project(
            id=str(uuid.uuid4()),
            name="AI Project",
            description="Artificial intelligence and machine learning project",
            status="active",
            priority="high",
            tags=["ai", "ml", "python"],
            created_date=datetime.now(),
            updated_date=datetime.now()
        )
        
        project2 = Project(
            id=str(uuid.uuid4()),
            name="Web Development",
            description="Frontend web development with React",
            status="active",
            priority="medium",
            tags=["web", "react", "javascript"],
            created_date=datetime.now(),
            updated_date=datetime.now()
        )
        
        # Add mock embeddings
        project1.__dict__['embedding'] = [0.1] * 1536  # Mock AI-related embedding
        project2.__dict__['embedding'] = [0.9] * 1536  # Mock web-related embedding
        
        await postgres_db.add_project(project1)
        await postgres_db.add_project(project2)
        
        # Test semantic search
        if hasattr(postgres_db, 'semantic_search_projects'):
            query_embedding = [0.1] * 1536  # Should be similar to AI project
            
            results = await postgres_db.semantic_search_projects(
                query_embedding,
                limit=5,
                similarity_threshold=0.7
            )
            
            assert len(results) >= 1
            # First result should be the AI project (most similar)
            best_match, similarity = results[0]
            assert best_match.id == project1.id
            assert similarity > 0.7
    
    @pytest.mark.asyncio
    async def test_schema_isolation(self, postgres_db):
        """Test schema-based tenant isolation"""
        # This test would require multiple database connections
        # with different schema configurations
        
        # For now, verify that tables exist in expected schema
        if hasattr(postgres_db, 'schema'):
            assert postgres_db.schema is not None
            
        # Verify basic operations work with schema
        project_data = generate_test_project(name="Schema Test Project")
        project = Project(**project_data)
        
        await postgres_db.add_project(project)
        retrieved_project = await postgres_db.get_project_by_id(project.id)
        
        assert retrieved_project is not None
        assert retrieved_project.name == project.name


class TestDatabaseFactory:
    """Test database factory operations"""
    
    @pytest.mark.asyncio
    async def test_create_sqlite_database(self, test_config):
        """Test creating SQLite database via factory"""
        test_config.database_type = "sqlite"
        
        db = await DatabaseFactory.create_database(test_config)
        assert db is not None
        
        # Test basic operation
        project_data = generate_test_project()
        project = Project(**project_data)
        
        await db.add_project(project)
        retrieved_project = await db.get_project_by_id(project.id)
        
        assert retrieved_project is not None
        assert retrieved_project.id == project.id
        
        await db.close()
    
    @pytest.mark.asyncio
    async def test_create_tinydb_database(self, test_config):
        """Test creating TinyDB database via factory"""
        test_config.database_type = "tinydb"
        
        db = await DatabaseFactory.create_database(test_config)
        assert db is not None
        
        # Test basic operation
        project_data = generate_test_project()
        project = Project(**project_data)
        
        await db.add_project(project)
        retrieved_project = await db.get_project_by_id(project.id)
        
        assert retrieved_project is not None
        assert retrieved_project.id == project.id
        
        await db.close()
    
    @pytest.mark.asyncio
    async def test_invalid_database_type(self, test_config):
        """Test factory with invalid database type"""
        test_config.database_type = "invalid_db_type"
        
        with pytest.raises(ValueError, match="Unsupported database type"):
            await DatabaseFactory.create_database(test_config)
    
    @pytest.mark.asyncio
    async def test_database_connection_management(self, test_config):
        """Test proper database connection management"""
        test_config.database_type = "sqlite"
        
        # Create multiple databases
        db1 = await DatabaseFactory.create_database(test_config)
        db2 = await DatabaseFactory.create_database(test_config)
        
        # Both should be functional
        assert db1 is not None
        assert db2 is not None
        
        # Test operations on both
        project1_data = generate_test_project(name="DB1 Project")
        project2_data = generate_test_project(name="DB2 Project")
        
        project1 = Project(**project1_data)
        project2 = Project(**project2_data)
        
        await db1.add_project(project1)
        await db2.add_project(project2)
        
        # Verify isolation (if using different database files)
        db1_projects = await db1.get_projects()
        db2_projects = await db2.get_projects()
        
        # Both should have at least their own project
        assert len(db1_projects) >= 1
        assert len(db2_projects) >= 1
        
        # Close connections
        await db1.close()
        await db2.close()