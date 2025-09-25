"""
Intelligent Data Retrieval Service

Implements smart data retrieval with context awareness, semantic search,
and RAG (Retrieval-Augmented Generation) capabilities for the Personal Assistant.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

from .database_interface import DatabaseInterface
from .embedding_service import EmbeddingService, get_embedding_service
from .models import Project, Todo, CalendarEvent, StatusEntry, PersonalData

logger = logging.getLogger(__name__)

@dataclass
class SearchContext:
    """Context information for intelligent retrieval"""
    user_id: str
    tenant_id: str
    query: str
    intent: Optional[str] = None  # "project_search", "todo_planning", "status_update", etc.
    time_scope: Optional[str] = None  # "today", "this_week", "this_month"
    priority_filter: Optional[str] = None  # "high", "medium", "low"
    content_types: List[str] = None  # ["projects", "todos", "documents", "events"]
    max_results: int = 10
    similarity_threshold: float = 0.7

@dataclass
class RetrievalResult:
    """Result from intelligent retrieval"""
    content_type: str
    item_id: str
    title: str
    description: Optional[str]
    relevance_score: float
    context_match: Dict[str, Any]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content_type": self.content_type,
            "item_id": self.item_id,
            "title": self.title,
            "description": self.description,
            "relevance_score": self.relevance_score,
            "context_match": self.context_match,
            "metadata": self.metadata
        }

class QueryIntentClassifier:
    """Classifies user queries to determine intent and context"""
    
    INTENT_KEYWORDS = {
        "project_search": ["project", "working on", "building", "developing", "task list"],
        "todo_planning": ["todo", "tasks", "need to do", "plan", "schedule", "deadline"],
        "status_update": ["status", "current", "what am i", "progress", "working", "doing"],
        "calendar_query": ["meeting", "event", "calendar", "schedule", "appointment"],
        "document_search": ["document", "file", "notes", "wrote", "saved", "remember"],
        "review": ["review", "summary", "overview", "report", "recap"]
    }
    
    TIME_KEYWORDS = {
        "today": ["today", "now", "current", "this moment"],
        "this_week": ["this week", "week", "weekly", "7 days"],
        "this_month": ["this month", "month", "monthly", "30 days"],
        "recent": ["recent", "recently", "latest", "new"],
        "overdue": ["overdue", "late", "past due", "missed"]
    }
    
    PRIORITY_KEYWORDS = {
        "high": ["urgent", "important", "high priority", "critical", "asap"],
        "medium": ["medium", "normal", "standard"],
        "low": ["low priority", "later", "when time permits", "eventually"]
    }
    
    @staticmethod
    def classify_intent(query: str) -> str:
        """Classify the intent of a query"""
        query_lower = query.lower()
        
        intent_scores = {}
        for intent, keywords in QueryIntentClassifier.INTENT_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            if score > 0:
                intent_scores[intent] = score
        
        if intent_scores:
            return max(intent_scores.items(), key=lambda x: x[1])[0]
        
        return "general_search"
    
    @staticmethod
    def extract_time_scope(query: str) -> Optional[str]:
        """Extract time scope from query"""
        query_lower = query.lower()
        
        for scope, keywords in QueryIntentClassifier.TIME_KEYWORDS.items():
            if any(keyword in query_lower for keyword in keywords):
                return scope
        
        return None
    
    @staticmethod
    def extract_priority_filter(query: str) -> Optional[str]:
        """Extract priority filter from query"""
        query_lower = query.lower()
        
        for priority, keywords in QueryIntentClassifier.PRIORITY_KEYWORDS.items():
            if any(keyword in query_lower for keyword in keywords):
                return priority
        
        return None

class ContextualRetriever:
    """Performs contextual retrieval based on user intent and history"""
    
    def __init__(self, db: DatabaseInterface, embedding_service: EmbeddingService):
        self.db = db
        self.embedding_service = embedding_service
        self.intent_classifier = QueryIntentClassifier()
    
    async def retrieve(self, context: SearchContext) -> List[RetrievalResult]:
        """Perform intelligent retrieval based on context"""
        
        # Enhance context with intent classification if not provided
        if not context.intent:
            context.intent = self.intent_classifier.classify_intent(context.query)
        
        if not context.time_scope:
            context.time_scope = self.intent_classifier.extract_time_scope(context.query)
        
        if not context.priority_filter:
            context.priority_filter = self.intent_classifier.extract_priority_filter(context.query)
        
        logger.info(f"Intelligent retrieval - Intent: {context.intent}, Time: {context.time_scope}, Priority: {context.priority_filter}")
        
        # Determine content types to search based on intent
        if not context.content_types:
            context.content_types = self._determine_content_types(context.intent)
        
        # Perform retrieval based on intent
        results = []
        
        if "projects" in context.content_types:
            project_results = await self._retrieve_projects(context)
            results.extend(project_results)
        
        if "todos" in context.content_types:
            todo_results = await self._retrieve_todos(context)
            results.extend(todo_results)
        
        if "events" in context.content_types:
            event_results = await self._retrieve_events(context)
            results.extend(event_results)
        
        if "documents" in context.content_types:
            doc_results = await self._retrieve_documents(context)
            results.extend(doc_results)
        
        # Sort by relevance score and apply limit
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:context.max_results]
    
    def _determine_content_types(self, intent: str) -> List[str]:
        """Determine which content types to search based on intent"""
        intent_mapping = {
            "project_search": ["projects", "todos"],
            "todo_planning": ["todos", "projects"],
            "status_update": ["projects", "todos", "events"],
            "calendar_query": ["events"],
            "document_search": ["documents"],
            "review": ["projects", "todos", "events", "documents"],
            "general_search": ["projects", "todos", "events", "documents"]
        }
        
        return intent_mapping.get(intent, ["projects", "todos"])
    
    async def _retrieve_projects(self, context: SearchContext) -> List[RetrievalResult]:
        """Retrieve projects with contextual filtering"""
        results = []
        
        try:
            # Get query embedding
            query_embedding = await self.embedding_service.generate_embedding(context.query)
            
            # Perform vector search if available
            if hasattr(self.db, 'semantic_search_projects'):
                search_results = await self.db.semantic_search_projects(
                    query_embedding,
                    limit=context.max_results,
                    similarity_threshold=context.similarity_threshold
                )
                
                for project, similarity in search_results:
                    # Apply contextual filtering
                    if self._matches_context_filters(project, context):
                        result = RetrievalResult(
                            content_type="project",
                            item_id=project.id,
                            title=project.name,
                            description=project.description,
                            relevance_score=similarity,
                            context_match={
                                "intent_match": context.intent == "project_search",
                                "priority_match": not context.priority_filter or project.priority == context.priority_filter,
                                "time_match": self._check_time_relevance(project.updated_date, context.time_scope)
                            },
                            metadata={
                                "priority": project.priority,
                                "status": project.status,
                                "tags": project.tags,
                                "created_date": project.created_date.isoformat(),
                                "updated_date": project.updated_date.isoformat()
                            }
                        )
                        results.append(result)
            else:
                # Fallback to basic search
                all_projects = await self.db.get_projects(limit=50)
                filtered_projects = [p for p in all_projects if self._matches_context_filters(p, context)]
                
                for project in filtered_projects:
                    # Simple text similarity
                    similarity = self._calculate_text_similarity(context.query, f"{project.name} {project.description}")
                    
                    if similarity > context.similarity_threshold:
                        result = RetrievalResult(
                            content_type="project",
                            item_id=project.id,
                            title=project.name,
                            description=project.description,
                            relevance_score=similarity,
                            context_match={"text_match": True},
                            metadata={"priority": project.priority, "status": project.status}
                        )
                        results.append(result)
        
        except Exception as e:
            logger.error(f"Error retrieving projects: {e}")
        
        return results
    
    async def _retrieve_todos(self, context: SearchContext) -> List[RetrievalResult]:
        """Retrieve todos with contextual filtering"""
        results = []
        
        try:
            # Apply time-based filtering for todos
            todos = await self.db.get_todos(limit=100)
            
            # Filter based on context
            filtered_todos = []
            for todo in todos:
                if self._matches_todo_context(todo, context):
                    filtered_todos.append(todo)
            
            # Generate embeddings and calculate similarity
            query_embedding = await self.embedding_service.generate_embedding(context.query)
            
            for todo in filtered_todos:
                # Calculate similarity
                todo_text = f"{todo.title} {todo.description or ''}"
                todo_embedding = await self.embedding_service.generate_embedding(todo_text)
                similarity = self.embedding_service.cosine_similarity(query_embedding, todo_embedding)
                
                if similarity > context.similarity_threshold:
                    result = RetrievalResult(
                        content_type="todo",
                        item_id=todo.id,
                        title=todo.title,
                        description=todo.description,
                        relevance_score=similarity,
                        context_match={
                            "priority_match": not context.priority_filter or todo.priority == context.priority_filter,
                            "completion_relevant": self._is_completion_relevant(todo, context),
                            "time_match": self._check_todo_time_relevance(todo, context.time_scope)
                        },
                        metadata={
                            "priority": todo.priority,
                            "completed": todo.completed,
                            "due_date": todo.due_date.isoformat() if todo.due_date else None,
                            "project_id": todo.project_id
                        }
                    )
                    results.append(result)
        
        except Exception as e:
            logger.error(f"Error retrieving todos: {e}")
        
        return results
    
    async def _retrieve_events(self, context: SearchContext) -> List[RetrievalResult]:
        """Retrieve calendar events with contextual filtering"""
        results = []
        
        try:
            # Determine time range based on context
            start_date, end_date = self._get_time_range(context.time_scope)
            
            events = await self.db.get_calendar_events(start_date, end_date)
            
            query_embedding = await self.embedding_service.generate_embedding(context.query)
            
            for event in events:
                event_text = f"{event.title} {event.description or ''}"
                event_embedding = await self.embedding_service.generate_embedding(event_text)
                similarity = self.embedding_service.cosine_similarity(query_embedding, event_embedding)
                
                if similarity > context.similarity_threshold:
                    result = RetrievalResult(
                        content_type="event",
                        item_id=event.id,
                        title=event.title,
                        description=event.description,
                        relevance_score=similarity,
                        context_match={
                            "time_relevant": True,
                            "upcoming": event.start_time > datetime.now()
                        },
                        metadata={
                            "start_time": event.start_time.isoformat(),
                            "end_time": event.end_time.isoformat(),
                            "location": event.location,
                            "attendees": event.attendees
                        }
                    )
                    results.append(result)
        
        except Exception as e:
            logger.error(f"Error retrieving events: {e}")
        
        return results
    
    async def _retrieve_documents(self, context: SearchContext) -> List[RetrievalResult]:
        """Retrieve documents with contextual filtering"""
        results = []
        
        try:
            # Use hybrid search if available (combining text and vector search)
            query_embedding = await self.embedding_service.generate_embedding(context.query)
            
            if hasattr(self.db, 'hybrid_search_documents'):
                search_results = await self.db.hybrid_search_documents(
                    context.query,
                    query_embedding,
                    limit=context.max_results
                )
                
                for doc_data in search_results:
                    result = RetrievalResult(
                        content_type="document",
                        item_id=doc_data["id"],
                        title=doc_data["title"],
                        description=doc_data.get("content", "")[:200] + "..." if len(doc_data.get("content", "")) > 200 else doc_data.get("content", ""),
                        relevance_score=doc_data.get("combined_score", 0.0),
                        context_match={
                            "text_score": doc_data.get("text_score", 0.0),
                            "semantic_score": doc_data.get("semantic_score", 0.0)
                        },
                        metadata={
                            "file_path": doc_data.get("file_path"),
                            "mime_type": doc_data.get("mime_type"),
                            "size_bytes": doc_data.get("size_bytes"),
                            "created_date": doc_data.get("created_date"),
                            "updated_date": doc_data.get("updated_date")
                        }
                    )
                    results.append(result)
        
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
        
        return results
    
    def _matches_context_filters(self, item: Union[Project, Todo], context: SearchContext) -> bool:
        """Check if item matches contextual filters"""
        # Priority filter
        if context.priority_filter and hasattr(item, 'priority') and item.priority != context.priority_filter:
            return False
        
        # Time scope filter
        if context.time_scope and hasattr(item, 'updated_date'):
            if not self._check_time_relevance(item.updated_date, context.time_scope):
                return False
        
        return True
    
    def _matches_todo_context(self, todo: Todo, context: SearchContext) -> bool:
        """Check if todo matches specific todo context"""
        # Don't show completed todos for planning contexts unless specifically asked
        if context.intent == "todo_planning" and todo.completed:
            if "completed" not in context.query.lower():
                return False
        
        # Show only incomplete todos for status updates
        if context.intent == "status_update" and todo.completed:
            return False
        
        return self._matches_context_filters(todo, context)
    
    def _check_time_relevance(self, item_date: datetime, time_scope: Optional[str]) -> bool:
        """Check if item date is relevant to time scope"""
        if not time_scope:
            return True
        
        now = datetime.now()
        
        if time_scope == "today":
            return item_date.date() == now.date()
        elif time_scope == "this_week":
            week_start = now - timedelta(days=now.weekday())
            return item_date >= week_start
        elif time_scope == "this_month":
            return item_date.year == now.year and item_date.month == now.month
        elif time_scope == "recent":
            return now - item_date <= timedelta(days=7)
        
        return True
    
    def _check_todo_time_relevance(self, todo: Todo, time_scope: Optional[str]) -> bool:
        """Check todo time relevance including due dates"""
        if not time_scope:
            return True
        
        now = datetime.now()
        
        if time_scope == "overdue" and todo.due_date:
            return todo.due_date < now and not todo.completed
        
        # Check due date relevance
        if todo.due_date:
            return self._check_time_relevance(todo.due_date, time_scope)
        
        # Fallback to created/updated date
        return self._check_time_relevance(todo.updated_date or todo.created_date, time_scope)
    
    def _is_completion_relevant(self, todo: Todo, context: SearchContext) -> bool:
        """Check if todo completion status is relevant to context"""
        if "completed" in context.query.lower():
            return todo.completed
        elif context.intent in ["todo_planning", "status_update"]:
            return not todo.completed
        return True
    
    def _get_time_range(self, time_scope: Optional[str]) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Get time range for date-based queries"""
        if not time_scope:
            return None, None
        
        now = datetime.now()
        
        if time_scope == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            return start, end
        elif time_scope == "this_week":
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7)
            return start, end
        elif time_scope == "this_month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if now.month == 12:
                end = start.replace(year=now.year + 1, month=1)
            else:
                end = start.replace(month=now.month + 1)
            return start, end
        
        return None, None
    
    def _calculate_text_similarity(self, query: str, text: str) -> float:
        """Simple text similarity calculation"""
        query_words = set(query.lower().split())
        text_words = set(text.lower().split())
        
        if not query_words:
            return 0.0
        
        intersection = query_words.intersection(text_words)
        return len(intersection) / len(query_words)

