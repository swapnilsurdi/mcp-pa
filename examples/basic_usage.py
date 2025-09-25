#!/usr/bin/env python3
"""
Basic usage example for the MCP Personal Assistant

This script demonstrates how to use the MCP Personal Assistant
outside of Claude Desktop for testing and development.
"""

import sys
import asyncio
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database_factory import get_database
from src.models import Project, Todo, CalendarEvent


async def main():
    """Example usage of the MCP Personal Assistant"""
    print("🚀 MCP Personal Assistant - Basic Usage Example")
    print("=" * 50)

    try:
        # Initialize database
        print("1. Initializing database...")
        db = get_database()
        print("   ✓ Database connected successfully")

        # Get current status
        print("\n2. Getting current status...")
        status = db.get_status()
        print(f"   User: {status.name}")
        print(f"   Last updated: {status.last_updated}")

        # Create a sample project
        print("\n3. Creating a sample project...")
        from uuid import uuid4
        from datetime import datetime
        project = db.create_project(Project(
            id=str(uuid4()),
            name="Sample Project",
            description="A test project created via the API",
            status="in_progress",
            priority="medium",
            tags=["example", "test"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tasks=[],
            notes=None,
            progress=0,
            start_date=None,
            end_date=None
        ))
        print(f"   ✓ Created project: {project.name} (ID: {project.id})")

        # List all projects
        print("\n4. Listing all projects...")
        projects = db.list_projects()
        print(f"   Found {len(projects)} projects:")
        for p in projects:
            print(f"   - {p.name} ({p.status})")

        # Create a sample todo
        print("\n5. Creating a sample todo...")
        todo = db.create_todo(Todo(
            id=str(uuid4()),
            title="Test the MCP server",
            description="Verify that the MCP Personal Assistant is working correctly",
            completed=False,
            priority="high",
            tags=["testing"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            project_id=None,
            due_date=None,
            reminder_date=None
        ))
        print(f"   ✓ Created todo: {todo.title} (ID: {todo.id})")

        # List all todos
        print("\n6. Listing all todos...")
        todos = db.list_todos()
        print(f"   Found {len(todos)} todos:")
        for t in todos:
            status_emoji = "✓" if t.completed else "○"
            print(f"   {status_emoji} {t.title} ({t.priority})")

        print("\n🎉 Basic usage example completed successfully!")
        print("\nNext steps:")
        print("- Configure Claude Desktop to use this MCP server")
        print("- Try the tools through Claude Desktop")
        print("- Explore the API documentation in docs/")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())