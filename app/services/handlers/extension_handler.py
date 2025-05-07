import logging
from typing import Dict, Any
import json

logger = logging.getLogger(__name__)

class ExtensionHandler:
    """Handler for extension-related chat queries"""
    
    def __init__(self, openai_client):
        """Initialize with the OpenAI client"""
        self.openai_client = openai_client
        logger.info("Extension Handler initialized")
    
    def process_query(self, query: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process extension-specific queries using OpenAI LLM
        
        Args:
            query: The user's query text
            context_data: Any contextual data provided (may include lastConversation)
            
        Returns:
            Dict with response_message field and goto field for navigation
        """
        try:
            logger.info(f"Processing extension query: {query}")
            logger.info(f"Context data: {json.dumps(context_data, default=str)}")
            
            # Prepare messages with context if available
            messages = [
                {"role": "system", "content": """You are the Goodlife shopping assistant, designed to help users navigate the extension and webapp, find products, compare prices, and get shopping recommendations. Be helpful, friendly, and concise.

When appropriate, suggest navigating to specific pages based on the user's query. Your response must be actionable and help users navigate the interface.

Available navigation destinations:
- dashboard: The main dashboard of the webapp with overview of activities and recommendations
- settings: User settings and preferences for the Goodlife account
- savings: The savings stack page showing saved deals and price alerts
- history: Browsing history page showing recently viewed products
- lists: Lists view page showing user's saved shopping lists

Follow these specific navigation rules:
1. For queries about profile information, changing profile info, credit cards, or memberships, direct users to the settings page. Tell them this information can be managed there.
2. For queries about recent products or browsing history, ask if they want to view their extension browsing history, see other product info, or get a detailed view in the dashboard.
3. For queries about benefits, rewards, or savings for a specific product (when user is on a product page), direct them to the savings page.
4. When you need to ask a clarifying question back to the user, do not set any navigation destination (do not include a 'goto' field).

For navigation queries, you must determine whether the user needs to go to a specific page.

Please format your response as a JSON object with a 'response_message' field for the text response and an optional 'goto' field for navigation."""}
            ]
            
            # Add last conversation if available
            if context_data and context_data.get("lastConversation"):
                last_query = context_data["lastConversation"].get("query")
                last_response = context_data["lastConversation"].get("response")
                if last_query and last_response:
                    messages.append({"role": "user", "content": last_query})
                    messages.append({"role": "assistant", "content": last_response})
            
            # Add current query
            messages.append({"role": "user", "content": query})
            
            # Generate response using OpenAI
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=messages,
                max_tokens=300,
                temperature=0.7,
                response_format={ "type": "json_object" },
                functions=[{
                    "name": "provide_response",
                    "description": "Provides a response to the user with optional navigation",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "response_message": {
                                "type": "string",
                                "description": "The text response to display to the user"
                            },
                            "goto": {
                                "type": "string",
                                "description": "The destination to navigate to (dashboard, settings, savings, history, lists)",
                                "enum": ["dashboard", "settings", "savings", "history", "lists", None]
                            }
                        },
                        "required": ["response_message"]
                    }
                }],
                function_call={"name": "provide_response"}
            )
            
            # Extract the response JSON
            function_call = response.choices[0].message.function_call
            if function_call and function_call.arguments:
                try:
                    response_data = json.loads(function_call.arguments)
                    logger.info(f"Structured response: {response_data}")
                    
                    # Return structured response with goto field
                    return {
                        "response_message": response_data.get("response_message", "I'm not sure how to respond to that."),
                        "goto": response_data.get("goto")
                    }
                except json.JSONDecodeError:
                    logger.error("Failed to parse function call arguments as JSON")
            
            # Fallback to simple text response if function call parsing fails
            response_text = response.choices[0].message.content.strip() if response.choices[0].message.content else "I'm not sure how to respond to that."
            logger.info(f"LLM response (fallback): {response_text}")
            
            return {
                "response_message": response_text
            }
            
        except Exception as e:
            logger.error(f"Error in extension handler: {str(e)}", exc_info=True)
            return {
                "response_message": "I encountered an error processing your request. Please try again."
            } 