# MCP Personal Assistant Configuration Guide

## Environment Variables

The MCP Personal Assistant can be configured using environment variables. Here's a comprehensive guide:

### Database Configuration

#### `MCP_PA_DB_TYPE`
- **Description**: Database type to use
- **Options**: `sqlite` (default), `tinydb`
- **Example**: `export MCP_PA_DB_TYPE=sqlite`

#### `MCP_PA_DB_PATH`
- **Description**: Custom path for the database file
- **Default**: 
  - SQLite: `~/Library/Application Support/mcp-pa/database.sqlite`
  - TinyDB: `~/Library/Application Support/mcp-pa/database.json`
- **Example**: `export MCP_PA_DB_PATH=/custom/path/mydata.db`

#### `MCP_PA_ENCRYPTION_KEY`
- **Description**: Encryption key for database (optional)
- **Default**: None (no encryption)
- **Example**: `export MCP_PA_ENCRYPTION_KEY=my-secure-key-123`
- **Note**: If set, all data will be encrypted at rest

### Storage Configuration

#### `MCP_PA_DOCS_DIR`
- **Description**: Directory for document storage
- **Default**: `~/Library/Application Support/mcp-pa/documents`
- **Example**: `export MCP_PA_DOCS_DIR=/Users/myuser/Documents/MCP`

#### `MCP_PA_MAX_FILE_SIZE_MB`
- **Description**: Maximum file size for uploaded documents in MB
- **Default**: `100`
- **Example**: `export MCP_PA_MAX_FILE_SIZE_MB=50`

## Configuration Examples

### Basic Configuration
```bash
# Use default settings
python -m src.server
```

### Encrypted SQLite Configuration
```bash
export MCP_PA_DB_TYPE=sqlite
export MCP_PA_ENCRYPTION_KEY=my-secure-key-123
export MCP_PA_DOCS_DIR=/secure/documents
python -m src.server
```

### TinyDB with Custom Paths
```bash
export MCP_PA_DB_TYPE=tinydb
export MCP_PA_DB_PATH=/Users/myuser/mcp/data.json
export MCP_PA_DOCS_DIR=/Users/myuser/mcp/documents
python -m src.server
```

### Maximum Security Configuration
```bash
export MCP_PA_DB_TYPE=sqlite
export MCP_PA_ENCRYPTION_KEY=$(openssl rand -base64 32)
export MCP_PA_DOCS_DIR=/secure/encrypted/documents
export MCP_PA_MAX_FILE_SIZE_MB=25
python -m src.server
```

## Claude Desktop Configuration

Add environment variables to your Claude Desktop config:

```json
{
  "mcpServers": {
    "personal-assistant": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/mcp-pa",
      "env": {
        "MCP_PA_DB_TYPE": "sqlite",
        "MCP_PA_ENCRYPTION_KEY": "your-secret-key",
        "MCP_PA_DOCS_DIR": "/custom/documents/path",
        "MCP_PA_MAX_FILE_SIZE_MB": "50"
      }
    }
  }
}
```

## Default Paths by Operating System

### macOS
- Database: `~/Library/Application Support/mcp-pa/database.sqlite`
- Documents: `~/Library/Application Support/mcp-pa/documents`

### Linux
- Database: `~/.config/mcp-pa/database.sqlite`
- Documents: `~/.config/mcp-pa/documents`

### Windows
- Database: `%APPDATA%\mcp-pa\database.sqlite`
- Documents: `%APPDATA%\mcp-pa\documents`

## Database Comparison

### SQLite
Advantages:
- Better performance with large datasets
- ACID compliance
- Built-in support for concurrent access
- Efficient querying
- Transaction support

Disadvantages:
- Binary format (not human-readable)
- Requires SQLite knowledge for manual inspection

### TinyDB
Advantages:
- Human-readable JSON format
- Simple to backup and inspect
- No additional dependencies
- Easy to modify manually if needed

Disadvantages:
- Performance degrades with large datasets
- Limited querying capabilities
- File locking for concurrent access

## Security Considerations

1. **Encryption Key Management**
   - Store encryption keys securely
   - Don't commit keys to version control
   - Consider using a key management service

2. **File Permissions**
   - Ensure database and document directories have appropriate permissions
   - Restrict access to sensitive data

3. **Backup Strategy**
   - Regular backups of both database and documents
   - Test backup restoration procedures
   - Consider encrypted backups

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```
   Error: Permission denied: /path/to/database
   ```
   Solution: Ensure the user has write permissions to the directory

2. **Encryption Key Errors**
   ```
   Error: Invalid encryption key
   ```
   Solution: Verify the encryption key matches the one used to create the database

3. **Database Corruption**
   ```
   Error: Database is corrupted
   ```
   Solution: Restore from backup or create a new database

### Debug Mode

Enable debug logging:
```python
server.set_logging_level(LoggingLevel.DEBUG)
```

## Migration Guide

### Switching from TinyDB to SQLite

1. Export data from TinyDB:
   ```bash
   export MCP_PA_DB_TYPE=tinydb
   python export_data.py > backup.json
   ```

2. Import to SQLite:
   ```bash
   export MCP_PA_DB_TYPE=sqlite
   python import_data.py backup.json
   ```

### Adding Encryption to Existing Database

1. Backup existing data
2. Set encryption key and restart server
3. Import backed up data

## Performance Tuning

### SQLite Optimization
```bash
# Enable Write-Ahead Logging
export SQLITE_JOURNAL_MODE=WAL

# Increase cache size
export SQLITE_CACHE_SIZE=10000
```

### File System Optimization
- Use SSD storage for database
- Regular defragmentation
- Monitor disk space

## Advanced Topics

### Custom Database Path Resolution
```python
import os
from pathlib import Path

def get_custom_db_path():
    if os.environ.get('MCP_PA_CUSTOM_ENV'):
        return Path.home() / 'custom' / 'database.sqlite'
    return None
```

### Database Backup Script
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
DB_PATH="$HOME/Library/Application Support/mcp-pa/database.sqlite"
BACKUP_PATH="$HOME/backups/mcp-pa_$DATE.sqlite"

cp "$DB_PATH" "$BACKUP_PATH"
echo "Backup created: $BACKUP_PATH"
```

## Best Practices

1. Always use encryption for sensitive data
2. Regular backups with rotation policy
3. Monitor disk space usage
4. Use appropriate file size limits
5. Keep encryption keys secure
6. Test disaster recovery procedures
7. Document your configuration
