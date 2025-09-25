import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
import threading
from .database_interface import DatabaseInterface
from .models import (
    UserStatus, Project, Task, Todo, CalendarEvent, Document,
    ProjectStatus, TaskStatus, Priority, DocumentType
)

class SQLiteDatabase(DatabaseInterface):
    def __init__(self, db_path: str, encryption_key: Optional[str] = None):
        self.db_path = db_path
        self.encryption_key = encryption_key
        self._local = threading.local()
        self.initialize()
    
    def _get_connection(self):
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                isolation_level=None  # Autocommit mode
            )
            self._local.connection.row_factory = sqlite3.Row
            
            # Enable foreign keys
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            
            # If encryption is enabled (using SQLCipher), set the key
            if self.encryption_key:
                try:
                    self._local.connection.execute(f"PRAGMA key = '{self.encryption_key}'")
                    # Test the key by trying to access the database
                    self._local.connection.execute("SELECT count(*) FROM sqlite_master")
                except sqlite3.DatabaseError:
                    # If the key is wrong or database is not encrypted, handle gracefully
                    pass
        
        return self._local.connection
    
    @contextmanager
    def _transaction(self):
        """Context manager for transactions"""
        conn = self._get_connection()
        try:
            conn.execute("BEGIN")
            yield conn
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    
    def initialize(self):
        """Initialize database schema"""
        conn = self._get_connection()
        
        # Create tables
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS user_status (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                data TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS todos (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS calendar_events (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL
            );
            
            -- Create indexes for common queries
            CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(id);
            CREATE INDEX IF NOT EXISTS idx_todos_completed ON todos(id);
            CREATE INDEX IF NOT EXISTS idx_calendar_events_dates ON calendar_events(id);
            CREATE INDEX IF NOT EXISTS idx_documents_tags ON documents(id);
        """)
        
        # Initialize default status if not exists
        cursor = conn.execute("SELECT COUNT(*) FROM user_status")
        if cursor.fetchone()[0] == 0:
            default_status = UserStatus(name="User")
            conn.execute(
                "INSERT INTO user_status (id, data) VALUES (1, ?)",
                (json.dumps(default_status.model_dump(), default=str),)
            )
    
    def _serialize(self, obj: Any) -> str:
        """Serialize object to JSON string"""
        if hasattr(obj, 'model_dump'):
            return json.dumps(obj.model_dump(), default=str)
        return json.dumps(obj, default=str)
    
    def _deserialize(self, data: str, model_class) -> Any:
        """Deserialize JSON string to object"""
        try:
            obj_dict = json.loads(data)
            # Convert ISO format strings back to datetime objects
            for key, value in obj_dict.items():
                if isinstance(value, str) and key.endswith(('_at', '_date', '_time')):
                    try:
                        obj_dict[key] = datetime.fromisoformat(value)
                    except ValueError:
                        pass
            return model_class(**obj_dict)
        except Exception as e:
            print(f"Deserialization error: {e}")
            raise
    
    # Status operations
    def get_status(self) -> UserStatus:
        conn = self._get_connection()
        cursor = conn.execute("SELECT data FROM user_status WHERE id = 1")
        row = cursor.fetchone()
        if row:
            return self._deserialize(row['data'], UserStatus)
        return UserStatus(name="User")
    
    def update_status(self, status: UserStatus) -> UserStatus:
        conn = self._get_connection()
        with self._transaction():
            conn.execute(
                "INSERT OR REPLACE INTO user_status (id, data) VALUES (1, ?)",
                (self._serialize(status),)
            )
        return status
    
    # Project operations
    def create_project(self, project: Project) -> Project:
        conn = self._get_connection()
        with self._transaction():
            conn.execute(
                "INSERT INTO projects (id, data) VALUES (?, ?)",
                (project.id, self._serialize(project))
            )
        return project
    
    def get_project(self, project_id: str) -> Optional[Project]:
        conn = self._get_connection()
        cursor = conn.execute("SELECT data FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        if row:
            return self._deserialize(row['data'], Project)
        return None
    
    def list_projects(self, status: Optional[ProjectStatus] = None) -> List[Project]:
        conn = self._get_connection()
        cursor = conn.execute("SELECT data FROM projects")
        projects = []
        for row in cursor:
            project = self._deserialize(row['data'], Project)
            if status is None or project.status == status:
                projects.append(project)
        return projects
    
    def update_project(self, project: Project) -> Project:
        conn = self._get_connection()
        with self._transaction():
            conn.execute(
                "UPDATE projects SET data = ? WHERE id = ?",
                (self._serialize(project), project.id)
            )
        return project
    
    def delete_project(self, project_id: str) -> bool:
        conn = self._get_connection()
        with self._transaction():
            cursor = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        return cursor.rowcount > 0
    
    # Todo operations
    def create_todo(self, todo: Todo) -> Todo:
        conn = self._get_connection()
        with self._transaction():
            conn.execute(
                "INSERT INTO todos (id, data) VALUES (?, ?)",
                (todo.id, self._serialize(todo))
            )
        return todo
    
    def get_todo(self, todo_id: str) -> Optional[Todo]:
        conn = self._get_connection()
        cursor = conn.execute("SELECT data FROM todos WHERE id = ?", (todo_id,))
        row = cursor.fetchone()
        if row:
            return self._deserialize(row['data'], Todo)
        return None
    
    def list_todos(self, completed: Optional[bool] = None) -> List[Todo]:
        conn = self._get_connection()
        cursor = conn.execute("SELECT data FROM todos")
        todos = []
        for row in cursor:
            todo = self._deserialize(row['data'], Todo)
            if completed is None or todo.completed == completed:
                todos.append(todo)
        return todos
    
    def update_todo(self, todo: Todo) -> Todo:
        conn = self._get_connection()
        with self._transaction():
            conn.execute(
                "UPDATE todos SET data = ? WHERE id = ?",
                (self._serialize(todo), todo.id)
            )
        return todo
    
    def delete_todo(self, todo_id: str) -> bool:
        conn = self._get_connection()
        with self._transaction():
            cursor = conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
        return cursor.rowcount > 0
    
    # Calendar operations
    def create_event(self, event: CalendarEvent) -> CalendarEvent:
        conn = self._get_connection()
        with self._transaction():
            conn.execute(
                "INSERT INTO calendar_events (id, data) VALUES (?, ?)",
                (event.id, self._serialize(event))
            )
        return event
    
    def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        conn = self._get_connection()
        cursor = conn.execute("SELECT data FROM calendar_events WHERE id = ?", (event_id,))
        row = cursor.fetchone()
        if row:
            return self._deserialize(row['data'], CalendarEvent)
        return None
    
    def list_events(self, start_date: Optional[datetime] = None, 
                   end_date: Optional[datetime] = None) -> List[CalendarEvent]:
        conn = self._get_connection()
        cursor = conn.execute("SELECT data FROM calendar_events")
        events = []
        for row in cursor:
            event = self._deserialize(row['data'], CalendarEvent)
            if start_date and event.start_time < start_date:
                continue
            if end_date and event.end_time > end_date:
                continue
            events.append(event)
        return sorted(events, key=lambda x: x.start_time)
    
    def update_event(self, event: CalendarEvent) -> CalendarEvent:
        conn = self._get_connection()
        with self._transaction():
            conn.execute(
                "UPDATE calendar_events SET data = ? WHERE id = ?",
                (self._serialize(event), event.id)
            )
        return event
    
    def delete_event(self, event_id: str) -> bool:
        conn = self._get_connection()
        with self._transaction():
            cursor = conn.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))
        return cursor.rowcount > 0
    
    # Document operations
    def create_document(self, document: Document) -> Document:
        conn = self._get_connection()
        with self._transaction():
            conn.execute(
                "INSERT INTO documents (id, data) VALUES (?, ?)",
                (document.id, self._serialize(document))
            )
        return document
    
    def get_document(self, document_id: str) -> Optional[Document]:
        conn = self._get_connection()
        cursor = conn.execute("SELECT data FROM documents WHERE id = ?", (document_id,))
        row = cursor.fetchone()
        if row:
            return self._deserialize(row['data'], Document)
        return None
    
    def list_documents(self, tags: Optional[List[str]] = None) -> List[Document]:
        conn = self._get_connection()
        cursor = conn.execute("SELECT data FROM documents")
        documents = []
        for row in cursor:
            document = self._deserialize(row['data'], Document)
            if tags is None or any(tag in document.tags for tag in tags):
                documents.append(document)
        return documents
    
    def update_document(self, document: Document) -> Document:
        conn = self._get_connection()
        with self._transaction():
            conn.execute(
                "UPDATE documents SET data = ? WHERE id = ?",
                (self._serialize(document), document.id)
            )
        return document
    
    def delete_document(self, document_id: str) -> bool:
        conn = self._get_connection()
        with self._transaction():
            cursor = conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        return cursor.rowcount > 0
    
    def close(self):
        """Close database connection"""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            delattr(self._local, 'connection')
