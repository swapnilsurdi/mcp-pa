"""
PostgreSQL + pgvector Database Implementation

Provides vector search capabilities and horizontal scaling support
for the Personal Assistant MCP server.
"""

import asyncio
import json
import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple
import uuid

import asyncpg
import numpy as np
from pgvector.asyncpg import register_vector

from .database_interface import DatabaseInterface
from .models import Project, Todo, CalendarEvent, StatusEntry, PersonalData

logger = logging.getLogger(__name__)

class PostgresDatabase(DatabaseInterface):
    """PostgreSQL database with pgvector for semantic search"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool: Optional[asyncpg.Pool] = None
        self.embedding_dimension = 1536  # OpenAI ada-002 dimensions
    
    async def connect(self) -> None:
        """Initialize database connection and setup tables"""
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            
            # Register vector type
            await register_vector(self.pool)
            
            # Extract schema from connection string if present
            self.schema = self._extract_schema_from_connection()
            
            # Initialize schema and tables
            await self._initialize_schema_and_tables()
            
            logger.info(f"Connected to PostgreSQL with pgvector, schema: {self.schema}")
            
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    def _extract_schema_from_connection(self) -> str:
        """Extract schema name from connection string for multi-tenancy"""
        import urllib.parse as urlparse
        
        try:
            parsed = urlparse.urlparse(self.connection_string)
            options = urlparse.parse_qs(parsed.query).get('options', [])
            
            for option in options:
                if 'search_path=' in option:
                    # Extract first schema from search_path
                    search_path = option.split('search_path=')[1]
                    schema = search_path.split(',')[0]
                    return schema
            
        except Exception as e:
            logger.debug(f"Could not extract schema from connection string: {e}")
        
        return "public"  # Default schema
    
    async def _initialize_schema_and_tables(self) -> None:
        """Create schema and initialize tables"""
        async with self.pool.acquire() as conn:
            # Create schema if it doesn't exist (for tenant isolation)
            if self.schema != "public":
                await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema}")
                await conn.execute(f"SET search_path TO {self.schema}, public")
            
            # Enable pgvector extension in current schema
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            
            await self._create_tables(conn)
    
    async def close(self) -> None:
        """Close database connections"""
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL connection closed")
    
    async def _create_tables(self, conn) -> None:
        """Create tables with vector columns for semantic search"""
        
        # Projects table with vector embeddings
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id VARCHAR PRIMARY KEY,
                name VARCHAR NOT NULL,
                description TEXT,
                status VARCHAR NOT NULL,
                priority VARCHAR NOT NULL,
                tags TEXT[],
                created_date TIMESTAMP NOT NULL,
                updated_date TIMESTAMP NOT NULL,
                embedding vector(1536),
                metadata JSONB DEFAULT '{}'::jsonb
            )
        """)

        # Create vector index for projects
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS projects_embedding_idx
            ON projects USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """)

        # Todos table with vector embeddings
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                    id VARCHAR PRIMARY KEY,
                    title VARCHAR NOT NULL,
                    description TEXT,
                    completed BOOLEAN NOT NULL DEFAULT FALSE,
                    priority VARCHAR NOT NULL DEFAULT 'medium',
                project_id VARCHAR,
                due_date TIMESTAMP,
                created_date TIMESTAMP NOT NULL,
                updated_date TIMESTAMP NOT NULL,
                embedding vector(1536),
                metadata JSONB DEFAULT '{}'::jsonb,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
            )
        """)

        # Create vector index for todos
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS todos_embedding_idx
            ON todos USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """)

        # Calendar events table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS calendar_events (
                    id VARCHAR PRIMARY KEY,
                    title VARCHAR NOT NULL,
                    description TEXT,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP NOT NULL,
                location VARCHAR,
                attendees TEXT[],
                created_date TIMESTAMP NOT NULL,
                updated_date TIMESTAMP NOT NULL,
                embedding vector(1536),
                metadata JSONB DEFAULT '{}'::jsonb
            )
        """)

        # Status entries table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS status_entries (
                id VARCHAR PRIMARY KEY,
                status VARCHAR NOT NULL,
                message TEXT,
                emoji VARCHAR,
                expiry_date TIMESTAMP,
                created_date TIMESTAMP NOT NULL,
                metadata JSONB DEFAULT '{}'::jsonb
            )
        """)

        # Personal data table for key-value storage
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS personal_data (
                key VARCHAR PRIMARY KEY,
                value JSONB NOT NULL,
                data_type VARCHAR NOT NULL,
                created_date TIMESTAMP NOT NULL,
                updated_date TIMESTAMP NOT NULL,
                metadata JSONB DEFAULT '{}'::jsonb
            )
        """)

        # Documents table for full-text and vector search
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id VARCHAR PRIMARY KEY,
                title VARCHAR NOT NULL,
                content TEXT NOT NULL,
                file_path VARCHAR,
                mime_type VARCHAR,
                size_bytes BIGINT,
                created_date TIMESTAMP NOT NULL,
                updated_date TIMESTAMP NOT NULL,
                embedding vector(1536),
                content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, ''))) STORED,
                metadata JSONB DEFAULT '{}'::jsonb
            )
        """)

        # Create GIN index for full-text search
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS documents_content_tsv_idx
            ON documents USING gin(content_tsv)
        """)

        # Create vector index for documents
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS documents_embedding_idx
            ON documents USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """)
    
    # Project operations
    async def add_project(self, project: Project) -> None:
        """Add project with vector embedding"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO projects (id, name, description, status, priority, tags, created_date, updated_date, embedding, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """, 
                project.id, project.name, project.description, project.status, project.priority,
                project.tags, project.created_date, project.updated_date, 
                getattr(project, 'embedding', None), json.dumps(getattr(project, 'metadata', {}))
            )
    
    async def get_projects(self, limit: Optional[int] = None) -> List[Project]:
        """Get all projects"""
        query = "SELECT * FROM projects ORDER BY updated_date DESC"
        if limit:
            query += f" LIMIT {limit}"
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [self._row_to_project(row) for row in rows]
    
    async def get_project_by_id(self, project_id: str) -> Optional[Project]:
        """Get project by ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM projects WHERE id = $1", project_id)
            return self._row_to_project(row) if row else None
    
    async def update_project(self, project: Project) -> None:
        """Update project"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE projects 
                SET name = $2, description = $3, status = $4, priority = $5, tags = $6, 
                    updated_date = $7, embedding = $8, metadata = $9
                WHERE id = $1
            """,
                project.id, project.name, project.description, project.status, project.priority,
                project.tags, project.updated_date,
                getattr(project, 'embedding', None), json.dumps(getattr(project, 'metadata', {}))
            )
    
    async def delete_project(self, project_id: str) -> None:
        """Delete project"""
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM projects WHERE id = $1", project_id)
    
    # Vector search methods
    async def semantic_search_projects(self, query_embedding: List[float], limit: int = 5, similarity_threshold: float = 0.7) -> List[Tuple[Project, float]]:
        """Perform semantic search on projects"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT *, 1 - (embedding <=> $1) as similarity
                FROM projects 
                WHERE embedding IS NOT NULL
                AND 1 - (embedding <=> $1) > $3
                ORDER BY embedding <=> $1
                LIMIT $2
            """, query_embedding, limit, similarity_threshold)
            
            return [(self._row_to_project(row), row['similarity']) for row in rows]
    
    async def semantic_search_todos(self, query_embedding: List[float], limit: int = 5, similarity_threshold: float = 0.7) -> List[Tuple[Todo, float]]:
        """Perform semantic search on todos"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT *, 1 - (embedding <=> $1) as similarity
                FROM todos 
                WHERE embedding IS NOT NULL
                AND 1 - (embedding <=> $1) > $3
                ORDER BY embedding <=> $1
                LIMIT $2
            """, query_embedding, limit, similarity_threshold)
            
            return [(self._row_to_todo(row), row['similarity']) for row in rows]
    
    async def semantic_search_documents(self, query_embedding: List[float], limit: int = 5, similarity_threshold: float = 0.7) -> List[Tuple[Dict, float]]:
        """Perform semantic search on documents"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT *, 1 - (embedding <=> $1) as similarity
                FROM documents 
                WHERE embedding IS NOT NULL
                AND 1 - (embedding <=> $1) > $3
                ORDER BY embedding <=> $1
                LIMIT $2
            """, query_embedding, limit, similarity_threshold)
            
            return [(dict(row), row['similarity']) for row in rows]
    
    async def hybrid_search_documents(self, query: str, query_embedding: List[float], limit: int = 5) -> List[Dict]:
        """Combine full-text search with vector search for documents"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT *, 
                    ts_rank(content_tsv, plainto_tsquery('english', $1)) as text_score,
                    1 - (embedding <=> $2) as semantic_score,
                    (ts_rank(content_tsv, plainto_tsquery('english', $1)) * 0.3 + 
                     (1 - (embedding <=> $2)) * 0.7) as combined_score
                FROM documents 
                WHERE content_tsv @@ plainto_tsquery('english', $1)
                   OR (embedding IS NOT NULL AND 1 - (embedding <=> $2) > 0.7)
                ORDER BY combined_score DESC
                LIMIT $3
            """, query, query_embedding, limit)
            
            return [dict(row) for row in rows]
    
    # Todo operations (implementing required interface methods)
    async def add_todo(self, todo: Todo) -> None:
        """Add todo with vector embedding"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO todos (id, title, description, completed, priority, project_id, due_date, created_date, updated_date, embedding, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
                todo.id, todo.title, todo.description, todo.completed, todo.priority,
                todo.project_id, todo.due_date, todo.created_date, todo.updated_date,
                getattr(todo, 'embedding', None), json.dumps(getattr(todo, 'metadata', {}))
            )
    
    async def get_todos(self, limit: Optional[int] = None, project_id: Optional[str] = None) -> List[Todo]:
        """Get todos with optional filtering"""
        base_query = "SELECT * FROM todos"
        params = []
        param_count = 0
        
        if project_id:
            param_count += 1
            base_query += f" WHERE project_id = ${param_count}"
            params.append(project_id)
        
        base_query += " ORDER BY created_date DESC"
        
        if limit:
            param_count += 1
            base_query += f" LIMIT ${param_count}"
            params.append(limit)
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(base_query, *params)
            return [self._row_to_todo(row) for row in rows]
    
    async def get_todo_by_id(self, todo_id: str) -> Optional[Todo]:
        """Get todo by ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM todos WHERE id = $1", todo_id)
            return self._row_to_todo(row) if row else None
    
    async def update_todo(self, todo: Todo) -> None:
        """Update todo"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE todos 
                SET title = $2, description = $3, completed = $4, priority = $5, 
                    project_id = $6, due_date = $7, updated_date = $8, 
                    embedding = $9, metadata = $10
                WHERE id = $1
            """,
                todo.id, todo.title, todo.description, todo.completed, todo.priority,
                todo.project_id, todo.due_date, todo.updated_date,
                getattr(todo, 'embedding', None), json.dumps(getattr(todo, 'metadata', {}))
            )
    
    async def delete_todo(self, todo_id: str) -> None:
        """Delete todo"""
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM todos WHERE id = $1", todo_id)
    
    # Calendar operations
    async def add_calendar_event(self, event: CalendarEvent) -> None:
        """Add calendar event"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO calendar_events (id, title, description, start_time, end_time, location, attendees, created_date, updated_date, embedding, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
                event.id, event.title, event.description, event.start_time, event.end_time,
                event.location, event.attendees, event.created_date, event.updated_date,
                getattr(event, 'embedding', None), json.dumps(getattr(event, 'metadata', {}))
            )
    
    async def get_calendar_events(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[CalendarEvent]:
        """Get calendar events within date range"""
        base_query = "SELECT * FROM calendar_events"
        params = []
        param_count = 0
        
        conditions = []
        if start_date:
            param_count += 1
            conditions.append(f"start_time >= ${param_count}")
            params.append(start_date)
        
        if end_date:
            param_count += 1
            conditions.append(f"end_time <= ${param_count}")
            params.append(end_date)
        
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)
        
        base_query += " ORDER BY start_time"
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(base_query, *params)
            return [self._row_to_calendar_event(row) for row in rows]
    
    # Status operations
    async def set_status(self, status: StatusEntry) -> None:
        """Set status entry"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO status_entries (id, status, message, emoji, expiry_date, created_date, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO UPDATE SET
                    status = EXCLUDED.status,
                    message = EXCLUDED.message,
                    emoji = EXCLUDED.emoji,
                    expiry_date = EXCLUDED.expiry_date,
                    metadata = EXCLUDED.metadata
            """,
                status.id, status.status, status.message, status.emoji,
                status.expiry_date, status.created_date, json.dumps(getattr(status, 'metadata', {}))
            )
    
    async def get_status(self) -> Optional[StatusEntry]:
        """Get current status"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM status_entries 
                WHERE expiry_date IS NULL OR expiry_date > NOW()
                ORDER BY created_date DESC 
                LIMIT 1
            """)
            return self._row_to_status_entry(row) if row else None
    
    # Personal data operations
    async def set_personal_data(self, data: PersonalData) -> None:
        """Set personal data"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO personal_data (key, value, data_type, created_date, updated_date, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value,
                    data_type = EXCLUDED.data_type,
                    updated_date = EXCLUDED.updated_date,
                    metadata = EXCLUDED.metadata
            """,
                data.key, json.dumps(data.value), data.data_type,
                data.created_date, data.updated_date, json.dumps(getattr(data, 'metadata', {}))
            )
    
    async def get_personal_data(self, key: str) -> Optional[PersonalData]:
        """Get personal data by key"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM personal_data WHERE key = $1", key)
            return self._row_to_personal_data(row) if row else None
    
    async def get_all_personal_data(self) -> List[PersonalData]:
        """Get all personal data"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM personal_data ORDER BY updated_date DESC")
            return [self._row_to_personal_data(row) for row in rows]
    
    # Helper methods to convert database rows to model objects
    def _row_to_project(self, row) -> Project:
        """Convert database row to Project model"""
        return Project(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            status=row['status'],
            priority=row['priority'],
            tags=row['tags'] or [],
            created_date=row['created_date'],
            updated_date=row['updated_date']
        )
    
    def _row_to_todo(self, row) -> Todo:
        """Convert database row to Todo model"""
        return Todo(
            id=row['id'],
            title=row['title'],
            description=row['description'],
            completed=row['completed'],
            priority=row['priority'],
            project_id=row['project_id'],
            due_date=row['due_date'],
            created_date=row['created_date'],
            updated_date=row['updated_date']
        )
    
    def _row_to_calendar_event(self, row) -> CalendarEvent:
        """Convert database row to CalendarEvent model"""
        return CalendarEvent(
            id=row['id'],
            title=row['title'],
            description=row['description'],
            start_time=row['start_time'],
            end_time=row['end_time'],
            location=row['location'],
            attendees=row['attendees'] or [],
            created_date=row['created_date'],
            updated_date=row['updated_date']
        )
    
    def _row_to_status_entry(self, row) -> StatusEntry:
        """Convert database row to StatusEntry model"""
        return StatusEntry(
            id=row['id'],
            status=row['status'],
            message=row['message'],
            emoji=row['emoji'],
            expiry_date=row['expiry_date'],
            created_date=row['created_date']
        )
    
    def _row_to_personal_data(self, row) -> PersonalData:
        """Convert database row to PersonalData model"""
        return PersonalData(
            key=row['key'],
            value=json.loads(row['value']) if isinstance(row['value'], str) else row['value'],
            data_type=row['data_type'],
            created_date=row['created_date'],
            updated_date=row['updated_date']
        )