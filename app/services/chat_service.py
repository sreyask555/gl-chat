from typing import Dict, Any
from datetime import datetime
import json
import openai
import logging
from app.config.settings import settings
from app.services.handlers import DashboardHandler, SettingsHandler, ExtensionHandler

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        logger.info("Initializing ChatService")
        self.current_date = datetime.now()
        logger.debug(f"Setting OpenAI API key: {settings.OPENAI_API_KEY[:5]}...")
        openai.api_key = settings.OPENAI_API_KEY
        # Cache the OpenAI client
        self.openai_client = openai.OpenAI()
        
        # Initialize handlers
        self.dashboard_handler = DashboardHandler(self.openai_client)
        self.settings_handler = SettingsHandler(self.openai_client)
        self.extension_handler = ExtensionHandler(self.openai_client)

    async def process_unified_query(self, query: str, context_data: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Unified entry point for processing queries. Routes to the appropriate handler based on metadata.
        
        Args:
            query: The user's query
            context_data: The context data for the query
            metadata: Metadata that determines how to handle the query (contains page)
            
        Returns:
            Dict[str, Any]: The response from the appropriate handler
        """
        try:
            logger.info(f"Processing unified query: {query}")
            logger.debug(f"Metadata: {json.dumps(metadata, indent=2)}")
            
            # Route to the appropriate handler based on metadata page
            page = metadata.get("page", "dashboard")
            
            # Route based on page type
            if page == "settings":
                logger.info(f"Routing to settings handler")
                return self.settings_handler.process_query(query, context_data)
            elif page == "extension":
                logger.info(f"Routing to extension handler")
                return self.extension_handler.process_query(query, context_data)
            else:  # Default to dashboard
                logger.info(f"Routing to dashboard handler")
                return self.dashboard_handler.process_query(query, context_data)
                
        except Exception as e:
            logger.error(f"Error in process_unified_query: {str(e)}", exc_info=True)
            return {
                "response_message": "I encountered an error processing your request. Please try again."
            }