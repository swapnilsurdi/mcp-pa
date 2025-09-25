"""
Unit tests for data models
"""

import pytest
from datetime import datetime, timedelta
import uuid
from pydantic import ValidationError

from src.models import Project, Todo, CalendarEvent, StatusEntry, PersonalData


class TestProject:
    """Test Project model"""
    
    def test_project_creation(self):
        """Test basic project creation"""
        project = Project(
            id="test_id",
            name="Test Project",
            description="Test Description",
            status="active",
            priority="high",
            tags=["test", "project"],
            created_date=datetime.now(),
            updated_date=datetime.now()
        )
        
        assert project.id == "test_id"
        assert project.name == "Test Project"
        assert project.status == "active"
        assert project.priority == "high"
        assert "test" in project.tags
    
    def test_project_validation(self):
        """Test project validation"""
        # Missing required fields
        with pytest.raises(ValidationError):
            Project()
        
        # Invalid status
        with pytest.raises(ValidationError):
            Project(
                id="test",
                name="Test",
                description="Test",
                status="invalid_status",
                priority="high",
                created_date=datetime.now(),
                updated_date=datetime.now()
            )
        
        # Invalid priority
        with pytest.raises(ValidationError):
            Project(
                id="test",
                name="Test", 
                description="Test",
                status="active",
                priority="invalid_priority",
                created_date=datetime.now(),
                updated_date=datetime.now()
            )
    
    def test_project_defaults(self):
        """Test project default values"""
        project = Project(
            id="test",
            name="Test",
            description="Test",
            created_date=datetime.now(),
            updated_date=datetime.now()
        )
        
        assert project.status == "active"
        assert project.priority == "medium"
        assert project.tags == []
    
    def test_project_serialization(self):
        """Test project JSON serialization"""
        project = Project(
            id="test",
            name="Test Project",
            description="Test Description",
            status="active",
            priority="high",
            tags=["test"],
            created_date=datetime.now(),
            updated_date=datetime.now()
        )
        
        json_data = project.model_dump()
        assert json_data["id"] == "test"
        assert json_data["name"] == "Test Project"
        assert isinstance(json_data["created_date"], datetime)


class TestTodo:
    """Test Todo model"""
    
    def test_todo_creation(self):
        """Test basic todo creation"""
        todo = Todo(
            id="test_todo",
            title="Test Todo",
            description="Test Description",
            completed=False,
            priority="high",
            created_date=datetime.now(),
            updated_date=datetime.now()
        )
        
        assert todo.id == "test_todo"
        assert todo.title == "Test Todo"
        assert todo.completed is False
        assert todo.priority == "high"
    
    def test_todo_validation(self):
        """Test todo validation"""
        # Missing required fields
        with pytest.raises(ValidationError):
            Todo()
        
        # Invalid priority
        with pytest.raises(ValidationError):
            Todo(
                id="test",
                title="Test",
                completed=False,
                priority="invalid",
                created_date=datetime.now(),
                updated_date=datetime.now()
            )
    
    def test_todo_defaults(self):
        """Test todo default values"""
        todo = Todo(
            id="test",
            title="Test Todo",
            created_date=datetime.now(),
            updated_date=datetime.now()
        )
        
        assert todo.completed is False
        assert todo.priority == "medium"
        assert todo.description is None
        assert todo.project_id is None
        assert todo.due_date is None
    
    def test_todo_completion(self):
        """Test todo completion functionality"""
        todo = Todo(
            id="test",
            title="Test Todo",
            completed=False,
            created_date=datetime.now(),
            updated_date=datetime.now()
        )
        
        # Mark as completed
        todo.completed = True
        assert todo.completed is True
    
    def test_todo_due_date(self):
        """Test todo due date handling"""
        future_date = datetime.now() + timedelta(days=7)
        
        todo = Todo(
            id="test",
            title="Test Todo",
            due_date=future_date,
            created_date=datetime.now(),
            updated_date=datetime.now()
        )
        
        assert todo.due_date == future_date


