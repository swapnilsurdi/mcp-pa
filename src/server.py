import json
import asyncio
import os
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4
from io import BytesIO

from mcp.server import Server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel,
)

from .database_factory import get_database
from .document_manager import DocumentManager
from .config import get_config
from .models import (
    UserStatus, Project, Task, Todo, CalendarEvent, Document,
    ProjectStatus, TaskStatus, Priority, Location, LaptopDetails, Permissions
)

# Initialize server
server = Server("mcp-pa")
db = get_database()
doc_manager = DocumentManager()

# Set up logging
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@server.list_resources()
async def list_resources() -> List[Resource]:
    """List available resources"""
    return [
        Resource(
            uri="pa://status",
            name="Current Status",
            description="Your current status and system information",
            mimeType="application/json"
        ),
        Resource(
            uri="pa://projects",
            name="All Projects",
            description="List of all projects",
            mimeType="application/json"
        ),
        Resource(
            uri="pa://todos",
            name="All Todos",
            description="List of all todos and reminders",
            mimeType="application/json"
        ),
        Resource(
            uri="pa://calendar",
            name="Calendar Events",
            description="List of all calendar events",
            mimeType="application/json"
        ),
        Resource(
            uri="pa://documents",
            name="Documents",
            description="List of all documents",
            mimeType="application/json"
        )
    ]

