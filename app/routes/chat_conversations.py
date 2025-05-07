from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging
from app.models.chat_message import ChatMessage
from app.middleware.auth import verify_token
from bson import ObjectId

logger = logging.getLogger(__name__)
router = APIRouter()

# Request and response models
class ConversationRequest(BaseModel):
    query: str
    response: str
    metadata: Optional[dict] = None

class ConversationResponse(BaseModel):
    message: str
    data: Optional[List[dict]] = None
    count: Optional[int] = None

@router.get("/status", response_model=dict)
async def status(user_id: str = Depends(verify_token)):
    """Check if the chat history API is working correctly"""
    try:
        count = await ChatMessage.count_user_messages(user_id)
        return {
            "status": "ok",
            "message": "Chat history API is working correctly",
            "userId": user_id,
            "messageCount": count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error checking status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to check status")

@router.post("/conversations", response_model=ConversationResponse)
async def save_conversation(conversation: ConversationRequest, user_id: str = Depends(verify_token)):
    """Save a chat conversation"""
    try:
        chat_message = await ChatMessage.create_message(
            user_id=user_id,
            query_text=conversation.query,
            response_text=conversation.response,
            metadata=conversation.metadata
        )
        
        # Convert ObjectId to string for serialization
        user_id_str = str(chat_message.userId) if isinstance(chat_message.userId, ObjectId) else chat_message.userId
        
        # Only include the fields we want in the response - explicitly excluding 'id'
        formatted_conversation = {
            "_id": str(chat_message.id) if hasattr(chat_message, 'id') and chat_message.id else None,
            "userId": user_id_str,
            "query": chat_message.query,
            "response": chat_message.response,
            "source": chat_message.source,
            "page": chat_message.page,
            "createdAt": chat_message.createdAt
        }
        
        return {
            "message": "Chat conversation saved successfully",
            "data": [formatted_conversation]
        }
    except Exception as e:
        logger.error(f"Error saving chat conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save chat conversation")

@router.get("/conversations", response_model=ConversationResponse)
async def get_conversations(
    limit: Optional[int] = Query(50, ge=1, le=100),
    before: Optional[datetime] = None,
    user_id: str = Depends(verify_token)
):
    """Get chat conversation history for a user"""
    try:
        messages = await ChatMessage.get_user_conversations(
            user_id=user_id,
            limit=limit,
            before=before
        )
        
        # Format response
        formatted_conversations = []
        for conv in messages:
            # Convert ObjectId to string
            user_id_str = str(conv.get("userId", "")) if isinstance(conv.get("userId"), ObjectId) else conv.get("userId", "")
            
            # Explicitly only include the fields we want, ensuring 'id' is excluded
            # Rename MongoDB's "_id" field to "_id" in the response
            formatted_conv = {
                "_id": str(conv.get("_id")) if "_id" in conv else None,
                "userId": user_id_str,
                "query": conv.get("query", ""),
                "response": conv.get("response", ""),
                "source": conv.get("source", "webapp"),
                "page": conv.get("page", "dashboard"),
                "createdAt": conv.get("createdAt", datetime.now())
            }
            formatted_conversations.append(formatted_conv)
        
        return {
            "message": "Chat conversations retrieved successfully",
            "data": formatted_conversations
        }
    except Exception as e:
        logger.error(f"Error retrieving chat conversations: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve chat conversations")

@router.delete("/conversations", response_model=ConversationResponse)
async def delete_conversations(user_id: str = Depends(verify_token)):
    """Delete all chat conversations for a user"""
    try:
        deleted_count = await ChatMessage.delete_user_conversations(user_id=user_id)
        return {
            "message": "Chat history cleared successfully",
            "count": deleted_count
        }
    except Exception as e:
        logger.error(f"Error deleting chat conversations: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to clear chat history") 