from beanie import Document
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from bson import ObjectId
from pymongo import IndexModel, ASCENDING, DESCENDING
import logging

# Configure logging
logger = logging.getLogger(__name__)

class ChatMessage(Document):
    """Schema representing a chat message in the database"""
    # Note: userId stored as string in model but converted to ObjectId for queries
    userId: str
    query: str
    response: str
    source: str = "webapp"
    page: str = "dashboard"
    createdAt: datetime = Field(default_factory=datetime.now)
    
    class Settings:
        name = "chatmessages"  # Collection name to match the existing MongoDB collection
        indexes = [
            IndexModel([("createdAt", ASCENDING)], expireAfterSeconds=172800),  # TTL index (2 days)
            IndexModel([("userId", ASCENDING), ("createdAt", DESCENDING)])  # Compound index
        ]
    
    @classmethod
    async def create_message(cls, user_id: str, query_text: str, response_text: str, metadata: dict = None) -> "ChatMessage":
        """Create a new chat message"""
        now = datetime.now()
        
        # Extract source and page from metadata if provided
        source = "webapp"
        page = "dashboard"
        if metadata:
            source = metadata.get('source', source)
            page = metadata.get('page', page)
        
        # Create the ChatMessage instance
        message = cls(
            userId=user_id,
            query=query_text,
            response=response_text,
            source=source,
            page=page,
            createdAt=now
        )
        
        # Store userId as ObjectId in the database
        collection = cls.get_motor_collection()
        doc_dict = message.dict()
        
        # Remove the id field as MongoDB will generate _id
        if 'id' in doc_dict:
            del doc_dict['id']
        
        if ObjectId.is_valid(user_id):
            doc_dict["userId"] = ObjectId(user_id)
            
        result = await collection.insert_one(doc_dict)
        message.id = result.inserted_id
        
        return message
    
    @classmethod
    async def get_user_conversations(cls, user_id: str, limit: int = 50, before: Optional[datetime] = None) -> List[dict]:
        """Get user conversation history"""
        if before is None:
            before = datetime.now()
        
        # Convert to ObjectId for querying
        user_oid = None
        if ObjectId.is_valid(user_id):
            user_oid = ObjectId(user_id)
        else:
            return []  # Return empty list for invalid ObjectId
        
        try:
            collection = cls.get_motor_collection()
            
            # Try using ObjectId first
            query_filter = {"userId": user_oid, "createdAt": {"$lt": before}}
            messages = await collection.find(query_filter).sort([("createdAt", -1)]).limit(limit).to_list(None)
            
            # If no results, try with string userId as fallback
            if len(messages) == 0:
                query_filter = {"userId": str(user_id), "createdAt": {"$lt": before}}
                messages = await collection.find(query_filter).sort([("createdAt", -1)]).limit(limit).to_list(None)
            
            # Return in chronological order
            return list(reversed(messages))
        except Exception as e:
            logger.error(f"Error in get_user_conversations: {str(e)}")
            return []
    
    @classmethod
    async def delete_user_conversations(cls, user_id: str) -> int:
        """Delete all conversations for a user"""
        if ObjectId.is_valid(user_id):
            user_oid = ObjectId(user_id)
            result = await cls.get_motor_collection().delete_many({"userId": user_oid})
            return result.deleted_count
        return 0
        
    @classmethod
    async def count_user_messages(cls, user_id: str) -> int:
        """Count messages for a user"""
        if ObjectId.is_valid(user_id):
            user_oid = ObjectId(user_id)
            return await cls.get_motor_collection().count_documents({"userId": user_oid})
        return 0 