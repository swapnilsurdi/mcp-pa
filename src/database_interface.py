from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
from .models import (
    UserStatus, Project, Task, Todo, CalendarEvent, Document,
    ProjectStatus, TaskStatus, Priority
)

class DatabaseInterface(ABC):
    """Abstract interface for database operations"""
    
    @abstractmethod
    def initialize(self):
        """Initialize database schema/structure"""
        pass
    
    # Status operations
    @abstractmethod
    def get_status(self) -> UserStatus:
        """Get current user status"""
        pass
    
    @abstractmethod
    def update_status(self, status: UserStatus) -> UserStatus:
        """Update user status"""
        pass
    
    # Project operations
    @abstractmethod
    def create_project(self, project: Project) -> Project:
        """Create a new project"""
        pass
    
    @abstractmethod
    def get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID"""
        pass
    
    @abstractmethod
    def list_projects(self, status: Optional[ProjectStatus] = None) -> List[Project]:
        """List projects with optional status filter"""
        pass
    
    @abstractmethod
    def update_project(self, project: Project) -> Project:
        """Update existing project"""
        pass
    
    @abstractmethod
    def delete_project(self, project_id: str) -> bool:
        """Delete project by ID"""
        pass
    
    # Todo operations
    @abstractmethod
    def create_todo(self, todo: Todo) -> Todo:
        """Create a new todo"""
        pass
    
    @abstractmethod
    def get_todo(self, todo_id: str) -> Optional[Todo]:
        """Get todo by ID"""
        pass
    
    @abstractmethod
    def list_todos(self, completed: Optional[bool] = None) -> List[Todo]:
        """List todos with optional completion filter"""
        pass
    
    @abstractmethod
    def update_todo(self, todo: Todo) -> Todo:
        """Update existing todo"""
        pass
    
    @abstractmethod
    def delete_todo(self, todo_id: str) -> bool:
        """Delete todo by ID"""
        pass
    
    # Calendar operations
    @abstractmethod
    def create_event(self, event: CalendarEvent) -> CalendarEvent:
        """Create a new calendar event"""
        pass
    
    @abstractmethod
    def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        """Get calendar event by ID"""
        pass
    
    @abstractmethod
    def list_events(self, start_date: Optional[datetime] = None, 
                   end_date: Optional[datetime] = None) -> List[CalendarEvent]:
        """List calendar events with optional date range filter"""
        pass
    
    @abstractmethod
    def update_event(self, event: CalendarEvent) -> CalendarEvent:
        """Update existing calendar event"""
        pass
    
    @abstractmethod
    def delete_event(self, event_id: str) -> bool:
        """Delete calendar event by ID"""
        pass
    
    # Document operations
    @abstractmethod
    def create_document(self, document: Document) -> Document:
        """Create a new document record"""
        pass
    
    @abstractmethod
    def get_document(self, document_id: str) -> Optional[Document]:
        """Get document by ID"""
        pass
    
    @abstractmethod
    def list_documents(self, tags: Optional[List[str]] = None) -> List[Document]:
        """List documents with optional tag filter"""
        pass
    
    @abstractmethod
    def update_document(self, document: Document) -> Document:
        """Update existing document"""
        pass
    
    @abstractmethod
    def delete_document(self, document_id: str) -> bool:
        """Delete document by ID"""
        pass
    
    @abstractmethod
    def close(self):
        """Close database connection"""
        pass
