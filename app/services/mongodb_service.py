import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
from ..config import settings
from ..models import Document, DocumentSearchRequest, DocumentSearchResponse

logger = logging.getLogger(__name__)

class MongoDBService:
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self.collection: Optional[AsyncIOMotorCollection] = None
        self._connected = False

    async def connect(self):
        """Connect to MongoDB Atlas"""
        try:
            self.client = AsyncIOMotorClient(settings.mongodb_uri)
            if self.client is not None:
                self.database = self.client[settings.mongodb_database]
                if self.database is not None:
                    self.collection = self.database[settings.mongodb_collection]
            
            if self.client is not None:
                await self.client.admin.command('ping')
                self._connected = True
                logger.info(f"Successfully connected to MongoDB Atlas database: {settings.mongodb_database}")
                
                if self.collection is not None:
                    await self.collection.create_index([("content", "text"), ("metadata.title", "text")])
                    await self.collection.create_index("created_at")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB Atlas: {str(e)}")
            self._connected = False
            raise

    async def disconnect(self):
        """Disconnect from MongoDB Atlas"""
        if self.client:
            self.client.close()
            self._connected = False
            logger.info("Disconnected from MongoDB Atlas")

    async def is_connected(self) -> bool:
        """Check if connected to MongoDB"""
        if not self._connected or not self.client:
            return False
        try:
            await self.client.admin.command('ping')
            return True
        except Exception:
            self._connected = False
            return False

    async def insert_document(self, document: Document) -> str:
        """Insert a single document"""
        if not await self.is_connected():
            await self.connect()
        
        if self.collection is None:
            raise RuntimeError("MongoDB collection not initialized")
        
        doc_dict = document.dict()
        doc_dict['created_at'] = datetime.utcnow()
        doc_dict['updated_at'] = datetime.utcnow()
        
        result = await self.collection.insert_one(doc_dict)
        logger.info(f"Inserted document with ID: {result.inserted_id}")
        return str(result.inserted_id)

    async def insert_documents(self, documents: List[Document]) -> List[str]:
        """Insert multiple documents"""
        if not await self.is_connected():
            await self.connect()
        
        if self.collection is None:
            raise RuntimeError("MongoDB collection not initialized")
        
        if not documents:
            return []
        
        docs_dict = []
        for doc in documents:
            doc_dict = doc.dict()
            doc_dict['created_at'] = datetime.utcnow()
            doc_dict['updated_at'] = datetime.utcnow()
            docs_dict.append(doc_dict)
        
        result = await self.collection.insert_many(docs_dict)
        inserted_ids = [str(id) for id in result.inserted_ids]
        logger.info(f"Inserted {len(inserted_ids)} documents")
        return inserted_ids

    async def search_documents(self, query: str, limit: int = 10, filter_dict: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Search documents using enhanced text search with context-aware relevance scoring"""
        if not await self.is_connected():
            await self.connect()
        
        if self.collection is None:
            raise RuntimeError("MongoDB collection not initialized")
        
        documents = []
        query_lower = query.lower()
        
        conceptual_filter = {
            "$or": [
                {"metadata.title": {"$regex": f"^{query}$", "$options": "i"}},
                {"metadata.title": {"$regex": f"^what is {query}", "$options": "i"}},
                {"content": {"$regex": f"\\b{query}\\b(?!\\s+(search|api|tool|function))", "$options": "i"}},
            ]
        }
        if filter_dict:
            conceptual_filter.update(filter_dict)
        
        conceptual_cursor = self.collection.find(conceptual_filter).limit(limit // 3)
        conceptual_docs = []
        async for doc in conceptual_cursor:
            doc['id'] = str(doc.pop('_id'))
            score = 15
            if 'title' in doc.get('metadata', {}) and query_lower in doc['metadata']['title'].lower():
                score += 5
            doc['_search_score'] = score
            conceptual_docs.append(Document(**doc))
        
        documents.extend(conceptual_docs)
        remaining_limit = limit - len(conceptual_docs)
        
        if remaining_limit > 0:
            search_filter = {"$text": {"$search": query}}
            if filter_dict:
                search_filter.update(filter_dict)
            
            cursor = self.collection.find(
                search_filter,
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(remaining_limit)
            
            conceptual_ids = {doc.id for doc in conceptual_docs}
            async for doc in cursor:
                doc_id = str(doc.pop('_id'))
                if doc_id not in conceptual_ids:
                    doc['id'] = doc_id
                    base_score = doc.pop('score', 1)
                    
                    content_lower = doc.get('content', '').lower()
                    title_lower = doc.get('metadata', {}).get('title', '').lower()
                    
                    penalty = 0
                    technical_phrases = [f"{query_lower} search", f"{query_lower} api", f"{query_lower} tool", 
                                       f"{query_lower} function", f"search {query_lower}", f"using {query_lower}"]
                    for phrase in technical_phrases:
                        if phrase in content_lower or phrase in title_lower:
                            penalty += 0.3
                    
                    bonus = 0
                    conceptual_indicators = ["what is", "definition", "overview", "introduction", "about"]
                    for indicator in conceptual_indicators:
                        if indicator in content_lower or indicator in title_lower:
                            bonus += 0.2
                    
                    final_score = max(0.1, base_score - penalty + bonus)
                    doc['_search_score'] = final_score
                    documents.append(Document(**doc))
        
        if len(documents) < limit // 2 and remaining_limit > 0:
            keywords = [word for word in query_lower.split() if len(word) > 2]
            keyword_filter = {
                "$or": [
                    {"content": {"$regex": keyword, "$options": "i"}} 
                    for keyword in keywords
                ]
            }
            if filter_dict:
                keyword_filter.update(filter_dict)
            
            existing_ids = {doc.id for doc in documents}
            fallback_cursor = self.collection.find(keyword_filter).limit(remaining_limit)
            async for doc in fallback_cursor:
                doc_id = str(doc.pop('_id'))
                if doc_id not in existing_ids:
                    doc['id'] = doc_id
                    doc['_search_score'] = 0.3
                    documents.append(Document(**doc))
        
        documents.sort(key=lambda x: getattr(x, '_search_score', 0), reverse=True)
        
        logger.info(f"Found {len(documents)} documents for query: {query} using context-aware search")
        return documents[:limit]

    async def get_all_documents(self, limit: int = 100) -> List[Document]:
        """Get all documents with optional limit"""
        if not await self.is_connected():
            await self.connect()
        
        if self.collection is None:
            raise RuntimeError("MongoDB collection not initialized")
        
        cursor = self.collection.find().limit(limit).sort("created_at", -1)
        documents = []
        
        async for doc in cursor:
            doc['id'] = str(doc.pop('_id'))
            documents.append(Document(**doc))
        
        logger.info(f"Retrieved {len(documents)} documents")
        return documents

    async def delete_document(self, document_id: str) -> bool:
        """Delete a document by ID"""
        if not await self.is_connected():
            await self.connect()
        
        if self.collection is None:
            raise RuntimeError("MongoDB collection not initialized")
        
        from bson import ObjectId
        result = await self.collection.delete_one({"_id": ObjectId(document_id)})
        success = result.deleted_count > 0
        if success:
            logger.info(f"Deleted document with ID: {document_id}")
        else:
            logger.warning(f"Document not found for deletion: {document_id}")
        return success

    async def get_document_count(self) -> int:
        """Get total document count"""
        if not await self.is_connected():
            await self.connect()
        
        if self.collection is None:
            raise RuntimeError("MongoDB collection not initialized")
        
        count = await self.collection.count_documents({})
        return count

    async def search_documents_semantic(self, query: str, limit: int = 10, filter_dict: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Advanced semantic search with fuzzy matching and content analysis"""
        if not await self.is_connected():
            await self.connect()
        
        if self.collection is None:
            raise RuntimeError("MongoDB collection not initialized")
        
        pipeline = []
        
        match_stage = {
            "$match": {
                "$or": [
                    {"$text": {"$search": query}},
                    {"content": {"$regex": query, "$options": "i"}},
                    {"metadata.title": {"$regex": query, "$options": "i"}},
                    {"metadata.description": {"$regex": query, "$options": "i"}}
                ]
            }
        }
        
        if filter_dict:
            match_stage["$match"].update(filter_dict)
        
        pipeline.append(match_stage)
        
        pipeline.append({
            "$addFields": {
                "relevance_score": {
                    "$add": [
                        {"$cond": [{"$gt": [{"$meta": "textScore"}, 0]}, {"$meta": "textScore"}, 0]},
                        {"$cond": [{"$regexMatch": {"input": "$metadata.title", "regex": query, "options": "i"}}, 5, 0]},
                        {"$cond": [{"$regexMatch": {"input": "$metadata.title", "regex": f"^what is {query}", "options": "i"}}, 8, 0]},
                        {"$cond": [{"$lt": [{"$strLenCP": "$content"}, 1000]}, 2, 0]},
                        {"$cond": [{"$gt": ["$created_at", {"$dateSubtract": {"startDate": "$$NOW", "unit": "day", "amount": 30}}]}, 1, 0]},
                        {"$cond": [{"$regexMatch": {"input": "$content", "regex": f"{query} (search|api|tool|function)", "options": "i"}}, -2, 0]},
                        {"$cond": [{"$regexMatch": {"input": "$content", "regex": "(what is|definition|overview|introduction)", "options": "i"}}, 3, 0]}
                    ]
                }
            }
        })
        
        pipeline.append({"$sort": {"relevance_score": -1, "created_at": -1}})
        
        pipeline.append({"$limit": limit})
        
        documents = []
        async for doc in self.collection.aggregate(pipeline):
            doc['id'] = str(doc.pop('_id'))
            doc['_search_score'] = doc.pop('relevance_score', 1)
            documents.append(Document(**doc))
        
        logger.info(f"Found {len(documents)} documents for semantic search query: {query}")
        return documents

mongodb_service = MongoDBService()
