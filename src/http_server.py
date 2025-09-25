"""
FastAPI HTTP MCP Server for Personal Assistant

This implements a cloud-native HTTP MCP server with:
- Multi-tenancy support
- OAuth authentication
- Intelligent data retrieval with vector search
- PostgreSQL + pgvector integration
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Sequence
from datetime import datetime, timedelta
import uuid

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn
from contextlib import asynccontextmanager

from mcp.server.models import InitializeRequest
from mcp.server.session import ServerSession
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
)

from .http_config import Config, get_config
from .database_interface import DatabaseInterface
from .database_factory import DatabaseFactory
from .models import Project, Todo, CalendarEvent, StatusEntry, PersonalData
from .document_manager import DocumentManager
from .auth_service import AuthService, UserContext, create_auth_service, AuthenticationError, AuthorizationError
from .embedding_service import get_embedding_service, generate_content_embedding
from .intelligent_retrieval import IntelligentRetrievalService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

class MCPRequest(BaseModel):
    method: str
    params: Optional[Dict[str, Any]] = None

class MCPResponse(BaseModel):
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

class PersonalAssistantHTTPServer:
    """HTTP MCP Server for Personal Assistant with multi-tenancy and vector search"""
    
    def __init__(self, config: Config):
        self.config = config
        self.db_interfaces: Dict[str, DatabaseInterface] = {}
        self.document_managers: Dict[str, DocumentManager] = {}
        self.intelligent_retrievers: Dict[str, IntelligentRetrievalService] = {}
        self.auth_service = create_auth_service(config.auth)
        self.embedding_service = get_embedding_service(
            provider=config.vector_search.provider,
            model=config.vector_search.model
        )
        
        # Create FastAPI app with lifespan
        self.app = FastAPI(
            title="MCP Personal Assistant Server",
            description="HTTP MCP Server with multi-tenancy and vector search",
            version="2.0.0",
            lifespan=self.lifespan
        )
        
        self._setup_middleware()
        self._setup_routes()
    
    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """Manage application lifecycle"""
        logger.info("Starting HTTP MCP Server...")
        yield
        logger.info("Shutting down HTTP MCP Server...")
        
        # Clean up database connections
        for db_interface in self.db_interfaces.values():
            await db_interface.close()
    
    def _setup_middleware(self):
        """Setup FastAPI middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure based on your needs
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        @self.app.middleware("http")
        async def authenticate_request(request: Request, call_next):
            """Authentication middleware"""
            # Skip auth for health checks and docs
            if request.url.path in ["/health", "/docs", "/openapi.json", "/metrics"]:
                return await call_next(request)
            
            # Skip auth if disabled
            if not self.config.auth.enabled:
                # Create a mock user context for development
                request.state.user = UserContext(
                    user_id="dev_user",
                    email="dev@example.com",
                    tenant_id="development"
                )
                return await call_next(request)
            
            # Extract and validate token
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing or invalid authorization header"
                )
            
            token = auth_header[7:]  # Remove "Bearer " prefix
            
            try:
                user_context = await self.auth_service.authenticate(token)
                request.state.user = user_context
                return await call_next(request)
                
            except AuthenticationError as e:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=str(e)
                )
            except Exception as e:
                logger.error(f"Authentication error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Authentication service error"
                )
    
    
    async def _get_user_database(self, tenant_id: str) -> DatabaseInterface:
        """Get or create database interface for tenant with proper isolation"""
        if tenant_id not in self.db_interfaces:
            # Create tenant-specific database configuration
            tenant_config = self._create_tenant_config(tenant_id)
            
            self.db_interfaces[tenant_id] = await DatabaseFactory.create_database(tenant_config)
            
            # Initialize document manager for tenant
            self.document_managers[tenant_id] = DocumentManager(
                self.db_interfaces[tenant_id],
                f"documents_{tenant_id}"
            )
            
            # Initialize intelligent retrieval service for tenant
            self.intelligent_retrievers[tenant_id] = IntelligentRetrievalService(
                self.db_interfaces[tenant_id],
                self.embedding_service
            )
            
            logger.info(f"Initialized database for tenant: {tenant_id}")
        
        return self.db_interfaces[tenant_id]
    
    async def _get_intelligent_retriever(self, tenant_id: str) -> IntelligentRetrievalService:
        """Get intelligent retrieval service for tenant"""
        # Ensure database is initialized (which also initializes the retriever)
        await self._get_user_database(tenant_id)
        return self.intelligent_retrievers[tenant_id]
    
    def _create_tenant_config(self, tenant_id: str) -> Config:
        """Create tenant-specific configuration with proper isolation"""
        if self.config.database_type == "postgresql":
            # Use schema-based isolation for PostgreSQL
            connection_string = self.config.pgvector_connection_string
            
            # Append schema to connection string if not already present
            if "?options=" not in connection_string:
                connection_string += f"?options=-c search_path=tenant_{tenant_id},public"
            else:
                connection_string += f",-c search_path=tenant_{tenant_id},public"
            
            tenant_config = Config(
                database_type="postgresql",
                pgvector_connection_string=connection_string
            )
            
            # Copy other configuration
            tenant_config.vector_search = self.config.vector_search
            tenant_config.features = self.config.features
            
        else:
            # File-based isolation for SQLite/TinyDB
            base_path = self.config.database_path
            if "." in base_path:
                name, ext = base_path.rsplit(".", 1)
                tenant_path = f"{name}_{tenant_id}.{ext}"
            else:
                tenant_path = f"{base_path}_{tenant_id}"
            
            tenant_config = Config(
                database_type=self.config.database_type,
                database_path=tenant_path
            )
            
            # Copy other configuration
            tenant_config.vector_search = self.config.vector_search
            tenant_config.features = self.config.features
        
        return tenant_config
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {"status": "healthy", "timestamp": datetime.utcnow()}
        
        @self.app.post("/mcp/initialize")
        async def initialize_mcp(request: Request):
            """Initialize MCP session"""
            user: UserContext = request.state.user
            
            return {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {}
                },
                "serverInfo": {
                    "name": "personal-assistant-http",
                    "version": "2.0.0"
                }
            }
        
        @self.app.post("/mcp/tools/list")
        async def list_tools(request: Request):
            """List available MCP tools"""
            return {
                "tools": [
                    {
                        "name": "get_dashboard",
                        "description": "Get intelligent dashboard with context-aware filtering",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Search query for context filtering"}
                            }
                        }
                    },
                    {
                        "name": "add_project",
                        "description": "Add a new project with vector embeddings",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                                "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                                "tags": {"type": "array", "items": {"type": "string"}}
                            },
                            "required": ["name", "description"]
                        }
                    },
                    {
                        "name": "semantic_search",
                        "description": "Perform semantic search across projects, todos, and documents",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "limit": {"type": "integer", "default": 5},
                                "types": {"type": "array", "items": {"type": "string"}}
                            },
                            "required": ["query"]
                        }
                    }
                ]
            }
        
        @self.app.post("/mcp/tools/call")
        async def call_tool(request: Request, body: MCPRequest):
            """Call MCP tool"""
            user: UserContext = request.state.user
            db = await self._get_user_database(user.tenant_id)
            
            tool_name = body.params.get("name") if body.params else None
            arguments = body.params.get("arguments", {}) if body.params else {}
            
            try:
                if tool_name == "get_dashboard":
                    result = await self._get_intelligent_dashboard(db, user, arguments)
                elif tool_name == "add_project":
                    result = await self._add_project_with_embeddings(db, user, arguments)
                elif tool_name == "semantic_search":
                    result = await self._semantic_search(db, user, arguments)
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unknown tool: {tool_name}"
                    )
                
                return {"content": [{"type": "text", "text": json.dumps(result, default=str)}]}
                
            except Exception as e:
                logger.error(f"Error calling tool {tool_name}: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def _get_intelligent_dashboard(self, db: DatabaseInterface, user: UserContext, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get intelligent dashboard with RAG-based context-aware filtering"""
        query = args.get("query", "")
        
        # Get intelligent retrieval service for user's tenant
        retriever = await self._get_intelligent_retriever(user.tenant_id)
        
        if query:
            # Use intelligent retrieval for context-aware results
            search_results = await retriever.search(
                user_id=user.user_id,
                tenant_id=user.tenant_id,
                query=query,
                content_types=["projects", "todos", "events"],
                max_results=15,
                intent="status_update"  # Dashboard context
            )
            
            # Organize results by type
            relevant_projects = [r for r in search_results["results"] if r["content_type"] == "project"]
            relevant_todos = [r for r in search_results["results"] if r["content_type"] == "todo"]
            relevant_events = [r for r in search_results["results"] if r["content_type"] == "event"]
            
            return {
                "type": "intelligent_dashboard",
                "query": query,
                "context_analysis": search_results["context"],
                "relevant_projects": relevant_projects[:5],
                "priority_todos": relevant_todos[:5],
                "upcoming_events": relevant_events[:3],
                "insights": self._generate_dashboard_insights(search_results["results"]),
                "suggestions": await self._generate_contextual_suggestions(user, query, search_results["results"]),
                "retrieval_metadata": search_results["retrieval_metadata"]
            }
        else:
            # Smart default dashboard - show contextually relevant items without explicit query
            now = datetime.now()
            
            # Get current work context using intelligent retrieval
            work_context_results = await retriever.search(
                user_id=user.user_id,
                tenant_id=user.tenant_id,
                query="current work status progress today",
                content_types=["projects", "todos", "events"],
                max_results=20,
                time_scope="today",
                intent="status_update"
            )
            
            # Get basic counts for overview
            all_projects = await db.get_projects()
            all_todos = await db.get_todos()
            upcoming_events = await db.get_calendar_events(
                start_date=now,
                end_date=now + timedelta(days=7)
            )
            
            # Separate results by type from context-aware search
            contextual_projects = [r for r in work_context_results["results"] if r["content_type"] == "project"]
            contextual_todos = [r for r in work_context_results["results"] if r["content_type"] == "todo"]
            contextual_events = [r for r in work_context_results["results"] if r["content_type"] == "event"]
            
            return {
                "type": "smart_dashboard",
                "overview": {
                    "total_projects": len(all_projects),
                    "active_projects": len([p for p in all_projects if p.status == "active"]),
                    "total_todos": len(all_todos),
                    "pending_todos": len([t for t in all_todos if not t.completed]),
                    "completed_today": len([t for t in all_todos if t.completed and 
                                          t.updated_date and t.updated_date.date() == now.date()]),
                    "upcoming_events": len(upcoming_events)
                },
                "current_focus": {
                    "active_projects": contextual_projects[:3],
                    "priority_todos": contextual_todos[:5],
                    "today_events": contextual_events[:3]
                },
                "insights": self._generate_dashboard_insights(work_context_results["results"]),
                "suggestions": await self._generate_contextual_suggestions(user, "", work_context_results["results"]),
                "context_metadata": work_context_results["retrieval_metadata"]
            }
    
    def _generate_dashboard_insights(self, results: List[Dict[str, Any]]) -> List[str]:
        """Generate insights from dashboard results using simple heuristics"""
        insights = []
        
        # Count by content type
        project_count = len([r for r in results if r["content_type"] == "project"])
        todo_count = len([r for r in results if r["content_type"] == "todo"])
        event_count = len([r for r in results if r["content_type"] == "event"])
        
        # High priority items
        high_priority = len([r for r in results if r.get("metadata", {}).get("priority") == "high"])
        
        if project_count > todo_count * 2:
            insights.append("You have many active projects - consider focusing on specific tasks")
        
        if high_priority > 3:
            insights.append(f"You have {high_priority} high-priority items requiring attention")
        
        if event_count > 5:
            insights.append("Your schedule is quite busy - consider time blocking for deep work")
        
        # Completion insights
        completed_todos = len([r for r in results if r.get("metadata", {}).get("completed") is True])
        if completed_todos > 0:
            insights.append(f"Great progress! You've completed {completed_todos} tasks recently")
        
        if not insights:
            insights.append("Your workspace is well-organized - keep up the good work!")
        
        return insights
    
    async def _generate_contextual_suggestions(self, user: UserContext, query: str, results: List[Dict[str, Any]]) -> List[str]:
        """Generate contextual suggestions based on current state"""
        suggestions = []
        
        # Analyze overdue items
        overdue_todos = [r for r in results if 
                        r["content_type"] == "todo" and 
                        r.get("metadata", {}).get("due_date") and 
                        not r.get("metadata", {}).get("completed")]
        
        if overdue_todos:
            suggestions.append(f"You have {len(overdue_todos)} overdue tasks - consider reviewing priorities")
        
        # Suggest focus areas
        high_relevance = [r for r in results if r.get("relevance_score", 0) > 0.8]
        if len(high_relevance) > 1:
            suggestions.append("Consider focusing on your most relevant items first")
        
        # Project-task balance
        project_results = [r for r in results if r["content_type"] == "project"]
        todo_results = [r for r in results if r["content_type"] == "todo"]
        
        if len(project_results) > len(todo_results):
            suggestions.append("Consider breaking down your projects into specific actionable tasks")
        
        # Time-based suggestions
        if query and ("today" in query.lower() or "now" in query.lower()):
            suggestions.append("Focus on quick wins to build momentum for the day")
        
        if not suggestions:
            suggestions.append("Everything looks well-organized - great job staying on top of things!")
        
        return suggestions
    
    async def _add_project_with_embeddings(self, db: DatabaseInterface, user: UserContext, args: Dict[str, Any]) -> Dict[str, Any]:
        """Add project with vector embeddings for semantic search"""
        project_data = {
            "id": str(uuid.uuid4()),
            "name": args["name"],
            "description": args["description"],
            "priority": args.get("priority", "medium"),
            "status": "active",
            "tags": args.get("tags", []),
            "created_date": datetime.now(),
            "updated_date": datetime.now()
        }
        
        project = Project(**project_data)
        
        # Generate embeddings for semantic search if vector search is enabled
        if self.config.vector_search.enabled:
            content_text = f"{project.name} {project.description}"
            metadata = {
                "priority": project.priority,
                "status": project.status,
                "tags": project.tags
            }
            
            embedding = await generate_content_embedding(
                content_text, 
                content_type="project",
                metadata=metadata
            )
            
            # Store embedding with project (depending on database implementation)
            if hasattr(project, '__dict__'):
                project.__dict__['embedding'] = embedding
            
            logger.info(f"Generated embedding for project {project.id}")
        
        await db.add_project(project)
        
        return {
            "message": "Project added successfully with semantic indexing",
            "project": project_data,
            "vector_search_enabled": self.config.vector_search.enabled
        }
    
    async def _semantic_search(self, db: DatabaseInterface, user: UserContext, args: Dict[str, Any]) -> Dict[str, Any]:
        """Perform intelligent semantic search across all data types"""
        query = args["query"]
        limit = args.get("limit", 10)
        search_types = args.get("types", ["projects", "todos", "documents", "events"])
        
        # Get intelligent retrieval service for user's tenant
        retriever = await self._get_intelligent_retriever(user.tenant_id)
        
        # Perform intelligent search with context awareness
        intelligent_results = await retriever.search(
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            query=query,
            content_types=search_types,
            max_results=limit,
            similarity_threshold=args.get("similarity_threshold", 0.7),
            intent=args.get("intent"),
            time_scope=args.get("time_scope"),
            priority_filter=args.get("priority_filter")
        )
        
        return intelligent_results
    
    async def _semantic_search_projects(self, db: DatabaseInterface, query: str, limit: int = 5) -> List[Dict]:
        """Semantic search for projects"""
        if not self.config.vector_search.enabled:
            # Fallback to text search if vector search is disabled
            all_projects = await db.get_projects()
            matching_projects = [
                p for p in all_projects 
                if query.lower() in p.name.lower() or query.lower() in p.description.lower()
            ]
            
            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "priority": p.priority,
                    "relevance_score": 0.85  # Mock score for text search
                }
                for p in matching_projects[:limit]
            ]
        
        try:
            # Generate embedding for search query
            query_embedding = await self.embedding_service.generate_embedding(query)
            
            # Perform vector search if database supports it
            if hasattr(db, 'semantic_search_projects'):
                results = await db.semantic_search_projects(
                    query_embedding, 
                    limit=limit,
                    similarity_threshold=self.config.vector_search.similarity_threshold
                )
                
                return [
                    {
                        "id": project.id,
                        "name": project.name,
                        "description": project.description,
                        "priority": project.priority,
                        "relevance_score": similarity
                    }
                    for project, similarity in results
                ]
            else:
                # Fallback if database doesn't support vector search
                return await self._semantic_search_projects_fallback(db, query, limit)
                
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            # Fallback to text search
            return await self._semantic_search_projects_fallback(db, query, limit)
    
    async def _semantic_search_projects_fallback(self, db: DatabaseInterface, query: str, limit: int) -> List[Dict]:
        """Fallback text search for projects"""
        all_projects = await db.get_projects()
        matching_projects = [
            p for p in all_projects 
            if query.lower() in p.name.lower() or query.lower() in p.description.lower()
        ]
        
        return [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "priority": p.priority,
                "relevance_score": 0.75  # Lower score for text-based fallback
            }
            for p in matching_projects[:limit]
        ]
    
    async def _semantic_search_todos(self, db: DatabaseInterface, query: str, limit: int = 5) -> List[Dict]:
        """Semantic search for todos"""
        # TODO: Implement actual vector search
        all_todos = await db.get_todos()
        
        matching_todos = [
            t for t in all_todos 
            if query.lower() in t.title.lower() or (t.description and query.lower() in t.description.lower())
        ]
        
        return [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "priority": t.priority,
                "completed": t.completed,
                "relevance_score": 0.80  # Mock score
            }
            for t in matching_todos[:limit]
        ]
    
    async def _semantic_search_documents(self, db: DatabaseInterface, query: str, limit: int = 5) -> List[Dict]:
        """Semantic search for documents"""
        # TODO: Implement document search with vector embeddings
        return []
    
    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Run the HTTP server"""
        uvicorn.run(self.app, host=host, port=port)

async def main():
    """Main entry point for HTTP server"""
    config = Config()
    server = PersonalAssistantHTTPServer(config)
    
    logger.info(f"Starting HTTP MCP Server on port 8000")
    server.run()

if __name__ == "__main__":
    asyncio.run(main())