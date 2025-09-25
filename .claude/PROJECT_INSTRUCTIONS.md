# Personal Assistant MCP Integration

This project has access to a Personal Assistant MCP server with productivity and document management tools.

## Quick Reference

### Status & Dashboard
- "What's my current status?" - View your info, location, permissions, and system details
- "Show me my dashboard" - Get overview of projects, todos, calendar, and recent documents
- "Update my status..." - Update location, laptop details, or notes

### Projects
- "Create a project called [name]" - Create new project
- "Show me all active projects" - List projects by status
- "Update [project] progress to 50%" - Update project details
- "Add task '[title]' to [project]" - Add tasks to projects

### Todos
- "Create a todo: [title], due [date]" - Create todos with priorities
- "Show me pending todos" - List incomplete todos
- "Mark [todo] as completed" - Complete todos

### Calendar
- "Schedule [event] tomorrow at 2 PM" - Create calendar events
- "Show me this week's events" - View calendar by date range
- "Add a meeting with [attendees]" - Create events with attendees

### Documents
- "Store this document" - Upload a document (provide base64 content)
- "Create a reference to [URL]" - Reference external documents
- "Show me all documents" - List all stored documents
- "Find documents tagged with [tag]" - Search by tags

## Configuration

The MCP server uses these settings:
- Database: SQLite (default) or TinyDB
- Encryption: Optional via `MCP_PA_ENCRYPTION_KEY`
- Document storage: Configurable via `MCP_PA_DOCS_DIR`

## Available Tools

1. **get_status** - View current status with system info
2. **update_status** - Update user information
3. **create_project** - Create new projects
4. **list_projects** - List projects (filter by status)
5. **get_project** - Get project details
6. **update_project** - Update project info
7. **add_project_task** - Add tasks to projects
8. **create_todo** - Create todos/reminders
9. **list_todos** - List todos (filter by completion)
10. **complete_todo** - Mark todos as done
11. **create_calendar_event** - Schedule events
12. **list_calendar_events** - View calendar
13. **upload_document** - Upload documents (base64)
14. **create_external_document** - Reference external docs
15. **list_documents** - List documents (filter by tags)
16. **get_document** - Get document details
17. **get_dashboard** - Comprehensive overview

## Document Management

Upload documents with base64 content:
```
"Store this document"
Then provide: title, content_base64, description, tags
```

Reference external documents:
```
"Create a reference to this Google Doc: [URL]"
```

Supported document types:
- PDFs
- Images (JPEG, PNG, etc.)
- Text files
- Spreadsheets (Excel, CSV)
- Presentations
- Other file types

## Notes

- Data is stored securely with optional encryption
- Multiple instances can access the same database
- Documents are stored with unique IDs and checksums
- Maximum file size is configurable (default: 100MB)
- All dates use ISO format
- The assistant handles ID management automatically
