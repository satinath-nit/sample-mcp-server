import logging
import os
import tempfile
import shutil
from typing import List, Dict, Any, Optional
import git
import asyncio
from pathlib import Path
from ..config import settings
from ..models import Document, GitHubIngestRequest, GitHubIngestResponse
from .mongodb_service import mongodb_service

logger = logging.getLogger(__name__)

class GitHubService:
    def __init__(self):
        self.github_token = settings.github_token

    def _get_auth_url(self, repo_url: str) -> str:
        """Convert GitHub URL to authenticated URL"""
        if self.github_token and self.github_token != "your-github-token-here":
            if repo_url.startswith("https://github.com/"):
                return repo_url.replace("https://github.com/", f"https://{self.github_token}@github.com/")
        return repo_url

    async def ingest_repository(self, request: GitHubIngestRequest) -> GitHubIngestResponse:
        """Ingest a GitHub repository into MongoDB"""
        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp()
            logger.info(f"Cloning repository {request.repository_url} to {temp_dir}")
            
            auth_url = self._get_auth_url(request.repository_url)
            repo = git.Repo.clone_from(auth_url, temp_dir, branch=request.branch)
            
            documents = []
            files_processed = 0
            
            repo_path = Path(temp_dir)
            for pattern in request.file_patterns:
                for file_path in repo_path.rglob(pattern):
                    if file_path.is_file():
                        try:
                            if file_path.stat().st_size > request.max_file_size:
                                logger.warning(f"Skipping large file: {file_path} ({file_path.stat().st_size} bytes)")
                                continue
                            
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                            
                            relative_path = file_path.relative_to(repo_path)
                            metadata = {
                                "source": "github",
                                "repository_url": request.repository_url,
                                "branch": request.branch,
                                "file_path": str(relative_path),
                                "file_name": file_path.name,
                                "file_extension": file_path.suffix,
                                "file_size": file_path.stat().st_size,
                                "title": f"{request.repository_url.split('/')[-1]}: {relative_path}"
                            }
                            
                            document = Document(
                                content=content,
                                metadata=metadata
                            )
                            documents.append(document)
                            files_processed += 1
                            
                        except Exception as e:
                            logger.error(f"Error processing file {file_path}: {str(e)}")
                            continue
            
            if documents:
                document_ids = await mongodb_service.insert_documents(documents)
                documents_created = len(document_ids)
            else:
                documents_created = 0
            
            logger.info(f"Successfully ingested {files_processed} files, created {documents_created} documents")
            
            return GitHubIngestResponse(
                status="success",
                message=f"Successfully ingested repository {request.repository_url}",
                files_processed=files_processed,
                documents_created=documents_created
            )
            
        except Exception as e:
            logger.error(f"Error ingesting repository {request.repository_url}: {str(e)}")
            return GitHubIngestResponse(
                status="error",
                message=f"Failed to ingest repository: {str(e)}",
                files_processed=0,
                documents_created=0
            )
        
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")

github_service = GitHubService()