class IntelligentRetrievalService:
    """Main service for intelligent data retrieval"""
    
    def __init__(self, db: DatabaseInterface, embedding_service: Optional[EmbeddingService] = None):
        self.db = db
        self.embedding_service = embedding_service or get_embedding_service()
        self.retriever = ContextualRetriever(db, self.embedding_service)
    
    async def search(self, 
                    user_id: str,
                    tenant_id: str,
                    query: str,
                    **kwargs) -> Dict[str, Any]:
        """Perform intelligent search with context awareness"""
        
        context = SearchContext(
            user_id=user_id,
            tenant_id=tenant_id,
            query=query,
            intent=kwargs.get('intent'),
            time_scope=kwargs.get('time_scope'),
            priority_filter=kwargs.get('priority_filter'),
            content_types=kwargs.get('content_types'),
            max_results=kwargs.get('max_results', 10),
            similarity_threshold=kwargs.get('similarity_threshold', 0.7)
        )
        
        results = await self.retriever.retrieve(context)
        
        return {
            "query": query,
            "context": {
                "intent": context.intent,
                "time_scope": context.time_scope,
                "priority_filter": context.priority_filter,
                "content_types": context.content_types
            },
            "results": [result.to_dict() for result in results],
            "total_results": len(results),
            "retrieval_metadata": {
                "similarity_threshold": context.similarity_threshold,
                "max_results": context.max_results,
                "search_timestamp": datetime.now().isoformat()
            }
        }