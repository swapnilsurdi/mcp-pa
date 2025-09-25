from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class ProjectStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class DocumentType(str, Enum):
    PDF = "pdf"
    IMAGE = "image"
    TEXT = "text"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    OTHER = "other"

class Location(BaseModel):
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    details: Optional[str] = None

class LaptopDetails(BaseModel):
    os: Optional[str] = None
    model: Optional[str] = None
    specs: Optional[Dict[str, Any]] = None

class Permissions(BaseModel):
    file_system: bool = True
    browser: bool = False
    terminal: bool = True
    database: bool = True
    network: bool = False
    available_to_setup: List[str] = ["browser", "network"]

class UserStatus(BaseModel):
    name: str
    current_location: Optional[Location] = None
    laptop_details: Optional[LaptopDetails] = None
    permissions: Permissions = Field(default_factory=Permissions)
    last_updated: datetime = Field(default_factory=datetime.now)
    active_projects: List[str] = []
    notes: Optional[str] = None

class Task(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    priority: Priority = Priority.MEDIUM
    due_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    tags: List[str] = []

class Project(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: ProjectStatus = ProjectStatus.NOT_STARTED
    priority: Priority = Priority.MEDIUM
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    tasks: List[Task] = []
    tags: List[str] = []
    notes: Optional[str] = None
    progress: int = 0  # 0-100 percentage

class Todo(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    reminder_date: Optional[datetime] = None
    priority: Priority = Priority.MEDIUM
    completed: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    tags: List[str] = []

class CalendarEvent(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    attendees: List[str] = []
    reminder_minutes: int = 15
    created_at: datetime = Field(default_factory=datetime.now)
    tags: List[str] = []

class Document(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    file_path: str
    document_type: DocumentType
    mime_type: Optional[str] = None
    size_bytes: int
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    tags: List[str] = []
    metadata: Dict[str, Any] = {}
    external_url: Optional[str] = None  # For documents stored elsewhere (e.g., cloud storage)
    checksum: Optional[str] = None
