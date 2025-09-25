-- Initialize PostgreSQL database for MCP Personal Assistant
-- This script sets up the database with pgvector extension

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create schemas for multi-tenancy (examples)
CREATE SCHEMA IF NOT EXISTS tenant_development;
CREATE SCHEMA IF NOT EXISTS tenant_default;

-- Set up permissions
GRANT USAGE ON SCHEMA tenant_development TO mcp_user;
GRANT USAGE ON SCHEMA tenant_default TO mcp_user;
GRANT CREATE ON SCHEMA tenant_development TO mcp_user;
GRANT CREATE ON SCHEMA tenant_default TO mcp_user;