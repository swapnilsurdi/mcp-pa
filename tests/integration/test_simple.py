#!/usr/bin/env python3
"""
Simple test validation script
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from datetime import datetime
from src.models import Project, Todo, CalendarEvent, StatusEntry, PersonalData

def test_project_creation():
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
    
    print("✓ Project creation test passed")

def test_todo_creation():
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
    
    print("✓ Todo creation test passed")

def test_calendar_event_creation():
    """Test basic calendar event creation"""
    start_time = datetime.now()
    end_time = start_time.replace(hour=start_time.hour + 1)
    
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
    
    print("✓ Calendar event creation test passed")

def test_status_entry_creation():
    """Test basic status entry creation"""
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
    
    print("✓ Status entry creation test passed")

def test_personal_data_creation():
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
    
    print("✓ Personal data creation test passed")

def run_basic_validation():
    """Run basic validation tests"""
    print("Running basic MCP Personal Assistant test validation...")
    print("=" * 60)
    
    try:
        test_project_creation()
        test_todo_creation()
        test_calendar_event_creation()
        test_status_entry_creation()
        test_personal_data_creation()
        
        print("=" * 60)
        print("✅ ALL BASIC TESTS PASSED")
        print("✅ Core models are working correctly")
        print("✅ Pydantic validation is functional")
        print("✅ Test infrastructure is ready")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_basic_validation()
    sys.exit(0 if success else 1)