# MCP Personal Assistant Migration Guide

## Database Migration

### Migrating from TinyDB to SQLite

If you started with TinyDB and want to switch to SQLite for better performance:

1. **Export data from TinyDB**:
   ```python
   # export_data.py
   import json
   from src.tinydb_database import TinyDBDatabase
   
   # Initialize TinyDB
   db = TinyDBDatabase("path/to/tinydb.json")
   
   # Export all data
   export_data = {
       "status": db.get_status().model_dump(),
       "projects": [p.model_dump() for p in db.list_projects()],
       "todos": [t.model_dump() for t in db.list_todos()],
       "events": [e.model_dump() for e in db.list_events()],
       "documents": [d.model_dump() for d in db.list_documents()]
   }
   
   # Save to file
   with open("export.json", "w") as f:
       json.dump(export_data, f, indent=2, default=str)
   ```

2. **Import data to SQLite**:
   ```python
   # import_data.py
   import json
   from datetime import datetime
   from src.sqlite_database import SQLiteDatabase
   from src.models import UserStatus, Project, Todo, CalendarEvent, Document
   
   # Load exported data
   with open("export.json", "r") as f:
       data = json.load(f)
   
   # Initialize SQLite
   db = SQLiteDatabase("path/to/sqlite.db")
   
   # Import status
   if "status" in data:
       status = UserStatus(**data["status"])
       db.update_status(status)
   
   # Import projects
   for project_data in data.get("projects", []):
       project = Project(**project_data)
       db.create_project(project)
   
   # Import todos
   for todo_data in data.get("todos", []):
       todo = Todo(**todo_data)
       db.create_todo(todo)
   
   # Import events
   for event_data in data.get("events", []):
       # Convert date strings to datetime objects
       event_data["start_time"] = datetime.fromisoformat(event_data["start_time"])
       event_data["end_time"] = datetime.fromisoformat(event_data["end_time"])
       event = CalendarEvent(**event_data)
       db.create_event(event)
   
   # Import documents
   for doc_data in data.get("documents", []):
       document = Document(**doc_data)
       db.create_document(document)
   ```

3. **Update configuration**:
   ```bash
   export MCP_PA_DB_TYPE=sqlite
   export MCP_PA_DB_PATH=/path/to/sqlite.db
   ```

### Adding Encryption to Existing Database

To add encryption to an existing database:

1. **For TinyDB**:
   ```bash
   # First, backup your database
   cp database.json database.json.backup
   
   # Set encryption key
   export MCP_PA_ENCRYPTION_KEY="your-secure-key"
   
   # Run migration script
   python migrate_encrypt.py
   ```

2. **For SQLite**:
   SQLite encryption requires SQLCipher. If unavailable, consider migrating to TinyDB with encryption:
   ```bash
   # Export from SQLite
   export MCP_PA_DB_TYPE=sqlite
   python export_data.py
   
   # Import to encrypted TinyDB
   export MCP_PA_DB_TYPE=tinydb
   export MCP_PA_ENCRYPTION_KEY="your-secure-key"
   python import_data.py
   ```

### Version Migrations

When upgrading between versions, always:

1. **Backup your data**:
   ```bash
   # For SQLite
   cp database.sqlite database.sqlite.backup
   
   # For TinyDB
   cp database.json database.json.backup
   
   # For documents
   tar -czf documents.tar.gz documents/
   ```

2. **Check for migration scripts**:
   ```bash
   # Look for version-specific migrations
   ls migrations/
   ```

3. **Run migrations in order**:
   ```bash
   python migrations/v1_to_v2.py
   python migrations/v2_to_v3.py
   ```

### Document Storage Migration

To migrate documents to a new location:

1. **Move existing documents**:
   ```bash
   # Create new directory
   mkdir -p /new/document/path
   
   # Copy documents
   cp -r /old/document/path/* /new/document/path/
   
   # Update configuration
   export MCP_PA_DOCS_DIR=/new/document/path
   ```

2. **Update document references**:
   ```python
   # update_doc_paths.py
   from src.database_factory import get_database
   
   db = get_database()
   
   for doc in db.list_documents():
       # Update file paths
       old_path = doc.file_path
       new_path = old_path.replace("/old/path", "/new/path")
       doc.file_path = new_path
       db.update_document(doc)
   ```

### Troubleshooting Migration Issues

#### Common Problems

1. **"Database version mismatch"**
   - Check if you're running the correct migration scripts
   - Verify database version in metadata

2. **"Encryption key error"**
   - Ensure you're using the same encryption key
   - Check if the database was previously encrypted

3. **"Document not found"**
   - Verify document paths are updated correctly
   - Check file permissions in new location

#### Recovery Steps

If migration fails:

1. **Restore from backup**:
   ```bash
   # Restore database
   cp database.backup database.sqlite
   
   # Restore documents
   tar -xzf documents.tar.gz
   ```

2. **Check logs for errors**:
   ```bash
   # Enable debug logging
   export MCP_PA_LOG_LEVEL=DEBUG
   python -m src.server
   ```

3. **Manual data recovery**:
   ```python
   # For corrupted SQLite
   import sqlite3
   
   conn = sqlite3.connect('corrupted.db')
   conn.execute('PRAGMA integrity_check')
   
   # Export what can be salvaged
   cursor = conn.execute('SELECT * FROM projects')
   salvaged_data = cursor.fetchall()
   ```

### Best Practices

1. **Always backup before migration**
2. **Test migrations on a copy first**
3. **Document custom modifications**
4. **Keep track of encryption keys**
5. **Verify data integrity after migration**

### Migration Scripts

Create standardized migration scripts:

```python
# migrations/base_migration.py
class BaseMigration:
    def __init__(self, source_db, target_db):
        self.source = source_db
        self.target = target_db
    
    def migrate(self):
        self.backup()
        self.transform()
        self.validate()
    
    def backup(self):
        """Create backup before migration"""
        pass
    
    def transform(self):
        """Transform data between formats"""
        pass
    
    def validate(self):
        """Validate migrated data"""
        pass
```

### Automated Migration Tool

For complex migrations:

```python
# migrate.py
import argparse
from src.database_factory import get_database

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--from', dest='from_type', required=True)
    parser.add_argument('--to', dest='to_type', required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--target', required=True)
    
    args = parser.parse_args()
    
    # Perform migration
    source_db = get_database(args.from_type, args.source)
    target_db = get_database(args.to_type, args.target)
    
    # Migrate data...
    
if __name__ == "__main__":
    main()
```

### Post-Migration Checklist

- [ ] All data successfully migrated
- [ ] No data loss or corruption
- [ ] Document paths updated
- [ ] Encryption working (if enabled)
- [ ] Application functions normally
- [ ] Backups are secure
- [ ] Documentation updated
