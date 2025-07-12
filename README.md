# sample-mcp-server
MCP Server Example


AI assistant application that integrates FastMCP server, MongoDB Atlas knowledge base, and LLM endpoint with **direct MCP tool calling** capabilities.

## 🎯 Key Update: Direct MCP Integration Implemented

This version implements the **exact requested flow**:
```
User Query → LLM Service → MCP Tools → MongoDB Atlas → LLM Service → User Response
```

### Flow Implementation
1. **User sends chat message** → FastAPI `/chat` endpoint
2. **LLM generates JSON function call** → Compatible with Llama3-8B-Instruct
3. **LLM service calls MCP tools directly** → `await mcp._mcp_call_tool(function_name, parameters)`
4. **MCP tools query MongoDB Atlas** → Native FastMCP integration
5. **Documents returned through MCP** → Proper MCP protocol response
6. **LLM processes results** → Generates final response with context
7. **User receives response** → Complete chat completion with document context

## 🚀 Quick Start

# 1. Setup project
task setup

# 2. Configure environment (IMPORTANT!)
# Edit .env file with your actual credentials
nano .env  # or your preferred editor

# 3. Start the server
task dev


## Features

- **FastMCP Server**: Provides MCP tools for document search and retrieval
- **REST API**: Complete API with /chat and /ingest_github endpoints
- **MongoDB Atlas Integration**: Document storage and search capabilities
- **LLM Integration**:  LLM  endpoint
- **GitHub Integration**: Repository document ingestion
- **Swagger/ReDoc Documentation**: Auto-generated API documentation
- **Production-Grade**: Comprehensive error handling, logging, and async architecture

## API Endpoints

- `GET /healthz` - Health check endpoint
- `POST /chat` - Chat completion with MCP tool calling
- `POST /ingest_github` - Ingest GitHub repository documents
- `POST /search` - Search documents in knowledge base
- `GET /documents/count` - Get total document count
- `GET /mcp/info` - Get MCP server information
- `GET /docs` - Swagger UI documentation
- `GET /redoc` - ReDoc documentation

## MCP Tools

- `search_documents` - Search documents by text query
- `get_all_documents` - Get all documents with limit
- `get_document_count` - Get total document count
- `search_documents_by_metadata` - Search by metadata filters

## Prerequisites

- Python 3.12+
- Poetry (for dependency management)
- MongoDB Atlas account and cluster
- GitHub token (for repository ingestion)
- Access to LLM endpoint

## 📋 Prerequisites

- **Python 3.12+** (recommended to use pyenv)
- **Poetry** for dependency management
- **Task** (optional but recommended) for task automation
- **MongoDB Atlas** account and cluster
- **GitHub token** for repository ingestion
- **Access to LLM endpoint**


### Access the Application

Once running, you can access:
- **API Server**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/healthz


### Manual API Testing

#### 1. Health Check
```bash
# Using Task
task test-health

# Manual curl
curl -X GET "http://localhost:8000/healthz" -H "accept: application/json" | jq
```

#### 2. MCP Server Information
```bash
# Using Task
task test-mcp-info

# Manual curl
curl -X GET "http://localhost:8000/mcp/info" -H "accept: application/json" | jq
```

#### 3. Document Count
```bash
# Using Task
task test-document-count

# Manual curl
curl -X GET "http://localhost:8000/documents/count" -H "accept: application/json" | jq
```

#### 4. Document Search
```bash
# Using Task
task test-search

# Manual curl
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "query": "Python programming",
    "limit": 5
  }' | jq
```

#### 5. Chat Completion (requires valid LLM credentials)
```bash
# Using Task
task test-chat

# Manual curl
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello, can you search for documents about Python programming?"}
    ]
  }' | jq
```

#### 6. GitHub Repository Ingestion (requires valid GitHub token)
```bash
# Using Task
task test-github-ingest

# Manual curl
curl -X POST "http://localhost:8000/ingest_github" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "repository_url": "https://github.com/python/cpython",
    "branch": "main",
    "file_patterns": ["*.py", "*.md"],
    "max_file_size": 1048576
  }' | jq
```

### Testing with Swagger UI

1. Start the server: `task dev`
2. Open http://localhost:8000/docs in your browser
3. Use the interactive API documentation to test endpoints
4. Click "Try it out" on any endpoint to test with custom parameters


## Architecture

### Services
- **MongoDBService**: Async MongoDB Atlas operations
- **GitHubService**: Repository cloning and document ingestion
- **LLMService**:  LLM integration with tool calling
- **MCP Server**: FastMCP server with document tools

### Models
- **Document**: Core document model with metadata
- **ChatRequest/Response**: Chat API models
- **GitHubIngestRequest/Response**: GitHub ingestion models
- **DocumentSearchRequest/Response**: Search API models

### Configuration
- **Pydantic Settings**: Environment-based configuration
- **Async Architecture**: Full async/await support
- **Error Handling**: Comprehensive error management
- **Logging**: Structured logging throughout



## 📁 Project Structure

```
chatgtg-backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application & endpoints
│   ├── config.py            # Configuration management
│   ├── models.py            # Pydantic models
│   ├── mcp_server.py        # FastMCP server & tools
│   └── services/
│       ├── __init__.py
│       ├── mongodb_service.py    # MongoDB Atlas operations
│       ├── github_service.py     # GitHub integration
│       └── llm_service.py        # LLM integration
├── pyproject.toml           # Poetry dependencies
├── Taskfile.yml            # Task automation
├── .env.template           # Environment template
├── .env                    # Your actual environment (create from template)
└── README.md              # This documentation
```

## 🛠️ Development

### Available Tasks

```bash
# View all available tasks
task --list

# Development tasks
task setup          # Setup project (install deps, create .env)
task dev           # Start development server
task run           # Start production server


### Adding New Features

1. **New API Endpoints**: Add to `app/main.py`
2. **New Services**: Create in `app/services/`
3. **New Models**: Add to `app/models.py`
4. **New MCP Tools**: Add to `app/mcp_server.py`
5. **New Tasks**: Add to `Taskfile.yml`


