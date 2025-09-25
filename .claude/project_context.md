# MCP Personal Assistant - Claude Project Context

This project provides a comprehensive MCP (Model Context Protocol) server for personal productivity management through Claude Desktop.

## Quick Commands

### Status & Dashboard
- "What's my current status?" - View info, location, permissions, and system details
- "Show me my dashboard" - Get overview of projects, todos, calendar, and recent documents
- "Update my status..." - Update location, laptop details, or notes

### Projects
- "Create a project called [name]" - Create new project with optional priority/description
- "Show me all active projects" - List projects by status
- "Update [project] progress to 50%" - Update project details
- "Add task '[title]' to [project]" - Add tasks to projects

### Todos
- "Create a todo: [title], due [date]" - Create todos with priorities and due dates
- "Show me pending todos" - List incomplete todos
- "Mark [todo] as completed" - Complete todos

### Calendar
- "Schedule [event] tomorrow at 2 PM" - Create calendar events with times
- "Show me this week's events" - View calendar by date range
- "Add a meeting with [attendees]" - Create events with attendee lists

### Documents
- "Store this document" - Upload a document (provide base64 content)
- "Create a reference to [URL]" - Reference external documents
- "Show me all documents" - List all stored documents
- "Find documents tagged with [tag]" - Search by tags

## Available MCP Tools

**Status Management:**
- `get_status` - View current status with system info
- `update_status` - Update user information

**Project Management:**
- `create_project` - Create new projects
- `list_projects` - List projects (filter by status)
- `get_project` - Get project details
- `update_project` - Update project info
- `add_project_task` - Add tasks to projects

**Todo Management:**
- `create_todo` - Create todos/reminders
- `list_todos` - List todos (filter by completion)
- `complete_todo` - Mark todos as done

**Calendar Management:**
- `create_calendar_event` - Schedule events
- `list_calendar_events` - View calendar by date range

**Document Management:**
- `upload_document` - Upload documents (base64 encoded)
- `create_external_document` - Reference external documents
- `list_documents` - List documents (filter by tags)
- `get_document` - Get document details

**Dashboard:**
- `get_dashboard` - Comprehensive overview of all activities

## Technical Details

**Database Support:**
- SQLite (default) - Better performance, ACID compliance, thread-safe
- TinyDB - JSON-based, human-readable, good for smaller datasets

**Security Features:**
- Optional database encryption via `MCP_PA_ENCRYPTION_KEY`
- Document storage with checksums and unique IDs
- File size limits and type validation

**Configuration:**
- `MCP_PA_DB_TYPE` - Database type (sqlite/tinydb)
- `MCP_PA_ENCRYPTION_KEY` - Encryption key for secure storage
- `MCP_PA_DOCS_DIR` - Custom document storage directory
- `MCP_PA_MAX_FILE_SIZE_MB` - Maximum file size limit

## Usage Notes

- Use natural language - the assistant parses requests automatically
- Data persists across sessions in local database
- Supports concurrent access from multiple clients
- Documents stored with metadata, tags, and integrity checksums
- All dates handled in ISO format internally
- Assistant manages IDs automatically for user convenience