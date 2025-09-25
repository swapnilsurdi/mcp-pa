# MCP Personal Assistant

A comprehensive MCP (Model Context Protocol) server for personal productivity management, including status tracking, project management, todos, calendar functionality, and document storage.

## Features

### 🔍 Status Management
- Track your current location, laptop details, and system permissions
- View a dashboard of active projects and upcoming tasks
- Update your personal information and system status

### 📋 Project Management
- Create and manage projects with customizable status and priority
- Add tasks to projects with due dates and priorities
- Track project progress with percentage completion
- Filter projects by status (not started, in progress, on hold, completed, cancelled)

### ✅ Todo Management
- Create and manage todos with due dates and reminders
- Set priority levels (low, medium, high, urgent)
- Mark todos as completed
- Filter todos by completion status

### 📅 Calendar Management
- Create calendar events with start/end times
- Set event locations and attendee lists
- Configure reminder notifications
- View events within date ranges

### 📄 Document Management
- Upload and store documents (PDFs, images, text files, etc.)
- Create references to external documents (cloud storage links)
- Tag and organize documents
- Support for encrypted storage
- Automatic file type detection and categorization

## Installation

1. Clone or download this repository to your local machine
2. Install the required dependencies:

```bash
cd /Users/surdi/Documents/mcp-pa
pip install -r requirements.txt
```

## Configuration

The MCP server can be configured using environment variables:

### Database Configuration
- `MCP_PA_DB_TYPE`: Database type (`sqlite` or `tinydb`, default: `sqlite`)
- `MCP_PA_DB_PATH`: Custom database file path
- `MCP_PA_ENCRYPTION_KEY`: Encryption key for database (optional)

### Storage Configuration
- `MCP_PA_DOCS_DIR`: Directory for document storage
- `MCP_PA_MAX_FILE_SIZE_MB`: Maximum file size in MB (default: 100)

### Default Locations
- **macOS**: `~/Library/Application Support/mcp-pa/`
- **Linux**: `~/.config/mcp-pa/`
- **Windows**: `%APPDATA%\mcp-pa\`

To use specific settings:
```bash
export MCP_PA_DB_TYPE=sqlite
export MCP_PA_ENCRYPTION_KEY=mysecretkey
export MCP_PA_DOCS_DIR=/path/to/documents
```

## Claude Desktop Configuration

To use this MCP server with Claude Desktop, add the following to your configuration file:

```json
{
  "mcpServers": {
    "personal-assistant": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/Users/surdi/Documents/mcp-pa",
      "env": {
        "MCP_PA_DB_TYPE": "sqlite",
        "MCP_PA_ENCRYPTION_KEY": "your-secret-key"
      }
    }
  }
}
```

The configuration file is located at:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`  
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

## Available Tools

### Status Management

#### `get_status`
Get your current status including location, laptop details, permissions, and system information.

#### `update_status`
Update your status information.

### Project Management

#### `create_project`
Create a new project with name, description, status, priority, dates, and tags.

#### `list_projects`
List all projects or filter by status.

#### `get_project`
Get detailed information about a specific project.

#### `update_project`
Update project information including status, priority, and progress.

#### `add_project_task`
Add a task to a project.

### Todo Management

#### `create_todo`
Create a new todo with title, description, due date, priority, and tags.

#### `list_todos`
List all todos with optional completion status filter.

#### `complete_todo`
Mark a todo as completed.

### Calendar Management

#### `create_calendar_event`
Create a calendar event with start/end times, location, and attendees.

#### `list_calendar_events`
List calendar events within a date range.

### Document Management

#### `upload_document`
Upload a document with base64 encoded content.
```
Parameters:
- title: Document filename
- content_base64: Base64 encoded file content
- description: Optional description
- tags: Optional tags array
```

#### `create_external_document`
Create a reference to an external document.
```
Parameters:
- title: Document title
- external_url: URL to external document
- description: Optional description
- tags: Optional tags array
```

#### `list_documents`
List all documents with optional tag filtering.

#### `get_document`
Get detailed information about a specific document.

### Dashboard

#### `get_dashboard`
Get a comprehensive dashboard view of all activities.

## Database Support

### SQLite (Default)
- Better performance for larger datasets
- ACID compliance with transaction support
- Thread-safe with connection pooling
- Efficient concurrent access
- Supports database encryption

### TinyDB
- Simple JSON-based storage
- Human-readable database file
- Supports encryption via Fernet
- Good for smaller datasets
- Easy to backup and inspect

## Document Storage

The document manager supports:
- Automatic file type detection
- SHA-256 checksum calculation
- File size validation
- Metadata tagging
- External document references

Supported document types:
- PDF files
- Images (JPEG, PNG, etc.)
- Text files
- Spreadsheets (Excel, CSV)
- Presentations (PowerPoint)
- Other file types

## Security Features

### Database Encryption
- SQLite: Can use SQLCipher for encryption (if available)
- TinyDB: Uses Fernet symmetric encryption
- Encryption key configurable via environment variable

### Document Security
- Files stored with unique IDs
- Original filenames preserved in metadata
- Checksum verification for integrity
- File size limits enforced

## Advanced Usage

### Using with Multiple Instances
The server supports concurrent access from multiple clients:
- SQLite uses connection pooling
- TinyDB uses thread-safe locking
- Both handle concurrent read/write operations

### Custom Database Location
```bash
export MCP_PA_DB_PATH=/custom/path/database.sqlite
```

### Encrypted Database
```bash
export MCP_PA_ENCRYPTION_KEY=your-secure-key-here
```

## Development

### Project Structure
```
mcp-pa/
├── src/
│   ├── __init__.py
│   ├── server.py              # Main MCP server
│   ├── config.py              # Configuration management
│   ├── models.py              # Data models
│   ├── database_interface.py  # Database interface
│   ├── database_factory.py    # Database factory
│   ├── sqlite_database.py     # SQLite implementation
│   ├── tinydb_database.py     # TinyDB implementation
│   └── document_manager.py    # Document management
├── data/                      # Default data directory
├── tests/                     # Test files
├── pyproject.toml            # Project configuration
└── requirements.txt          # Dependencies
```

### Running Tests
```bash
python test_server.py
```

### Building the Package
```bash
pip install build
python -m build
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details.

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Ensure the database directory exists
   - Check file permissions
   - Verify encryption key if using encryption

2. **Document Upload Failures**
   - Check file size limits
   - Ensure documents directory is writable
   - Verify base64 encoding is correct

3. **Configuration Problems**
   - Check environment variables
   - Verify the configuration file syntax
   - Ensure all required directories exist

### Debug Mode

Enable debug logging by setting the logging level in your application:
```python
server.set_logging_level(LoggingLevel.DEBUG)
```

## Future Enhancements

- [ ] File preview generation
- [ ] Full-text search across documents
- [ ] Automatic backup system
- [ ] OAuth integration for cloud storage
- [ ] Web interface for direct access
- [ ] Plugin system for extensibility
- [ ] Real-time notifications
- [ ] Database migration tools

## Support

For issues and feature requests, please create an issue in the GitHub repository.
