# MCP Personal Assistant Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Claude Desktop                           │
│                                                              │
│  User ◄──► Claude Interface ◄──► MCP Client                 │
└──────────────────────┬───────────────────────────────────────┘
                       │ MCP Protocol
                       │ (JSON-RPC)
┌──────────────────────▼───────────────────────────────────────┐
│                MCP Personal Assistant Server                  │
│  ┌─────────────────────────────────────────────────────┐     │
│  │                  MCP Server Core                     │     │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐ │     │
│  │  │  Resources  │  │    Tools    │  │   Handlers   │ │     │
│  │  └─────────────┘  └─────────────┘  └──────────────┘ │     │
│  └─────────────────────────────────────────────────────┘     │
│                            │                                  │
│  ┌─────────────────────────▼─────────────────────────────┐   │
│  │                  Database Layer                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │   │
│  │  │   Status    │  │  Projects   │  │    Todos     │  │   │
│  │  │   Table     │  │   Table     │  │    Table     │  │   │
│  │  └─────────────┘  └─────────────┘  └──────────────┘  │   │
│  │                   ┌──────────────┐                    │   │
│  │                   │   Calendar   │                    │   │
│  │                   │    Table     │                    │   │
│  │                   └──────────────┘                    │   │
│  └──────────────────────────────────────────────────────┘   │
│                            │                                 │
│                            ▼                                 │
│                    ┌──────────────┐                         │
│                    │   TinyDB     │                         │
│                    │ JSON Storage │                         │
│                    └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. MCP Server Core
The main server implementation that handles:
- Resource listing and reading
- Tool registration and execution
- Client communication via MCP protocol

### 2. Resources
Virtual endpoints that provide access to data:
- `pa://status` - Current user status
- `pa://projects` - All projects
- `pa://todos` - All todos
- `pa://calendar` - Calendar events

### 3. Tools
Available actions that can be performed:
- Status management (get/update)
- Project management (create/read/update/delete)
- Todo management (create/read/update/delete)
- Calendar management (create/read/update/delete)
- Dashboard views

### 4. Database Layer
Abstraction layer for data persistence:
- Handles CRUD operations for all entities
- Manages data serialization/deserialization
- Provides type-safe interfaces via Pydantic models

### 5. Storage
TinyDB JSON-based storage:
- Lightweight, file-based database
- No external dependencies
- Human-readable data format
- Automatic persistence

## Data Flow

1. **Client Request** → MCP Protocol → Server Handler
2. **Server Handler** → Tool/Resource Handler
3. **Handler** → Database Layer
4. **Database Layer** → TinyDB Storage
5. **Response** ← Reverse path back to client

## Key Design Decisions

1. **TinyDB for Storage**: Chosen for simplicity and portability, no need for external database server
2. **Pydantic Models**: Provides type safety and validation for all data structures
3. **Resource/Tool Separation**: Clear distinction between data access (resources) and actions (tools)
4. **Modular Architecture**: Easy to extend with new features or integrate with external services
5. **Local-First Design**: All data stored locally, ready for future cloud integration
