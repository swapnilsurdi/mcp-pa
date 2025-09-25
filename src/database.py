from tinydb import TinyDB, Query
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
from .models import (
    UserStatus, Project, Task, Todo, CalendarEvent,
    ProjectStatus, TaskStatus, Priority
)

class PersonalAssistantDB:
    def __init__(self, db_path: str = "data/pa_database.json"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = TinyDB(self.db_path)
        
        # Tables
        self.status_table = self.db.table('status')
        self.projects_table = self.db.table('projects')
        self.todos_table = self.db.table('todos')
        self.calendar_table = self.db.table('calendar')
        
        # Initialize default status if not exists
        if not self.status_table.all():
            default_status = UserStatus(name="User")
            self.status_table.insert(self._serialize_datetime(default_status.model_dump()))
    
    def _serialize_datetime(self, obj: Any) -> Any:
        """Custom JSON serializer for datetime objects"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: self._serialize_datetime(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_datetime(item) for item in obj]
        return obj
    
    def _deserialize_datetime(self, obj: Any) -> Any:
        """Custom JSON deserializer for datetime objects"""
        if isinstance(obj, str):
            try:
                return datetime.fromisoformat(obj)
            except ValueError:
                return obj
        elif isinstance(obj, dict):
            return {k: self._deserialize_datetime(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deserialize_datetime(item) for item in obj]
        return obj
    
    # Status operations
    def get_status(self) -> UserStatus:
        data = self.status_table.all()[0]
        data = self._deserialize_datetime(data)
        return UserStatus(**data)
    
    def update_status(self, status: UserStatus) -> UserStatus:
        data = self._serialize_datetime(status.model_dump())
        self.status_table.truncate()
        self.status_table.insert(data)
        return status
    
    # Project operations
    def create_project(self, project: Project) -> Project:
        data = self._serialize_datetime(project.model_dump())
        self.projects_table.insert(data)
        return project
    
    def get_project(self, project_id: str) -> Optional[Project]:
        result = self.projects_table.get(Query().id == project_id)
        if result:
            result = self._deserialize_datetime(result)
            return Project(**result)
        return None
    
    def list_projects(self, status: Optional[ProjectStatus] = None) -> List[Project]:
        if status:
            results = self.projects_table.search(Query().status == status.value)
        else:
            results = self.projects_table.all()
        
        return [Project(**self._deserialize_datetime(result)) for result in results]
    
    def update_project(self, project: Project) -> Project:
        data = self._serialize_datetime(project.model_dump())
        self.projects_table.update(data, Query().id == project.id)
        return project
    
    def delete_project(self, project_id: str) -> bool:
        return bool(self.projects_table.remove(Query().id == project_id))
    
    # Todo operations
    def create_todo(self, todo: Todo) -> Todo:
        data = self._serialize_datetime(todo.model_dump())
        self.todos_table.insert(data)
        return todo
    
    def get_todo(self, todo_id: str) -> Optional[Todo]:
        result = self.todos_table.get(Query().id == todo_id)
        if result:
            result = self._deserialize_datetime(result)
            return Todo(**result)
        return None
    
    def list_todos(self, completed: Optional[bool] = None) -> List[Todo]:
        if completed is not None:
            results = self.todos_table.search(Query().completed == completed)
        else:
            results = self.todos_table.all()
        
        return [Todo(**self._deserialize_datetime(result)) for result in results]
    
    def update_todo(self, todo: Todo) -> Todo:
        data = self._serialize_datetime(todo.model_dump())
        self.todos_table.update(data, Query().id == todo.id)
        return todo
    
    def delete_todo(self, todo_id: str) -> bool:
        return bool(self.todos_table.remove(Query().id == todo_id))
    
    # Calendar operations
    def create_event(self, event: CalendarEvent) -> CalendarEvent:
        data = self._serialize_datetime(event.model_dump())
        self.calendar_table.insert(data)
        return event
    
    def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        result = self.calendar_table.get(Query().id == event_id)
        if result:
            result = self._deserialize_datetime(result)
            return CalendarEvent(**result)
        return None
    
    def list_events(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[CalendarEvent]:
        results = self.calendar_table.all()
        events = [CalendarEvent(**self._deserialize_datetime(result)) for result in results]
        
        if start_date:
            events = [e for e in events if e.start_time >= start_date]
        if end_date:
            events = [e for e in events if e.end_time <= end_date]
        
        return sorted(events, key=lambda x: x.start_time)
    
    def update_event(self, event: CalendarEvent) -> CalendarEvent:
        data = self._serialize_datetime(event.model_dump())
        self.calendar_table.update(data, Query().id == event.id)
        return event
    
    def delete_event(self, event_id: str) -> bool:
        return bool(self.calendar_table.remove(Query().id == event_id))
