from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    mongodb_uri: str = "mongodb+srv://username:password@cluster.mongodb.net/"
    mongodb_database: str = "rag_db"
    mongodb_collection: str = "documents"
    
    openai_api_key: str = "your-api-key-here"
    openai_base_url: str = "https://llmendpoint/v1"
    openai_model: str = "model"
    
    mcp_server_name: str = "SampleMCPServer"
    mcp_server_version: str = "0.1.0"
    
    log_level: str = "INFO"
    
    github_token: str = "your-github-token-here"
    
    chat_api_host: str = "0.0.0.0"
    chat_api_port: int = 8000
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
