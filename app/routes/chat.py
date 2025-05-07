from fastapi import APIRouter, HTTPException, Depends
from app.services.chat_service import ChatService
from app.config.settings import settings
from typing import Dict, Any, Optional
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()
chat_service = ChatService()

@router.post("/unified")
async def unified_chat_processor(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Unified endpoint for processing all chat queries.
    This endpoint accepts a query, context data, and metadata, and routes the query
    to the appropriate handler based on the metadata.
    """
    try:
        logger.info("Received unified chat request")
        logger.debug(f"Request body: {request}")
        
        # Validate request structure
        if not isinstance(request, dict):
            logger.error("Request is not a dictionary")
            raise HTTPException(
                status_code=400,
                detail="Invalid request format. Request must be a JSON object."
            )
            
        if 'query' not in request:
            logger.error("Request missing 'query' field")
            raise HTTPException(
                status_code=400,
                detail="Invalid request format. Must include 'query' field."
            )
        
        # Extract fields from request
        query = request['query']
        context_data = request.get('contextData', {})
        metadata = request.get('metadata', {})
        
        # Validate query length
        query_length = len(query)
        logger.debug(f"Query length: {query_length}")
        if query_length > settings.MAX_QUERY_LENGTH:
            logger.error(f"Query exceeds maximum length: {query_length} > {settings.MAX_QUERY_LENGTH}")
            raise HTTPException(
                status_code=400,
                detail=f"Query exceeds maximum length of {settings.MAX_QUERY_LENGTH} characters"
            )

        # Process the query through the unified processor
        logger.info("Processing query through unified chat service")
        response = await chat_service.process_unified_query(query, context_data, metadata)
        logger.debug(f"Chat service response: {response}")
        return response

    except HTTPException as he:
        logger.error(f"HTTP Exception: {str(he)}")
        raise he
    except Exception as e:
        logger.error(f"Unexpected error processing unified chat request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat request: {str(e)}"
        )

@router.get("/status")
async def check_status() -> Dict[str, Any]:
    """
    Check the status of the chat service
    """
    try:
        return {
            "status": "ok",
            "message": "Chat service is running",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error checking status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error checking status: {str(e)}"
        ) 