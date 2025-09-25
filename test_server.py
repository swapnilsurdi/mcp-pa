#!/usr/bin/env python3
"""
Test script to verify MCP Personal Assistant server functionality
"""

import asyncio
import json
import os
from datetime import datetime, timedelta

async def test_server():
    print("Testing MCP Personal Assistant Server...")
    print("-" * 50)
    
    try:
        # Test configuration
        from src.config import get_config
        config = get_config()
        print(f"✓ Configuration loaded - Database type: {config.database.type}")
        print(f"✓ Documents directory: {config.storage.documents_dir}")
        
        # Import the server components
        from src.database_factory import get_database
        from src.document_manager import DocumentManager
        from src.models import UserStatus, Project, Todo, CalendarEvent, Document, ProjectStatus, Priority
        
        # Initialize database
        db = get_database()
        print(f"✓ Database initialized ({config.database.type})")
        
        # Initialize document manager
        doc_manager = DocumentManager()
        print("✓ Document manager initialized")
        
        # Test status operations
        status = db.get_status()
        print(f"✓ Retrieved status for: {status.name}")
        
        # Test project operations
        test_project = Project(
            id="test-project",
            name="Test Project",
            description="This is a test project",
            status=ProjectStatus.IN_PROGRESS,
            priority=Priority.HIGH
        )
        db.create_project(test_project)
        print("✓ Created test project")
        
        retrieved_project = db.get_project("test-project")
        print(f"✓ Retrieved project: {retrieved_project.name}")
        
        # Test todo operations
        test_todo = Todo(
            id="test-todo",
            title="Test Todo",
            description="This is a test todo",
            due_date=datetime.now() + timedelta(days=1),
            priority=Priority.MEDIUM
        )
        db.create_todo(test_todo)
        print("✓ Created test todo")
        
        # Test calendar operations
        test_event = CalendarEvent(
            id="test-event",
            title="Test Event",
            start_time=datetime.now() + timedelta(hours=1),
            end_time=datetime.now() + timedelta(hours=2),
            location="Test Location"
        )
        db.create_event(test_event)
        print("✓ Created test calendar event")
        
        # Test document operations
        test_document = Document(
            id="test-document",
            title="Test Document",
            description="This is a test document",
            file_path="test.txt",
            document_type="text",
            size_bytes=100,
            tags=["test"]
        )
        db.create_document(test_document)
        print("✓ Created test document")
        
        # Clean up test data
        db.delete_project("test-project")
        db.delete_todo("test-todo")
        db.delete_event("test-event")
        db.delete_document("test-document")
        print("✓ Cleaned up test data")
        
        # Close database
        db.close()
        print("✓ Database connection closed")
        
        print("\n" + "="*50)
        print("All tests passed successfully! 🎉")
        print("The MCP Personal Assistant server is ready to use.")
        print("="*50)
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_server())
