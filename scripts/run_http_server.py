#!/usr/bin/env python3
"""
Startup script for MCP Personal Assistant HTTP Server

Runs the enhanced cloud-native HTTP MCP server with intelligent
retrieval, multi-tenancy, and vector search capabilities.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from src.http_server import PersonalAssistantHTTPServer
from src.http_config import Config

def setup_logging():
    """Setup logging configuration"""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("mcp_http_server.log")
        ]
    )

async def main():
    """Main entry point"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting MCP Personal Assistant HTTP Server...")
    
    # Determine environment and create appropriate config
    environment = os.getenv("ENVIRONMENT", "development")
    
    if environment == "production":
        config = Config.for_production()
        logger.info("Running in PRODUCTION mode")
    else:
        config = Config.for_development()
        logger.info("Running in DEVELOPMENT mode")
    
    logger.info(f"Configuration: DB={config.database_type}, Auth={config.auth.enabled}, VectorSearch={config.vector_search.enabled}")
    
    # Create and run server
    try:
        server = PersonalAssistantHTTPServer(config)
        
        logger.info(f"Server starting on {config.server.host}:{config.server.port}")
        logger.info("Available endpoints:")
        logger.info("  GET  /health - Health check")
        logger.info("  POST /mcp/initialize - Initialize MCP session")  
        logger.info("  POST /mcp/tools/list - List available tools")
        logger.info("  POST /mcp/tools/call - Call MCP tools")
        logger.info("  GET  /docs - API documentation (development only)")
        
        server.run(host=config.server.host, port=config.server.port)
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"Server startup failed: {e}")
        sys.exit(1)