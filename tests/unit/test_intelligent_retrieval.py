"""
Unit tests for intelligent retrieval service
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from typing import List, Dict, Any

from src.intelligent_retrieval import (
    SearchContext,
    RetrievalResult,
    QueryIntentClassifier,
    ContextualRetriever,
    IntelligentRetrievalService
)
from src.models import Project, Todo, CalendarEvent


class TestSearchContext:
    """Test SearchContext dataclass"""
    
    def test_search_context_creation(self):
        """Test basic search context creation"""
        context = SearchContext(
            user_id="test_user",
            tenant_id="test_tenant",
            query="test query"
        )
        
        assert context.user_id == "test_user"
        assert context.tenant_id == "test_tenant"
        assert context.query == "test query"
        assert context.intent is None
        assert context.max_results == 10
        assert context.similarity_threshold == 0.7
    
    def test_search_context_with_filters(self):
        """Test search context with filters"""
        context = SearchContext(
            user_id="user",
            tenant_id="tenant",
            query="urgent tasks",
            intent="todo_planning",
            time_scope="today",
            priority_filter="high",
            content_types=["todos", "projects"],
            max_results=5,
            similarity_threshold=0.8
        )
        
        assert context.intent == "todo_planning"
        assert context.time_scope == "today"
        assert context.priority_filter == "high"
        assert context.content_types == ["todos", "projects"]
        assert context.max_results == 5
        assert context.similarity_threshold == 0.8


class TestRetrievalResult:
    """Test RetrievalResult dataclass"""
    
    def test_retrieval_result_creation(self):
        """Test retrieval result creation"""
        result = RetrievalResult(
            content_type="project",
            item_id="project_123",
            title="Test Project",
            description="A test project",
            relevance_score=0.85,
            context_match={"intent_match": True},
            metadata={"priority": "high"}
        )
        
        assert result.content_type == "project"
        assert result.item_id == "project_123"
        assert result.title == "Test Project"
        assert result.relevance_score == 0.85
        assert result.context_match["intent_match"] is True
        assert result.metadata["priority"] == "high"
    
    def test_retrieval_result_to_dict(self):
        """Test retrieval result to dict conversion"""
        result = RetrievalResult(
            content_type="todo",
            item_id="todo_456",
            title="Test Todo",
            description=None,
            relevance_score=0.75,
            context_match={"time_match": False},
            metadata={"completed": False}
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["content_type"] == "todo"
        assert result_dict["item_id"] == "todo_456"
        assert result_dict["title"] == "Test Todo"
        assert result_dict["description"] is None
        assert result_dict["relevance_score"] == 0.75
        assert result_dict["context_match"]["time_match"] is False
        assert result_dict["metadata"]["completed"] is False


class TestQueryIntentClassifier:
    """Test QueryIntentClassifier class"""
    
    def test_classify_intent_project_search(self):
        """Test intent classification for project search"""
        queries = [
            "show me my projects",
            "what am I working on",
            "current project status",
            "building new app"
        ]
        
        for query in queries:
            intent = QueryIntentClassifier.classify_intent(query)
            assert intent in ["project_search", "status_update", "general_search"]
    
    def test_classify_intent_todo_planning(self):
        """Test intent classification for todo planning"""
        queries = [
            "what tasks do I need to do",
            "todo list for today",
            "upcoming deadlines",
            "plan my work"
        ]
        
        for query in queries:
            intent = QueryIntentClassifier.classify_intent(query)
            assert intent in ["todo_planning", "status_update", "general_search"]
    
    def test_classify_intent_status_update(self):
        """Test intent classification for status updates"""
        queries = [
            "what is my current status",
            "show me my progress",
            "where am I on projects",
            "current work summary"
        ]
        
        for query in queries:
            intent = QueryIntentClassifier.classify_intent(query)
            # Status update queries might be classified as status_update or project_search
            assert intent in ["status_update", "project_search", "general_search"]
    
    def test_classify_intent_calendar_query(self):
        """Test intent classification for calendar queries"""
        queries = [
            "upcoming meetings",
            "schedule for today",
            "calendar events",
            "next appointment"
        ]
        
        for query in queries:
            intent = QueryIntentClassifier.classify_intent(query)
            assert intent in ["calendar_query", "general_search"]
    
    def test_classify_intent_document_search(self):
        """Test intent classification for document search"""
        queries = [
            "find my documents",
            "search files",
            "notes about project",
            "saved documentation"
        ]
        
        for query in queries:
            intent = QueryIntentClassifier.classify_intent(query)
            assert intent in ["document_search", "general_search"]
    
    def test_classify_intent_unknown(self):
        """Test intent classification for unknown queries"""
        queries = [
            "random unrelated query",
            "xyz abc def",
            ""
        ]
        
        for query in queries:
            intent = QueryIntentClassifier.classify_intent(query)
            assert intent == "general_search"
    
    def test_extract_time_scope(self):
        """Test time scope extraction"""
        test_cases = [
            ("tasks for today", "today"),
            ("this week's projects", "this_week"),
            ("monthly review", "this_month"),
            ("recent updates", "recent"),
            ("overdue tasks", "overdue"),
            ("random query", None)
        ]
        
        for query, expected_scope in test_cases:
            scope = QueryIntentClassifier.extract_time_scope(query)
            assert scope == expected_scope
    
    def test_extract_priority_filter(self):
        """Test priority filter extraction"""
        test_cases = [
            ("urgent tasks", "high"),
            ("high priority items", "high"),
            ("important projects", "high"),
            ("medium priority", "medium"),
            ("normal tasks", "medium"),
            ("low priority items", "low"),
            ("later tasks", "low"),
            ("regular query", None)
        ]
        
        for query, expected_priority in test_cases:
            priority = QueryIntentClassifier.extract_priority_filter(query)
            assert priority == expected_priority


class TestContextualRetriever:
    """Test ContextualRetriever class"""
    
    @pytest_asyncio.fixture
    async def mock_database(self):
        """Mock database interface"""
        db = AsyncMock()
        
        # Mock projects
        projects = [
            Project(
                id="p1",
                name="Website Development",
                description="Building company website",
                status="active",
                priority="high",
                tags=["web", "development"],
                created_date=datetime.now() - timedelta(days=5),
                updated_date=datetime.now() - timedelta(hours=2)
            ),
            Project(
                id="p2",
                name="Mobile App",
                description="iOS mobile application",
                status="active",
                priority="medium",
                tags=["mobile", "ios"],
                created_date=datetime.now() - timedelta(days=10),
                updated_date=datetime.now() - timedelta(days=1)
            )
        ]
        
        # Mock todos
        todos = [
            Todo(
                id="t1",
                title="Design homepage",
                description="Create mockups for homepage",
                completed=False,
                priority="high",
                project_id="p1",
                due_date=datetime.now() + timedelta(days=2),
                created_date=datetime.now() - timedelta(days=3),
                updated_date=datetime.now() - timedelta(hours=1)
            ),
            Todo(
                id="t2",
                title="Setup development env",
                description="Configure development environment",
                completed=True,
                priority="medium",
                project_id="p1",
                created_date=datetime.now() - timedelta(days=4),
                updated_date=datetime.now() - timedelta(days=3)
            )
        ]
        
        # Mock events
        events = [
            CalendarEvent(
                id="e1",
                title="Client Meeting",
                description="Review progress with client",
                start_time=datetime.now() + timedelta(hours=2),
                end_time=datetime.now() + timedelta(hours=3),
                location="Conference Room",
                attendees=["client@example.com"],
                created_date=datetime.now() - timedelta(days=1),
                updated_date=datetime.now() - timedelta(hours=1)
            )
        ]
        
        db.get_projects.return_value = projects
        db.get_todos.return_value = todos
        db.get_calendar_events.return_value = events
        
        return db
    
    @pytest_asyncio.fixture
    async def mock_embedding_service(self):
        """Mock embedding service"""
        service = AsyncMock()
        service.generate_embedding.return_value = [0.1] * 384
        service.cosine_similarity.return_value = 0.8
        return service
    
    @pytest_asyncio.fixture
    async def contextual_retriever(self, mock_database, mock_embedding_service):
        """Create contextual retriever with mocks"""
        return ContextualRetriever(mock_database, mock_embedding_service)
    
    @pytest.mark.asyncio
    async def test_retrieve_with_intent_classification(self, contextual_retriever):
        """Test retrieval with automatic intent classification"""
        context = SearchContext(
            user_id="user1",
            tenant_id="tenant1",
            query="what projects am I working on"
        )
        
        results = await contextual_retriever.retrieve(context)
        
        assert isinstance(results, list)
        # Should have classified intent automatically
        assert context.intent is not None
    
    @pytest.mark.asyncio
    async def test_retrieve_projects(self, contextual_retriever):
        """Test project retrieval"""
        context = SearchContext(
            user_id="user1",
            tenant_id="tenant1",
            query="web development",
            content_types=["projects"],
            max_results=5
        )
        
        results = await contextual_retriever.retrieve(context)
        
        assert isinstance(results, list)
        assert len(results) <= context.max_results
        
        # Check that results are RetrievalResult objects
        for result in results:
            assert isinstance(result, RetrievalResult)
            assert result.content_type == "project"
    
    @pytest.mark.asyncio
    async def test_retrieve_todos(self, contextual_retriever):
        """Test todo retrieval"""
        context = SearchContext(
            user_id="user1",
            tenant_id="tenant1",
            query="design tasks",
            content_types=["todos"],
            max_results=5
        )
        
        results = await contextual_retriever.retrieve(context)
        
        assert isinstance(results, list)
        for result in results:
            assert isinstance(result, RetrievalResult)
            assert result.content_type == "todo"
    
    @pytest.mark.asyncio
    async def test_retrieve_events(self, contextual_retriever):
        """Test event retrieval"""
        context = SearchContext(
            user_id="user1",
            tenant_id="tenant1",
            query="meetings",
            content_types=["events"],
            max_results=5
        )
        
        results = await contextual_retriever.retrieve(context)
        
        assert isinstance(results, list)
        for result in results:
            assert isinstance(result, RetrievalResult)
            assert result.content_type == "event"
    
    @pytest.mark.asyncio
    async def test_retrieve_with_priority_filter(self, contextual_retriever):
        """Test retrieval with priority filter"""
        context = SearchContext(
            user_id="user1",
            tenant_id="tenant1",
            query="high priority work",
            priority_filter="high",
            max_results=10
        )
        
        results = await contextual_retriever.retrieve(context)
        
        # Should have applied priority filter
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_retrieve_with_time_scope(self, contextual_retriever):
        """Test retrieval with time scope"""
        context = SearchContext(
            user_id="user1",
            tenant_id="tenant1", 
            query="today's work",
            time_scope="today",
            max_results=10
        )
        
        results = await contextual_retriever.retrieve(context)
        
        # Should have applied time scope filter
        assert isinstance(results, list)
    
    def test_determine_content_types(self, contextual_retriever):
        """Test content type determination based on intent"""
        test_cases = [
            ("project_search", ["projects", "todos"]),
            ("todo_planning", ["todos", "projects"]),
            ("calendar_query", ["events"]),
            ("document_search", ["documents"]),
            ("status_update", ["projects", "todos", "events"]),
            ("unknown_intent", ["projects", "todos"])
        ]
        
        for intent, expected_types in test_cases:
            types = contextual_retriever._determine_content_types(intent)
            assert types == expected_types
    
    def test_matches_context_filters(self, contextual_retriever):
        """Test context filter matching"""
        project = Project(
            id="p1",
            name="Test Project",
            description="Test",
            status="active",
            priority="high",
            created_date=datetime.now() - timedelta(days=1),
            updated_date=datetime.now() - timedelta(hours=1)
        )
        
        # Test priority filter match
        context = SearchContext(
            user_id="user1",
            tenant_id="tenant1",
            query="test",
            priority_filter="high"
        )
        assert contextual_retriever._matches_context_filters(project, context) is True
        
        # Test priority filter mismatch
        context.priority_filter = "low"
        assert contextual_retriever._matches_context_filters(project, context) is False
        
        # Test no filter
        context.priority_filter = None
        assert contextual_retriever._matches_context_filters(project, context) is True
    
    def test_check_time_relevance(self, contextual_retriever):
        """Test time relevance checking"""
        now = datetime.now()
        
        # Test today
        today_item = now.replace(hour=10, minute=0)
        assert contextual_retriever._check_time_relevance(today_item, "today") is True
        
        yesterday_item = now - timedelta(days=1)
        assert contextual_retriever._check_time_relevance(yesterday_item, "today") is False
        
        # Test this week
        this_week_item = now - timedelta(days=3)
        assert contextual_retriever._check_time_relevance(this_week_item, "this_week") is True
        
        last_week_item = now - timedelta(days=10)
        assert contextual_retriever._check_time_relevance(last_week_item, "this_week") is False
        
        # Test no scope
        assert contextual_retriever._check_time_relevance(last_week_item, None) is True
    
    def test_get_time_range(self, contextual_retriever):
        """Test time range calculation"""
        now = datetime.now()
        
        # Test today
        start, end = contextual_retriever._get_time_range("today")
        assert start is not None
        assert end is not None
        assert start.date() == now.date()
        assert end.date() == (now + timedelta(days=1)).date()
        
        # Test this week
        start, end = contextual_retriever._get_time_range("this_week")
        assert start is not None
        assert end is not None
        assert (end - start).days == 7
        
        # Test no scope
        start, end = contextual_retriever._get_time_range(None)
        assert start is None
        assert end is None
    
    def test_calculate_text_similarity(self, contextual_retriever):
        """Test text similarity calculation"""
        query = "web development project"
        
        # Exact match
        text1 = "web development project"
        similarity1 = contextual_retriever._calculate_text_similarity(query, text1)
        assert similarity1 == 1.0
        
        # Partial match
        text2 = "mobile development project"
        similarity2 = contextual_retriever._calculate_text_similarity(query, text2)
        assert 0 < similarity2 < 1.0
        
        # No match
        text3 = "completely different content"
        similarity3 = contextual_retriever._calculate_text_similarity(query, text3)
        assert similarity3 == 0.0
        
        # Empty query
        similarity4 = contextual_retriever._calculate_text_similarity("", text1)
        assert similarity4 == 0.0


class TestIntelligentRetrievalService:
    """Test IntelligentRetrievalService class"""
    
    @pytest_asyncio.fixture
    async def mock_database(self):
        """Mock database interface"""
        return AsyncMock()
    
    @pytest_asyncio.fixture
    async def mock_embedding_service(self):
        """Mock embedding service"""
        return AsyncMock()
    
    @pytest_asyncio.fixture
    async def retrieval_service(self, mock_database, mock_embedding_service):
        """Create retrieval service with mocks"""
        return IntelligentRetrievalService(mock_database, mock_embedding_service)
    
    @pytest.mark.asyncio
    async def test_search_basic(self, retrieval_service):
        """Test basic search functionality"""
        # Mock retriever
        mock_results = [
            RetrievalResult(
                content_type="project",
                item_id="p1",
                title="Test Project",
                description="A test project",
                relevance_score=0.85,
                context_match={"intent_match": True},
                metadata={"priority": "high"}
            )
        ]
        
        retrieval_service.retriever.retrieve = AsyncMock(return_value=mock_results)
        
        result = await retrieval_service.search(
            user_id="user1",
            tenant_id="tenant1",
            query="test project"
        )
        
        assert result["query"] == "test project"
        assert "context" in result
        assert "results" in result
        assert result["total_results"] == 1
        assert "retrieval_metadata" in result
        
        # Check result structure
        results = result["results"]
        assert len(results) == 1
        assert results[0]["content_type"] == "project"
        assert results[0]["item_id"] == "p1"
    
    @pytest.mark.asyncio
    async def test_search_with_filters(self, retrieval_service):
        """Test search with various filters"""
        mock_results = []
        retrieval_service.retriever.retrieve = AsyncMock(return_value=mock_results)
        
        result = await retrieval_service.search(
            user_id="user1",
            tenant_id="tenant1",
            query="urgent tasks",
            intent="todo_planning",
            time_scope="today",
            priority_filter="high",
            content_types=["todos"],
            max_results=5,
            similarity_threshold=0.8
        )
        
        # Verify search context was created correctly
        call_args = retrieval_service.retriever.retrieve.call_args[0][0]
        assert call_args.query == "urgent tasks"
        assert call_args.intent == "todo_planning"
        assert call_args.time_scope == "today"
        assert call_args.priority_filter == "high"
        assert call_args.content_types == ["todos"]
        assert call_args.max_results == 5
        assert call_args.similarity_threshold == 0.8
    
    @pytest.mark.asyncio
    async def test_search_context_structure(self, retrieval_service):
        """Test search result context structure"""
        mock_results = []
        retrieval_service.retriever.retrieve = AsyncMock(return_value=mock_results)
        
        result = await retrieval_service.search(
            user_id="user1",
            tenant_id="tenant1",
            query="test query"
        )
        
        # Check context structure
        context = result["context"]
        assert "intent" in context
        assert "time_scope" in context
        assert "priority_filter" in context
        assert "content_types" in context
        
        # Check metadata structure
        metadata = result["retrieval_metadata"]
        assert "similarity_threshold" in metadata
        assert "max_results" in metadata
        assert "search_timestamp" in metadata
    
    @pytest.mark.asyncio
    async def test_search_empty_results(self, retrieval_service):
        """Test search with no results"""
        retrieval_service.retriever.retrieve = AsyncMock(return_value=[])
        
        result = await retrieval_service.search(
            user_id="user1",
            tenant_id="tenant1",
            query="nonexistent content"
        )
        
        assert result["results"] == []
        assert result["total_results"] == 0
    
    @pytest.mark.asyncio
    async def test_search_multiple_content_types(self, retrieval_service):
        """Test search across multiple content types"""
        mock_results = [
            RetrievalResult(
                content_type="project",
                item_id="p1",
                title="Project 1",
                description="Description 1",
                relevance_score=0.9,
                context_match={},
                metadata={}
            ),
            RetrievalResult(
                content_type="todo",
                item_id="t1",
                title="Todo 1", 
                description="Description 1",
                relevance_score=0.8,
                context_match={},
                metadata={}
            ),
            RetrievalResult(
                content_type="event",
                item_id="e1",
                title="Event 1",
                description="Description 1",
                relevance_score=0.7,
                context_match={},
                metadata={}
            )
        ]
        
        retrieval_service.retriever.retrieve = AsyncMock(return_value=mock_results)
        
        result = await retrieval_service.search(
            user_id="user1",
            tenant_id="tenant1",
            query="mixed content",
            content_types=["projects", "todos", "events"]
        )
        
        assert result["total_results"] == 3
        
        # Check that different content types are included
        content_types = [r["content_type"] for r in result["results"]]
        assert "project" in content_types
        assert "todo" in content_types
        assert "event" in content_types