class TestCalendarEvent:
    """Test CalendarEvent model"""
    
    def test_event_creation(self):
        """Test basic event creation"""
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)
        
        event = CalendarEvent(
            id="test_event",
            title="Test Event",
            description="Test Description",
            start_time=start_time,
            end_time=end_time,
            location="Test Location",
            attendees=["test@example.com"],
            created_date=datetime.now(),
            updated_date=datetime.now()
        )
        
        assert event.id == "test_event"
        assert event.title == "Test Event"
        assert event.start_time == start_time
        assert event.end_time == end_time
        assert "test@example.com" in event.attendees
    
    def test_event_validation(self):
        """Test event validation"""
        # Missing required fields
        with pytest.raises(ValidationError):
            CalendarEvent()
        
        # End time before start time
        start_time = datetime.now() + timedelta(hours=2)
        end_time = datetime.now() + timedelta(hours=1)
        
        with pytest.raises(ValidationError):
            CalendarEvent(
                id="test",
                title="Test",
                start_time=start_time,
                end_time=end_time,
                created_date=datetime.now(),
                updated_date=datetime.now()
            )
    
    def test_event_defaults(self):
        """Test event default values"""
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=1)
        
        event = CalendarEvent(
            id="test",
            title="Test Event",
            start_time=start_time,
            end_time=end_time,
            created_date=datetime.now(),
            updated_date=datetime.now()
        )
        
        assert event.description is None
        assert event.location is None
        assert event.attendees == []
    
    def test_event_duration(self):
        """Test event duration calculation"""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=2, minutes=30)
        
        event = CalendarEvent(
            id="test",
            title="Test Event",
            start_time=start_time,
            end_time=end_time,
            created_date=datetime.now(),
            updated_date=datetime.now()
        )
        
        duration = event.end_time - event.start_time
        assert duration == timedelta(hours=2, minutes=30)


class TestStatusEntry:
    """Test StatusEntry model"""
    
    def test_status_creation(self):
        """Test basic status creation"""
        status = StatusEntry(
            id="test_status",
            status="working",
            message="Working on project",
            emoji="💻",
            created_date=datetime.now()
        )
        
        assert status.id == "test_status"
        assert status.status == "working"
        assert status.message == "Working on project"
        assert status.emoji == "💻"
    
    def test_status_validation(self):
        """Test status validation"""
        # Missing required fields
        with pytest.raises(ValidationError):
            StatusEntry()
    
    def test_status_defaults(self):
        """Test status default values"""
        status = StatusEntry(
            id="test",
            status="available",
            created_date=datetime.now()
        )
        
        assert status.message is None
        assert status.emoji is None
        assert status.expiry_date is None
    
    def test_status_expiry(self):
        """Test status expiry functionality"""
        expiry_date = datetime.now() + timedelta(hours=8)
        
        status = StatusEntry(
            id="test",
            status="busy",
            expiry_date=expiry_date,
            created_date=datetime.now()
        )
        
        assert status.expiry_date == expiry_date
        
        # Test if status is expired
        past_expiry = datetime.now() - timedelta(hours=1)
        expired_status = StatusEntry(
            id="test2",
            status="busy",
            expiry_date=past_expiry,
            created_date=datetime.now() - timedelta(hours=2)
        )
        
        assert expired_status.expiry_date < datetime.now()


class TestPersonalData:
    """Test PersonalData model"""
    
    def test_personal_data_creation(self):
        """Test basic personal data creation"""
        data = PersonalData(
            key="test_key",
            value={"setting": "value"},
            data_type="json",
            created_date=datetime.now(),
            updated_date=datetime.now()
        )
        
        assert data.key == "test_key"
        assert data.value == {"setting": "value"}
        assert data.data_type == "json"
    
    def test_personal_data_validation(self):
        """Test personal data validation"""
        # Missing required fields
        with pytest.raises(ValidationError):
            PersonalData()
        
        # Invalid data type
        with pytest.raises(ValidationError):
            PersonalData(
                key="test",
                value="value",
                data_type="invalid_type",
                created_date=datetime.now(),
                updated_date=datetime.now()
            )
    
    def test_personal_data_types(self):
        """Test different data types"""
        # String data
        string_data = PersonalData(
            key="string_key",
            value="string_value",
            data_type="string",
            created_date=datetime.now(),
            updated_date=datetime.now()
        )
        assert isinstance(string_data.value, str)
        
        # JSON data
        json_data = PersonalData(
            key="json_key",
            value={"nested": {"key": "value"}},
            data_type="json",
            created_date=datetime.now(),
            updated_date=datetime.now()
        )
        assert isinstance(json_data.value, dict)
        
        # Number data
        number_data = PersonalData(
            key="number_key",
            value=42,
            data_type="number",
            created_date=datetime.now(),
            updated_date=datetime.now()
        )
        assert isinstance(number_data.value, int)
    
    def test_personal_data_serialization(self):
        """Test personal data serialization"""
        data = PersonalData(
            key="test_key",
            value={"complex": {"nested": [1, 2, 3]}},
            data_type="json",
            created_date=datetime.now(),
            updated_date=datetime.now()
        )
        
        json_data = data.model_dump()
        assert json_data["key"] == "test_key"
        assert json_data["value"] == {"complex": {"nested": [1, 2, 3]}}
        assert json_data["data_type"] == "json"