@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read resource content"""
    if uri == "pa://status":
        status = db.get_status()
        return json.dumps(status.model_dump(), default=str)
    elif uri == "pa://projects":
        projects = db.list_projects()
        return json.dumps([p.model_dump() for p in projects], default=str)
    elif uri == "pa://todos":
        todos = db.list_todos()
        return json.dumps([t.model_dump() for t in todos], default=str)
    elif uri == "pa://calendar":
        events = db.list_events()
        return json.dumps([e.model_dump() for e in events], default=str)
    elif uri == "pa://documents":
        documents = db.list_documents()
        return json.dumps([d.model_dump() for d in documents], default=str)
    else:
        raise ValueError(f"Unknown resource: {uri}")

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="get_status",
            description="Get your current status including location, laptop details, and permissions",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="update_status",
            description="Update your status information",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "city": {"type": "string"},
                    "state": {"type": "string"},
                    "country": {"type": "string"},
                    "laptop_os": {"type": "string"},
                    "laptop_model": {"type": "string"},
                    "notes": {"type": "string"}
                }
            }
        ),
        Tool(
            name="create_project",
            description="Create a new project",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "status": {"type": "string", "enum": ["not_started", "in_progress", "on_hold", "completed", "cancelled"]},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
                    "start_date": {"type": "string", "format": "date-time"},
                    "end_date": {"type": "string", "format": "date-time"},
                    "tags": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="list_projects",
            description="List all projects or filter by status",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["not_started", "in_progress", "on_hold", "completed", "cancelled"]}
                }
            }
        ),
        Tool(
            name="get_project",
            description="Get details of a specific project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"}
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="update_project",
            description="Update a project's information",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "status": {"type": "string", "enum": ["not_started", "in_progress", "on_hold", "completed", "cancelled"]},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
                    "progress": {"type": "integer", "minimum": 0, "maximum": 100},
                    "notes": {"type": "string"}
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="add_project_task",
            description="Add a task to a project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "status": {"type": "string", "enum": ["todo", "in_progress", "done", "blocked"]},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
                    "due_date": {"type": "string", "format": "date-time"}
                },
                "required": ["project_id", "title"]
            }
        ),
        Tool(
            name="create_todo",
            description="Create a new todo/reminder",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "due_date": {"type": "string", "format": "date-time"},
                    "reminder_date": {"type": "string", "format": "date-time"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
                    "tags": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["title"]
            }
        ),
        Tool(
            name="list_todos",
            description="List todos, optionally filtered by completion status",
            inputSchema={
                "type": "object",
                "properties": {
                    "completed": {"type": "boolean"}
                }
            }
        ),
        Tool(
            name="complete_todo",
            description="Mark a todo as completed",
            inputSchema={
                "type": "object",
                "properties": {
                    "todo_id": {"type": "string"}
                },
                "required": ["todo_id"]
            }
        ),
        Tool(
            name="create_calendar_event",
            description="Create a calendar event",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "start_time": {"type": "string", "format": "date-time"},
                    "end_time": {"type": "string", "format": "date-time"},
                    "location": {"type": "string"},
                    "attendees": {"type": "array", "items": {"type": "string"}},
                    "reminder_minutes": {"type": "integer"}
                },
                "required": ["title", "start_time", "end_time"]
            }
        ),
        Tool(
            name="list_calendar_events",
            description="List calendar events within a date range",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "format": "date-time"},
                    "end_date": {"type": "string", "format": "date-time"}
                }
            }
        ),
        Tool(
            name="upload_document",
            description="Upload a document to the personal assistant",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content_base64": {"type": "string", "description": "Base64 encoded file content"},
                    "description": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["title", "content_base64"]
            }
        ),
        Tool(
            name="create_external_document",
            description="Create a reference to an external document (e.g., cloud storage link)",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "external_url": {"type": "string"},
                    "description": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["title", "external_url"]
            }
        ),
        Tool(
            name="list_documents",
            description="List all documents, optionally filtered by tags",
            inputSchema={
                "type": "object",
                "properties": {
                    "tags": {"type": "array", "items": {"type": "string"}}
                }
            }
        ),
        Tool(
            name="get_document",
            description="Get details of a specific document",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {"type": "string"}
                },
                "required": ["document_id"]
            }
        ),
        Tool(
            name="get_dashboard",
            description="Get a dashboard view of active projects, upcoming todos, and events",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict) -> List[TextContent]:
    """Handle tool calls"""
    
    if name == "get_status":
        status = db.get_status()
        # Add system information
        status_dict = status.model_dump()
        status_dict["system_info"] = {
            "database_type": get_config().database.type,
            "storage_directory": get_config().storage.documents_dir,
            "encryption_enabled": bool(get_config().database.encryption_key)
        }
        return [TextContent(
            type="text",
            text=json.dumps(status_dict, default=str, indent=2)
        )]
    
    elif name == "update_status":
        current_status = db.get_status()
        
        # Update fields if provided
        if "name" in arguments:
            current_status.name = arguments["name"]
        
        if any(key in arguments for key in ["city", "state", "country"]):
            if not current_status.current_location:
                current_status.current_location = Location()
            if "city" in arguments:
                current_status.current_location.city = arguments["city"]
            if "state" in arguments:
                current_status.current_location.state = arguments["state"]
            if "country" in arguments:
                current_status.current_location.country = arguments["country"]
        
        if any(key in arguments for key in ["laptop_os", "laptop_model"]):
            if not current_status.laptop_details:
                current_status.laptop_details = LaptopDetails()
            if "laptop_os" in arguments:
                current_status.laptop_details.os = arguments["laptop_os"]
            if "laptop_model" in arguments:
                current_status.laptop_details.model = arguments["laptop_model"]
        
        if "notes" in arguments:
            current_status.notes = arguments["notes"]
        
        current_status.last_updated = datetime.now()
        updated_status = db.update_status(current_status)
        
        return [TextContent(
            type="text",
            text=json.dumps(updated_status.model_dump(), default=str, indent=2)
        )]
    
    elif name == "create_project":
        project = Project(
            id=str(uuid4()),
            name=arguments["name"],
            description=arguments.get("description"),
            status=ProjectStatus(arguments.get("status", "not_started")),
            priority=Priority(arguments.get("priority", "medium")),
            start_date=datetime.fromisoformat(arguments["start_date"]) if "start_date" in arguments else None,
            end_date=datetime.fromisoformat(arguments["end_date"]) if "end_date" in arguments else None,
            tags=arguments.get("tags", [])
        )
        
        created_project = db.create_project(project)
        
        # Update active projects in status
        status = db.get_status()
        if created_project.id not in status.active_projects:
            status.active_projects.append(created_project.id)
            db.update_status(status)
        
        return [TextContent(
            type="text",
            text=json.dumps(created_project.model_dump(), default=str, indent=2)
        )]
    
    elif name == "list_projects":
        status_filter = ProjectStatus(arguments["status"]) if "status" in arguments else None
        projects = db.list_projects(status_filter)
        
        return [TextContent(
            type="text",
            text=json.dumps([p.model_dump() for p in projects], default=str, indent=2)
        )]
    
    elif name == "get_project":
        project = db.get_project(arguments["project_id"])
        if not project:
            return [TextContent(type="text", text="Project not found")]
        
        return [TextContent(
            type="text",
            text=json.dumps(project.model_dump(), default=str, indent=2)
        )]
    
    elif name == "update_project":
        project = db.get_project(arguments["project_id"])
        if not project:
            return [TextContent(type="text", text="Project not found")]
        
        # Update fields if provided
        if "name" in arguments:
            project.name = arguments["name"]
        if "description" in arguments:
            project.description = arguments["description"]
        if "status" in arguments:
            project.status = ProjectStatus(arguments["status"])
        if "priority" in arguments:
            project.priority = Priority(arguments["priority"])
        if "progress" in arguments:
            project.progress = arguments["progress"]
        if "notes" in arguments:
            project.notes = arguments["notes"]
        
        project.updated_at = datetime.now()
        updated_project = db.update_project(project)
        
        return [TextContent(
            type="text",
            text=json.dumps(updated_project.model_dump(), default=str, indent=2)
        )]
    
    elif name == "add_project_task":
        project = db.get_project(arguments["project_id"])
        if not project:
            return [TextContent(type="text", text="Project not found")]
        
        task = Task(
            id=str(uuid4()),
            title=arguments["title"],
            description=arguments.get("description"),
            status=TaskStatus(arguments.get("status", "todo")),
            priority=Priority(arguments.get("priority", "medium")),
            due_date=datetime.fromisoformat(arguments["due_date"]) if "due_date" in arguments else None
        )
        
        project.tasks.append(task)
        project.updated_at = datetime.now()
        updated_project = db.update_project(project)
        
        return [TextContent(
            type="text",
            text=json.dumps(updated_project.model_dump(), default=str, indent=2)
        )]
    
    elif name == "create_todo":
        todo = Todo(
            id=str(uuid4()),
            title=arguments["title"],
            description=arguments.get("description"),
            due_date=datetime.fromisoformat(arguments["due_date"]) if "due_date" in arguments else None,
            reminder_date=datetime.fromisoformat(arguments["reminder_date"]) if "reminder_date" in arguments else None,
            priority=Priority(arguments.get("priority", "medium")),
            tags=arguments.get("tags", [])
        )
        
        created_todo = db.create_todo(todo)
        
        return [TextContent(
            type="text",
            text=json.dumps(created_todo.model_dump(), default=str, indent=2)
        )]
    
    elif name == "list_todos":
        completed_filter = arguments.get("completed")
        todos = db.list_todos(completed_filter)
        
        return [TextContent(
            type="text",
            text=json.dumps([t.model_dump() for t in todos], default=str, indent=2)
        )]
    
    elif name == "complete_todo":
        todo = db.get_todo(arguments["todo_id"])
        if not todo:
            return [TextContent(type="text", text="Todo not found")]
        
        todo.completed = True
        todo.completed_at = datetime.now()
        updated_todo = db.update_todo(todo)
        
        return [TextContent(
            type="text",
            text=json.dumps(updated_todo.model_dump(), default=str, indent=2)
        )]
    
    elif name == "create_calendar_event":
        event = CalendarEvent(
            id=str(uuid4()),
            title=arguments["title"],
            description=arguments.get("description"),
            start_time=datetime.fromisoformat(arguments["start_time"]),
            end_time=datetime.fromisoformat(arguments["end_time"]),
            location=arguments.get("location"),
            attendees=arguments.get("attendees", []),
            reminder_minutes=arguments.get("reminder_minutes", 15)
        )
        
        created_event = db.create_event(event)
        
        return [TextContent(
            type="text",
            text=json.dumps(created_event.model_dump(), default=str, indent=2)
        )]
    
    elif name == "list_calendar_events":
        start_date = datetime.fromisoformat(arguments["start_date"]) if "start_date" in arguments else None
        end_date = datetime.fromisoformat(arguments["end_date"]) if "end_date" in arguments else None
        
        events = db.list_events(start_date, end_date)
        
        return [TextContent(
            type="text",
            text=json.dumps([e.model_dump() for e in events], default=str, indent=2)
        )]
    
    elif name == "upload_document":
        try:
            # Decode base64 content
            content_bytes = base64.b64decode(arguments["content_base64"])
            file_obj = BytesIO(content_bytes)
            
            # Store the document
            document = doc_manager.store_document(
                file_obj=file_obj,
                original_filename=arguments["title"],
                metadata={
                    "description": arguments.get("description", ""),
                    "tags": arguments.get("tags", [])
                }
            )
            
            # Update document with provided information
            document.description = arguments.get("description")
            document.tags = arguments.get("tags", [])
            
            # Save to database
            created_document = db.create_document(document)
            
            return [TextContent(
                type="text",
                text=json.dumps(created_document.model_dump(), default=str, indent=2)
            )]
        except Exception as e:
            return [TextContent(type="text", text=f"Error uploading document: {str(e)}")]
    
    elif name == "create_external_document":
        document = Document(
            id=str(uuid4()),
            title=arguments["title"],
            description=arguments.get("description"),
            file_path="",  # No local file for external documents
            document_type="other",
            size_bytes=0,
            external_url=arguments["external_url"],
            tags=arguments.get("tags", [])
        )
        
        created_document = db.create_document(document)
        
        return [TextContent(
            type="text",
            text=json.dumps(created_document.model_dump(), default=str, indent=2)
        )]
    
    elif name == "list_documents":
        tags_filter = arguments.get("tags")
        documents = db.list_documents(tags_filter)
        
        return [TextContent(
            type="text",
            text=json.dumps([d.model_dump() for d in documents], default=str, indent=2)
        )]
    
    elif name == "get_document":
        document = db.get_document(arguments["document_id"])
        if not document:
            return [TextContent(type="text", text="Document not found")]
        
        return [TextContent(
            type="text",
            text=json.dumps(document.model_dump(), default=str, indent=2)
        )]
    
    elif name == "get_dashboard":
        status = db.get_status()
        active_projects = [db.get_project(pid) for pid in status.active_projects if db.get_project(pid)]
        upcoming_todos = [t for t in db.list_todos(completed=False) if t.due_date and t.due_date <= datetime.now() + timedelta(days=7)]
        upcoming_events = db.list_events(datetime.now(), datetime.now() + timedelta(days=7))
        recent_documents = sorted(db.list_documents(), key=lambda d: d.created_at, reverse=True)[:5]
        
        dashboard = {
            "user_name": status.name,
            "current_location": status.current_location.model_dump() if status.current_location else None,
            "permissions": status.permissions.model_dump(),
            "active_projects": [p.model_dump() for p in active_projects if p],
            "upcoming_todos": [t.model_dump() for t in upcoming_todos],
            "upcoming_events": [e.model_dump() for e in upcoming_events],
            "recent_documents": [d.model_dump() for d in recent_documents],
            "statistics": {
                "total_projects": len(db.list_projects()),
                "active_projects": len([p for p in db.list_projects() if p.status == ProjectStatus.IN_PROGRESS]),
                "pending_todos": len(db.list_todos(completed=False)),
                "completed_todos": len(db.list_todos(completed=True)),
                "total_documents": len(db.list_documents())
            }
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(dashboard, default=str, indent=2)
        )]
    
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

# Cleanup on shutdown
import atexit
atexit.register(lambda: db.close())

if __name__ == "__main__":
    asyncio.run(main())
