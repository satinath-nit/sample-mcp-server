import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .config import settings
from .models import (
    ChatRequest, ChatResponse, GitHubIngestRequest, GitHubIngestResponse,
    DocumentSearchRequest, DocumentSearchResponse
)
from .services.mongodb_service import mongodb_service
from .services.github_service import github_service
from .services.llm_service import llm_service
from .mcp_server import start_mcp_server, mcp

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ChatGTG application...")
    
    try:
        await mongodb_service.connect()
        logger.info("MongoDB Atlas connection established")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB Atlas: {str(e)}")
    
    try:
        await start_mcp_server()
        logger.info("MCP server initialized")
    except Exception as e:
        logger.error(f"Failed to initialize MCP server: {str(e)}")
    
    logger.info("ChatGTG application startup complete")
    
    yield
    
    logger.info("Shutting down ChatGTG application...")
    await mongodb_service.disconnect()
    logger.info("ChatGTG application shutdown complete")

app = FastAPI(
    title="ChatGTG API",
    description="ChatGTG - AI Assistant with MongoDB Atlas Knowledge Base and MCP Server",
    version=settings.mcp_server_version,
    lifespan=lifespan
)

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/healthz")
async def healthz():
    """Health check endpoint"""
    try:
        mongo_status = await mongodb_service.is_connected()
        
        return {
            "status": "ok",
            "service": "ChatGTG",
            "version": settings.mcp_server_version,
            "mongodb_connected": mongo_status,
            "mcp_server": settings.mcp_server_name
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "message": str(e)
            }
        )

@app.post("/chat", response_model=ChatResponse)
async def chat_completion(request: ChatRequest):
    """
    Chat completion endpoint that uses the  LLM with MCP tool calling support.
    The LLM can call MCP tools to search and retrieve documents from MongoDB Atlas.
    """
    try:
        logger.info(f"Processing chat request with {len(request.messages)} messages")
        response = await llm_service.chat_completion(request)
        logger.info("Chat completion successful")
        return response
    except Exception as e:
        logger.error(f"Chat completion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat completion failed: {str(e)}")

@app.post("/ingest_github", response_model=GitHubIngestResponse)
async def ingest_github_repository(request: GitHubIngestRequest, background_tasks: BackgroundTasks):
    """
    Ingest a GitHub repository into the MongoDB Atlas knowledge base.
    This endpoint clones the repository and processes files according to the specified patterns.
    """
    try:
        logger.info(f"Starting GitHub ingestion for repository: {request.repository_url}")
        
        response = await github_service.ingest_repository(request)
        
        logger.info(f"GitHub ingestion completed: {response.status}")
        return response
    except Exception as e:
        logger.error(f"GitHub ingestion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"GitHub ingestion failed: {str(e)}")

@app.post("/search", response_model=DocumentSearchResponse)
async def search_documents(request: DocumentSearchRequest):
    """
    Search documents in the MongoDB Atlas knowledge base.
    """
    try:
        logger.info(f"Searching documents with query: {request.query}")
        documents = await mongodb_service.search_documents(
            request.query, 
            request.limit or 10, 
            request.filter
        )
        
        response = DocumentSearchResponse(
            documents=documents,
            total_count=len(documents)
        )
        
        logger.info(f"Search completed, found {len(documents)} documents")
        return response
    except Exception as e:
        logger.error(f"Document search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Document search failed: {str(e)}")

@app.get("/documents/count")
async def get_document_count():
    """Get the total count of documents in the knowledge base"""
    try:
        count = await mongodb_service.get_document_count()
        return {
            "total_documents": count,
            "database": settings.mongodb_database,
            "collection": settings.mongodb_collection
        }
    except Exception as e:
        logger.error(f"Failed to get document count: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get document count: {str(e)}")

@app.get("/mcp/info")
async def get_mcp_info():
    """Get information about the MCP server"""
    return {
        "mcp_server_name": settings.mcp_server_name,
        "mcp_server_version": settings.mcp_server_version,
        "tools": [
            {
                "name": "search_documents",
                "description": "Search documents by text query"
            },
            {
                "name": "get_all_documents", 
                "description": "Get all documents with limit"
            },
            {
                "name": "get_document_count",
                "description": "Get total document count"
            },
            {
                "name": "search_documents_by_metadata",
                "description": "Search by metadata filters"
            }
        ],
        "resources": [
            {
                "uri": "server://info",
                "description": "Get server information"
            },
            {
                "uri": "database://status", 
                "description": "Get database status"
            }
        ]
    }

app.mount("/mcp", mcp)
