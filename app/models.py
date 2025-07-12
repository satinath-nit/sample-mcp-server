from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the message sender (user, assistant, system)")
    content: str = Field(..., description="Content of the message")

class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="List of chat messages")
    max_tokens: Optional[int] = Field(default=1000, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(default=0.7, description="Temperature for response generation")
    stream: Optional[bool] = Field(default=False, description="Whether to stream the response")

class ChatResponse(BaseModel):
    id: str = Field(..., description="Unique identifier for the chat completion")
    object: str = Field(default="chat.completion", description="Object type")
    created: int = Field(..., description="Unix timestamp of creation")
    model: str = Field(..., description="Model used for completion")
    choices: List[Dict[str, Any]] = Field(..., description="List of completion choices")
    usage: Dict[str, int] = Field(..., description="Token usage information")

class GitHubIngestRequest(BaseModel):
    repository_url: str = Field(..., description="GitHub repository URL to ingest")
    branch: Optional[str] = Field(default="main", description="Branch to ingest from")
    file_patterns: Optional[List[str]] = Field(default=["*.md", "*.py", "*.js", "*.ts", "*.txt"], description="File patterns to include")
    max_file_size: Optional[int] = Field(default=1000000, description="Maximum file size in bytes")

class GitHubIngestResponse(BaseModel):
    status: str = Field(..., description="Status of the ingestion")
    message: str = Field(..., description="Status message")
    files_processed: int = Field(..., description="Number of files processed")
    documents_created: int = Field(..., description="Number of documents created in MongoDB")

class Document(BaseModel):
    id: Optional[str] = Field(default=None, description="Document ID")
    content: str = Field(..., description="Document content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Update timestamp")

class DocumentSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    limit: Optional[int] = Field(default=10, description="Maximum number of results")
    filter: Optional[Dict[str, Any]] = Field(default=None, description="Additional filters")

class DocumentSearchResponse(BaseModel):
    documents: List[Document] = Field(..., description="List of matching documents")
    total_count: int = Field(..., description="Total number of matching documents")
