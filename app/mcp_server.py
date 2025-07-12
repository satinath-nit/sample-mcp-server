import asyncio
import logging
from typing import Any, Dict, List, Optional
from fastmcp import FastMCP
from .services.mongodb_service import mongodb_service
from .config import settings

logger = logging.getLogger(__name__)

mcp = FastMCP(settings.mcp_server_name)

@mcp.tool()
async def search_documents(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for documents in the MongoDB Atlas knowledge base using enhanced relevance-based search.
    
    Args:
        query: The search query to find relevant documents
        limit: Maximum number of documents to return (default: 10)
    
    Returns:
        List of documents matching the search query, ranked by relevance
    """
    try:
        documents = await mongodb_service.search_documents(query, limit)
        return [
            {
                "id": doc.id,
                "content": doc.content[:500] + "..." if len(doc.content) > 500 else doc.content,  # Truncate long content
                "metadata": doc.metadata,
                "relevance_score": getattr(doc, '_search_score', 1),
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
            }
            for doc in documents
        ]
    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        return []

@mcp.tool()
async def get_all_documents(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get all documents from the MongoDB Atlas knowledge base.
    
    Args:
        limit: Maximum number of documents to return (default: 20)
    
    Returns:
        List of all documents in the knowledge base
    """
    try:
        documents = await mongodb_service.get_all_documents(limit)
        return [
            {
                "id": doc.id,
                "content": doc.content,
                "metadata": doc.metadata,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
            }
            for doc in documents
        ]
    except Exception as e:
        logger.error(f"Error getting all documents: {str(e)}")
        return []

@mcp.tool()
async def get_document_count() -> Dict[str, Any]:
    """
    Get the total count of documents in the MongoDB Atlas knowledge base.
    
    Returns:
        Dictionary containing the total document count
    """
    try:
        count = await mongodb_service.get_document_count()
        return {
            "total_documents": count,
            "database": settings.mongodb_database,
            "collection": settings.mongodb_collection
        }
    except Exception as e:
        logger.error(f"Error getting document count: {str(e)}")
        return {"total_documents": 0, "error": str(e)}

@mcp.tool()
async def search_documents_by_metadata(metadata_filter: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for documents by metadata filters in the MongoDB Atlas knowledge base.
    
    Args:
        metadata_filter: Dictionary of metadata filters to apply
        limit: Maximum number of documents to return (default: 10)
    
    Returns:
        List of documents matching the metadata filters
    """
    try:
        mongo_filter = {}
        for key, value in metadata_filter.items():
            mongo_filter[f"metadata.{key}"] = value
        
        documents = await mongodb_service.search_documents("", limit, mongo_filter)
        return [
            {
                "id": doc.id,
                "content": doc.content,
                "metadata": doc.metadata,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
            }
            for doc in documents
        ]
    except Exception as e:
        logger.error(f"Error searching documents by metadata: {str(e)}")
        return []

@mcp.tool()
async def search_documents_semantic(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Advanced semantic search for documents with enhanced relevance scoring and fuzzy matching.
    
    Args:
        query: The search query to find relevant documents
        limit: Maximum number of documents to return (default: 10)
    
    Returns:
        List of documents matching the search query with advanced relevance ranking
    """
    try:
        documents = await mongodb_service.search_documents_semantic(query, limit)
        return [
            {
                "id": doc.id,
                "content": doc.content[:500] + "..." if len(doc.content) > 500 else doc.content,
                "metadata": doc.metadata,
                "relevance_score": getattr(doc, '_search_score', 1),
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
            }
            for doc in documents
        ]
    except Exception as e:
        logger.error(f"Error in semantic search: {str(e)}")
        return []

@mcp.resource("server://info")
async def get_server_info() -> str:
    """Get information about the ChatGTG MCP server"""
    return f"""
ChatGTG MCP Server Information:
- Server Name: {settings.mcp_server_name}
- Version: {settings.mcp_server_version}
- Database: {settings.mongodb_database}
- Collection: {settings.mongodb_collection}
- Available Tools:
  - search_documents: Search documents by text query
  - get_all_documents: Get all documents with limit
  - get_document_count: Get total document count
  - search_documents_by_metadata: Search by metadata filters
"""

@mcp.resource("database://status")
async def get_database_status() -> str:
    """Get the current status of the MongoDB Atlas connection"""
    try:
        is_connected = await mongodb_service.is_connected()
        if is_connected:
            count = await mongodb_service.get_document_count()
            return f"""
Database Status: CONNECTED
- Database: {settings.mongodb_database}
- Collection: {settings.mongodb_collection}
- Total Documents: {count}
- Connection Status: Active
"""
        else:
            return """
Database Status: DISCONNECTED
- Connection Status: Not connected to MongoDB Atlas
"""
    except Exception as e:
        return f"""
Database Status: ERROR
- Error: {str(e)}
"""

async def start_mcp_server():
    """Start the MCP server"""
    try:
        if not await mongodb_service.is_connected():
            await mongodb_service.connect()
        
        logger.info(f"Starting MCP server: {settings.mcp_server_name} v{settings.mcp_server_version}")
        return mcp
    except Exception as e:
        logger.error(f"Failed to start MCP server: {str(e)}")
        raise

__all__ = ["mcp", "start_mcp_server", "search_documents", "get_all_documents", "get_document_count", "search_documents_by_metadata"]
