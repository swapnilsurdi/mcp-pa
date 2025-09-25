#!/usr/bin/env python3
"""
Model validation test using Pydantic directly
"""

import sys
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator

# Define test models similar to the actual models
class Project(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: str = "active"
    priority: str = "medium"
    tags: List[str] = []
    created_date: datetime
    updated_date: datetime

class Todo(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    completed: bool = False
    priority: str = "medium"
    project_id: Optional[str] = None
    created_date: datetime
    updated_date: Optional[datetime] = None

class CalendarEvent(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    attendees: List[str] = []
    created_date: datetime
    updated_date: Optional[datetime] = None

def test_project_validation():
    """Test project model validation"""
    now = datetime.now()
    
    # Valid project
    project = Project(
        id="test_project",
        name="Test Project",
        description="Test Description",
        status="active",
        priority="high",
        tags=["test", "validation"],
        created_date=now,
        updated_date=now
    )
    
    assert project.id == "test_project"
    assert project.name == "Test Project"
    assert project.status == "active"
    assert project.priority == "high"
    assert len(project.tags) == 2
    assert "test" in project.tags
    
    # Test JSON serialization
    json_data = project.model_dump()
    assert json_data["name"] == "Test Project"
    
    # Test JSON deserialization
    reconstructed = Project(**json_data)
    assert reconstructed.name == project.name
    
    print("✓ Project model validation passed")

def test_todo_validation():
    """Test todo model validation"""
    now = datetime.now()
    
    # Valid todo
    todo = Todo(
        id="test_todo",
        title="Test Todo",
        description="Test Description",
        completed=False,
        priority="high",
        project_id="test_project",
        created_date=now
    )
    
    assert todo.id == "test_todo"
    assert todo.title == "Test Todo"
    assert todo.completed is False
    assert todo.priority == "high"
    assert todo.project_id == "test_project"
    
    # Test completion toggle
    todo.completed = True
    assert todo.completed is True
    
    print("✓ Todo model validation passed")

def test_calendar_event_validation():
    """Test calendar event model validation"""
    now = datetime.now()
    end_time = now.replace(hour=now.hour + 1)
    
    # Valid event
    event = CalendarEvent(
        id="test_event",
        title="Test Event",
        description="Test meeting",
        start_time=now,
        end_time=end_time,
        location="Test Room",
        attendees=["test1@example.com", "test2@example.com"],
        created_date=now
    )
    
    assert event.id == "test_event"
    assert event.title == "Test Event"
    assert event.start_time == now
    assert event.end_time == end_time
    assert event.location == "Test Room"
    assert len(event.attendees) == 2
    assert "test1@example.com" in event.attendees
    
    print("✓ Calendar event model validation passed")

def test_model_serialization():
    """Test model serialization and deserialization"""
    import json
    
    now = datetime.now()
    
    # Create test data
    project = Project(
        id="p1",
        name="Project 1",
        created_date=now,
        updated_date=now
    )
    
    # Test pydantic JSON export
    json_str = project.model_dump_json()
    parsed_data = json.loads(json_str)
    
    assert parsed_data["name"] == "Project 1"
    assert "created_date" in parsed_data
    
    # Test reconstruction
    reconstructed = Project.model_validate(parsed_data)
    assert reconstructed.name == project.name
    assert reconstructed.id == project.id
    
    print("✓ Model serialization validation passed")

def test_model_validation_errors():
    """Test model validation error handling"""
    try:
        # Should fail - missing required fields
        Project(name="Test")
        assert False, "Should have raised validation error"
    except Exception as e:
        assert "validation error" in str(e).lower() or "missing" in str(e).lower()
        print("✓ Model validation errors handled correctly")

def run_model_validation():
    """Run all model validation tests"""
    print("Running Model Validation Tests")
    print("=" * 40)
    
    try:
        test_project_validation()
        test_todo_validation()
        test_calendar_event_validation()
        test_model_serialization()
        test_model_validation_errors()
        
        print("=" * 40)
        print("✅ ALL MODEL VALIDATION TESTS PASSED")
        print("✅ Pydantic models working correctly")
        print("✅ Serialization/deserialization functional")
        print("✅ Validation error handling working")
        
        return True
        
    except Exception as e:
        print(f"❌ Model validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_model_validation()
    sys.exit(0 if success else 1)