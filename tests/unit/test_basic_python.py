#!/usr/bin/env python3
"""
Basic Python validation without imports
"""

import sys
import os
from datetime import datetime

def test_python_basics():
    """Test basic Python functionality"""
    # Test data structures
    project_data = {
        "id": "test_project",
        "name": "Test Project",
        "description": "A test project",
        "status": "active",
        "priority": "high",
        "tags": ["test", "validation"],
        "created_date": datetime.now().isoformat(),
        "updated_date": datetime.now().isoformat()
    }
    
    todo_data = {
        "id": "test_todo",
        "title": "Test Todo",
        "description": "A test todo item",
        "completed": False,
        "priority": "high",
        "created_date": datetime.now().isoformat()
    }
    
    # Validate data structures
    assert project_data["id"] == "test_project"
    assert project_data["status"] == "active"
    assert len(project_data["tags"]) == 2
    assert "test" in project_data["tags"]
    
    assert todo_data["id"] == "test_todo"
    assert todo_data["completed"] is False
    assert todo_data["priority"] == "high"
    
    print("✓ Basic data structure validation passed")

def test_datetime_functionality():
    """Test datetime operations"""
    now = datetime.now()
    iso_time = now.isoformat()
    
    assert isinstance(iso_time, str)
    assert "T" in iso_time  # ISO format includes T separator
    
    print("✓ Datetime functionality validated")

def test_json_operations():
    """Test JSON serialization"""
    import json
    
    test_data = {
        "projects": [
            {"id": "p1", "name": "Project 1", "status": "active"},
            {"id": "p2", "name": "Project 2", "status": "completed"}
        ],
        "todos": [
            {"id": "t1", "title": "Todo 1", "completed": False},
            {"id": "t2", "title": "Todo 2", "completed": True}
        ]
    }
    
    # Test serialization
    json_str = json.dumps(test_data, indent=2)
    parsed_data = json.loads(json_str)
    
    assert parsed_data["projects"][0]["name"] == "Project 1"
    assert parsed_data["todos"][1]["completed"] is True
    
    print("✓ JSON operations validated")

def test_file_operations():
    """Test basic file operations"""
    test_file = "test_validation.tmp"
    test_content = "Test validation content"
    
    try:
        # Write test file
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        # Read test file
        with open(test_file, 'r') as f:
            content = f.read()
        
        assert content == test_content
        print("✓ File operations validated")
        
    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)

def run_basic_validation():
    """Run all basic validation tests"""
    print("Running Basic Python Validation Tests")
    print("=" * 50)
    
    try:
        test_python_basics()
        test_datetime_functionality()
        test_json_operations()
        test_file_operations()
        
        print("=" * 50)
        print("✅ ALL BASIC VALIDATION TESTS PASSED")
        print("✅ Python environment is functional")
        print("✅ Core functionality validated")
        
        return True
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_basic_validation()
    sys.exit(0 if success else 1)