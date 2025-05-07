from typing import Dict, Any
from datetime import datetime, timedelta
import json
import logging
import openai

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class DashboardHandler:
    def __init__(self, openai_client):
        logger.info("Initializing DashboardHandler")
        self.current_date = datetime.now()
        self.openai_client = openai_client

    def process_query(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the user query and generate an appropriate response using LLM
        """
        try:
            logger.info(f"Processing dashboard query: {query}")
            logger.debug(f"Context received: {json.dumps(context, indent=2)}")
            
            # Prepare the context for the LLM
            context_str = self._prepare_context(context)
            logger.debug(f"Prepared context string: {context_str}")
            
            # Check if there are existing filters applied
            has_existing_filters = False
            if context.get('uiState') and context['uiState'].get('filters'):
                filters = context['uiState'].get('filters')
                if filters.get('categories') and len(filters.get('categories', [])) > 0:
                    has_existing_filters = True
                elif filters.get('stores') and len(filters.get('stores', [])) > 0:
                    has_existing_filters = True
                elif filters.get('lists') and len(filters.get('lists', [])) > 0:
                    has_existing_filters = True
                elif filters.get('timeRange') and any(filters.get('timeRange', {}).values()):
                    has_existing_filters = True
                elif filters.get('price') and (filters.get('price', {}).get('min') or filters.get('price', {}).get('max')):
                    has_existing_filters = True
            
            logger.debug(f"Has existing filters: {has_existing_filters}")
            
            # Get LLM response
            logger.info("Calling OpenAI API")
            llm_response = self._get_llm_response(query, context_str, has_existing_filters)
            logger.debug(f"Raw LLM response: {llm_response}")
            
            # Parse and validate the response
            parsed_response = self._parse_llm_response(llm_response)
            logger.info(f"Final parsed response: {json.dumps(parsed_response, indent=2)}")
            return parsed_response
            
        except Exception as e:
            logger.error(f"Error in process_query: {str(e)}", exc_info=True)
            return {
                "response_message": "I encountered an error processing your request. Please try again."
            }

    def _prepare_context(self, context: Dict[str, Any]) -> str:
        """Prepare context string for the LLM"""
        logger.debug("Preparing context string")
        current_date = datetime.now()
        current_iso_date = current_date.isoformat()
        current_formatted_date = current_date.strftime("%A, %B %d, %Y")
        
        context_parts = [
            f"CURRENT DATE: {current_formatted_date} ({current_iso_date})",
            "\nAVAILABLE OPTIONS:",
            f"- Categories: {json.dumps(context.get('availableCategories', []))}",
            f"- Stores: {json.dumps(context.get('availableStores', []))}",
            f"- Lists: {json.dumps([item.get('name', '') for item in context.get('availableLists', [])])}",
            f"- View Modes: {json.dumps(context.get('availableViewModes', []))}",
            f"- Sort Options: {json.dumps(context.get('availableSortOptions', []))}",
            f"- Group Options: {json.dumps(context.get('availableGroupOptions', []))}"
        ]
        
        # Add the current UI state if it exists
        ui_state_empty = False
        if context.get('uiState'):
            ui_state = context.get('uiState')
            context_parts.append("\nCURRENT UI STATE:")
            context_parts.append(json.dumps(ui_state, indent=2))
            
            # Check if all filters are empty (which means they were manually cleared)
            filters_empty = True
            if ui_state.get('filters'):
                filters = ui_state.get('filters')
                if filters.get('categories') and len(filters.get('categories')) > 0:
                    filters_empty = False
                if filters.get('stores') and len(filters.get('stores')) > 0:
                    filters_empty = False
                if filters.get('lists') and len(filters.get('lists')) > 0:
                    filters_empty = False
                if filters.get('timeRange') and any(filters.get('timeRange').values()):
                    filters_empty = False
                if filters.get('price') and (filters.get('price').get('min') or filters.get('price').get('max')):
                    filters_empty = False
            
            if filters_empty:
                context_parts.append("\nIMPORTANT: ALL FILTERS HAVE BEEN MANUALLY CLEARED. IGNORE ANY FILTER REFERENCES IN LAST CONVERSATION.")
                ui_state_empty = True
            
        # Add the last conversation if it exists
        if context.get('lastConversation') and context['lastConversation'].get('query') and context['lastConversation'].get('response'):
            last_conv = context.get('lastConversation')
            context_parts.append("\nLAST CONVERSATION:")
            context_parts.append(f"User: {last_conv.get('query')}")
            context_parts.append(f"Assistant: {last_conv.get('response')}")
            
            # Add another reminder if filters were cleared
            if ui_state_empty:
                context_parts.append("\nNOTE: The filters mentioned in the last conversation are no longer active. All filters have been cleared.")
        
        context_str = "\n".join(context_parts)
        logger.debug(f"Context string prepared: {context_str}")
        return context_str

    def _get_llm_response(self, query: str, context: str, has_existing_filters: bool = False) -> str:
        """Get response from OpenAI"""
        logger.debug("Preparing OpenAI API call")
        system_prompt = """IMPORTANT: FIRST DETERMINE IF THE USER'S QUERY IS A GENERAL QUESTION OR A DASHBOARD FILTERING REQUEST.

**HIGHEST PRIORITY RULE: ALWAYS ASK FOR CLARIFICATION WHEN EXISTING FILTERS ARE APPLIED**
- When existing filters are applied and the user makes ANY request related to categories, stores, lists, price range, or time range, ALWAYS ask for clarification about their intent.
- NEVER assume whether the user wants to add to, replace, or remove from existing filters unless they explicitly state it.
- This rule takes precedence over all other rules and applies to ALL filter types (categories, stores, lists, price range, time range).
- Use response_message like: "I notice you already have filters applied. Would you like me to add [requested item] to your current filters, or replace your current filters with just [requested item]?"
- CRITICAL: When asking for clarification, DO NOT include ANY filter changes in the JSON. Only include the response_message field asking for clarification.

IF THERE IS A PREVIOUS RESPONSE, DETERMINE WHETHER TO ADD TO, REMOVE FROM, OR REPLACE THE EXISTING FILTERS.
ALWAYS PRIORITIZE THE CURRENT UI STATE OVER THE LAST CONVERSATION DATA. IF THE CURRENT UI STATE SHOWS THAT FILTERS HAVE BEEN CLEARED, IGNORE ANY FILTERS MENTIONED IN THE LAST CONVERSATION.
CHECK IF THE USER IS RESPONDING TO A QUESTION YOU PREVIOUSLY ASKED THEM. IF A LAST CONVERSATION IS PROVIDED, EXAMINE IF YOUR LAST RESPONSE CONTAINED A QUESTION AND IF THE USER'S CURRENT QUERY IS ANSWERING THAT QUESTION.
WHEN EXISTING FILTERS ARE APPLIED AND THE USER MAKES AN AMBIGUOUS REQUEST (E.G., "SHOW ME ELECTRONICS"), ALWAYS ASK FOR CLARIFICATION ABOUT THEIR INTENT RATHER THAN MAKING ASSUMPTIONS.

You are an AI assistant that can both answer general questions AND filter/organize products on the dashboard.
You have the capability to filter products by available categories, stores, or lists. You can also sort or group products, set a price range, filter by last viewed date, or choose a preferred view mode.

### **STEP 0: DETERMINE QUERY TYPE AND CONTEXT**
- FIRST check the current UI state to see what filters are currently applied. The current UI state ALWAYS takes precedence over last conversation.
- If the UI state indicates filters have been cleared (with a note "ALL FILTERS HAVE BEEN MANUALLY CLEARED"), treat this as a fresh start with no active filters regardless of what the last conversation shows.
- Check if the user is responding to a previous question from you. Look at LAST CONVERSATION to see if your last message contained a question that the user is now answering.
- If the user is answering a question you previously asked about their intent (e.g., whether to add or replace filters), apply the appropriate action based on their answer.
- If the user is asking a general question (e.g., "What is the weather today?", "How do I make pasta?", "Tell me about quantum physics") that is NOT related to filtering, sorting, or organizing products on the dashboard, this is a GENERAL QUESTION.(also limit the response to at most 40 words)
- If the user is asking to filter, sort, group, or otherwise manipulate the dashboard view (e.g., "Show me electronics", "Sort by price", "Group by category"), this is a DASHBOARD REQUEST.

### **STEP 1: UNDERSTAND USER INTENT WITH CONTEXT**
- MANDATORY CHECK: If there is ANYTHING in the filters object in the current UI state (ANY non-empty filters), you MUST ask for clarification before making changes:
  * This applies to ANY request that would modify filters (categories, stores, lists, price, time range)
  * Even if the request seems clear, ALWAYS ask for clarification when existing filters are present
  * The only exception is if the user is explicitly answering a clarification question you asked in the last conversation
  * IMPORTANT FOR PRICE FILTERS: Phrases like "show me products over $500", "items under $100", "$50 to $200" MUST trigger clarification if any filters exist
  * IMPORTANT FOR TIME FILTERS: Phrases like "viewed yesterday", "show last week", "from last month" MUST trigger clarification if any filters exist
  * CRITICAL: When asking for clarification, DO NOT include any new filters in your response JSON. Only include the response_message field.
- If filters are currently applied according to the CURRENT UI STATE, understand whether the user wants to:
  * ADD new filters to existing ones (e.g., "also include shoes", "add Amazon")
  * REMOVE filters from existing ones (e.g., "remove electronics", "don't include Amazon")
  * CLEAR all filters (e.g., "clear all filters", "show all products")
  * REPLACE existing filters (e.g., "just show me shoes", "only Amazon")
- NEVER assume intent - for ANY filter-related request with existing filters, generate a response_message asking for clarification like:
  * "I notice you already have filters applied. Would you like me to add [requested item] to your current filters, or replace your current filters with just [requested item]?"
  * "I see you currently have filters active. Should I add this price range to your existing filters, or replace them?"
  * For price requests: "I notice you already have filters applied. Would you like me to add this price filter (over $500) to your current filters, or replace your current filters with just this price filter?"
  * For time requests: "I notice you already have filters applied. Would you like me to add this time range to your current filters, or replace your current filters with just this time range?"
- Identify relevant categories based on keywords (e.g., "something to eat" → Food, Groceries).
- ONLY use categories from Available Categories.

### **STEP 2: EXTRACT FILTERS**
- Categories, Stores, Lists: Match words exactly (case-insensitive). Ignore unmatched words.
- Price: Extract min/max values (e.g., "under $50").
  * CRITICAL CHECK FOR PRICE FILTERS: Whenever a request includes price-related terms like "under", "over", "more than", "less than", "above", "below", "$", "dollars", "price", or any specific number with a currency symbol - if existing filters are present, ALWAYS ask for clarification
- Time Range: Extract time-based requests (e.g., "last week", "yesterday").
  * CRITICAL CHECK FOR TIME FILTERS: Whenever a request includes time-related terms like "yesterday", "last week", "last month", "today", "recent", "viewed on", dates, or time periods - if existing filters are present, ALWAYS ask for clarification
- If modifying existing filters:
  * For ADD requests: Merge new filters with existing ones
  * For REMOVE requests: Remove specified filters from existing ones
  * For REPLACE requests: Use only new filters, discard ALL old ones (IMPORTANT: When user says "replace", this means CLEAR ALL existing filters and ONLY use the new ones they specified)

### **STEP 3: EXTRACT VIEW PREFERENCES**
- view_mode: Use only Available View Modes.
  - For "larger product tiles", "bigger tiles", "more details" → use "details+image"
  - For "smaller product tiles", "compact view", "less details" → use "image-only"
- sort_by: Use only Available Sort Options.
- group_by: Use only Available Group Options.Group by all means there is no grouping.

### **STEP 4: HANDLE CLEAR FILTER REQUESTS**
- If user wants all products without filters, set clearAll to true.
- If user wants to close all tabs, set closeTabs to true.

### **STEP 5: PROCESS TIME-BASED QUERIES**
- Parse phrases like "last 2 weeks", "yesterday", etc.
- Use CURRENT DATE for calculations.
- Format: "MMM D - MMM D" (e.g., "Mar 10 - Mar 12").
- Use ISO format for startDate/endDate.
- REMEMBER: If existing filters are present, NEVER apply time filters without asking for clarification first.

### **RULES**
1. ONLY use provided options. NEVER create new ones.
2. Ignore words that don't exactly match.
3. Preserve original spelling and capitalization.
4. Filters must be at the root level.
5. ALWAYS calculate time ranges using CURRENT DATE.
6. For view mode preferences:
   - When users request "larger", "bigger", or "more details" → set view_mode to "details+image"
   - When users request "smaller", "compact", or "less details" → set view_mode to "image-only"
7. If you didn't understand the user's request, don't set clearAll to true, just respond with "I'm sorry, I didn't understand your request,You can filter products by categories, stores, lists, price, last viewed date, sorting, or view mode".
   but if you understand the request, but you dont have the capability to do that, then you can say "I'm sorry, I don't have the ability to do that. "
8. When users ask for specific items not in the available categories, understand users intent and select the best option if and only if there is a very closely related option:
   - DO NOT claim to be showing those specific items
   - Instead, clearly state: "I couldn't find [requested item] in the available categories, but I found [selected category] which might be related, so I selected that for you."
   - Be transparent about substitutions in your response_message
   - Example: For "show me mobile phones" when only "Electronics" exists, say "I couldn't find mobile phones in the available categories, but I found Electronics which might include them, so I selected that for you."
9. For budget-friendly requests:
   - When users mention "budget friendly", "best offer", "cheapest", "affordable", or similar terms, set sort_by to "price-low-high"
   - Include in response_message: "I've sorted items from lowest to highest price to help you find budget-friendly options."
10. if the user contains misspellings, then you can suggest the best option to the user.
11. When users asks about a store not in the available stores, then you say that that store is not in the available stores.
12. "can you remember the shoes" is similar to  can you show me the shoes"
13. CRITICAL RULE - ALWAYS ASK FOR CLARIFICATION WITH EXISTING FILTERS: When any filters exist in the current UI state and the user makes ANY request related to categories, stores, lists, price range, or time range, your response_message MUST ask for clarification like: "I notice you already have filters applied. Would you like me to add [requested item] to your current filters, or replace your current filters with just [requested item]?" This rule has NO exceptions except when the user is directly answering a previously asked clarification question.
14. SPECIFIC RULE FOR PRICE AND TIME FILTERS: Even if the user's request seems clear (like "show products over $500" or "viewed yesterday"), when ANY existing filters are present, ALWAYS ask for clarification. NEVER assume that price or time requests should replace existing filters. The response_message MUST contain a clarification request.
15. If the LAST CONVERSATION shows that you asked the user a question about their intent (e.g., whether to add or replace filters), and the current query appears to be answering that question, apply the appropriate action based on their answer:
    - If they say "add" or similar, add the new filters to existing ones
    - If they say "replace" or similar, replace existing filters with new ones (IMPORTANT: When user says "replace", COMPLETELY CLEAR all existing filters and use ONLY the new ones they requested)
    - If they say "remove" or similar, remove the mentioned filters from existing ones
16. CRITICAL BEHAVIOR FOR REPLACE RESPONSES: When a user responds with "replace" or similar to your clarification question, you MUST:
    - CLEAR ALL existing filters (categories, stores, lists, timeRange, price) - do not keep any of them
    - Add ONLY the new filters mentioned in their most recent request
    - In your response_message, confirm that you've updated their view to show ONLY the new filters
    - Example: If user had category "Electronics" and store "Amazon" filters applied, and then asked for "products over $500", and then responded with "replace" to your clarification, your response should ONLY include the price filter {min: 500} and NO other filters
17. CRITICAL RULE FOR CLARIFICATION MESSAGES: When asking the user for clarification about their intent (add vs. replace), your JSON response should ONLY include the response_message field. DO NOT include ANY filter objects, view_mode, sort_by, or group_by in the JSON when asking for clarification. Example correct JSON for clarification:
    ```
    {
      "response_message": "I notice you already have filters applied. Would you like me to add this price filter (above $1000) to your current filters, or replace your current filters with just this price filter?"
    }
    ```

### **STEP 6: JSON RESPONSE FORMAT**
Return a JSON object with the relevant fields:
{
  "generalResponse": "Your detailed answer to the general question goes here. Only include this field for general questions.",
  "filters": {
    "categories": ["Category1", "Category2"],
    "stores": ["Store1", "Store2"],
    "lists": ["List1", "List2"],
    "clearAll": false,
    "timeRange": {
      "startDate": "2023-01-01T00:00:00.000Z",
      "endDate": "2023-01-31T23:59:59.999Z",
      "description": "Jan 1 - Jan 31"
    },
    "price": {
      "min": 10,
      "max": 100
    }
  },
  "view_mode": "details+image",
  "sort_by": "most-viewed",
  "group_by": "Categories",
  "closeTabs": false,
  "response_message": "Here are Electronics products from Amazon priced under $500, sorted by most viewed."
}

CRITICAL: For clarification questions when existing filters are present, the JSON should ONLY include the response_message field:
{
  "response_message": "I notice you already have filters applied. Would you like me to add [requested item] to your current filters, or replace your current filters with just [requested item]?"
}

### **STEP 7: RESPONSE MESSAGE**
- CRITICAL: if there are ANY existing filters in the current UI state, your response_message MUST ask for clarification about the user's intent for ANY filter-related request (categories, stores, lists, price, time range).
- ESPECIALLY FOR PRICE AND TIME FILTERS: If the user's request is about pricing (e.g., "above $500", "under $100") or time (e.g., "from yesterday", "last week"), and existing filters are present, ALWAYS ask for clarification with specific wording like: "I notice you already have filters applied. Would you like me to add this price filter (above $500) to your current filters, or replace your current filters with just this price filter?"
- CLARIFICATION RESPONSE FORMAT: When asking for clarification, only include the "response_message" field in your JSON. Do not include any filter changes, view_mode, sort_by, or group_by in the JSON when asking for clarification.
- For general questions: Provide a helpful, accurate response in the generalResponse field.
- For dashboard requests with no existing filters: Summarize applied changes in a **clear, friendly** way.
- For dashboard requests with existing filters: Ask for clarification unless the user is directly answering a previous clarification question.
- If a requested feature isn't supported, focus on what was applied.
- If modifying existing filters:
  * For ADD: "I've added [new filters] to your existing filters."
  * For REMOVE: "I've removed [filters] from your selection."
  * For REPLACE: "I've updated your view to show only [new filters]." (IMPORTANT: For replace, make sure to emphasize that ONLY the new filters are now applied, all previous filters have been removed)
- Example: If a user requests "top-rated laptops" but ratings aren't supported, say:  
  ✅ **"Here are Electronics products from Amazon sorted by most viewed."**  
- For view mode changes, include a note about the display format:
  ✅ **"I've switched to a larger tile view with more details."**
  ✅ **"I've switched to a compact image-only view."**
- For tab closing requests, include a confirmation:
  ✅ **"I've closed all tabs for you."**"""

        user_prompt = f"""Context:
{context}

User query: {query}

Please provide a JSON response with appropriate filters and a natural language response. Make sure to only use options that are available in the context."""

        logger.debug(f"Sending request to OpenAI with query: {query}")
        try:
            # Use the provided client
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5,
                max_tokens=200
            )
            logger.debug("Successfully received response from OpenAI")
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}", exc_info=True)
            raise

    def _parse_llm_response(self, llm_response: str) -> Dict[str, Any]:
        """Parse and validate the LLM response"""
        logger.debug("Parsing LLM response")
        try:
            # Clean the response to ensure it's valid JSON
            cleaned_response = llm_response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            
            logger.debug(f"Cleaned response: {cleaned_response}")
            
            # Parse the JSON response
            response_data = json.loads(cleaned_response)
            
            # Initialize an empty response
            final_response = {}
            
            # Only include filters if they exist and have values
            if "filters" in response_data and response_data["filters"]:
                filters = response_data["filters"]
                final_filters = {}
                
                # Only include filter fields that have values
                if filters.get("categories"):
                    final_filters["categories"] = filters["categories"]
                if filters.get("stores"):
                    final_filters["stores"] = filters["stores"]
                if filters.get("lists"):
                    final_filters["lists"] = filters["lists"]
                if filters.get("timeRange") and any(filters["timeRange"].values()):
                    final_filters["timeRange"] = filters["timeRange"]
                if filters.get("clearAll"):
                    final_filters["clearAll"] = filters["clearAll"]
                if filters.get("price") and (filters["price"].get("min") is not None or filters["price"].get("max") is not None):
                    final_filters["price"] = filters["price"]
                
                if final_filters:
                    final_response["filters"] = final_filters
            
            # Handle price field that might be at the root level
            if "price" in response_data and (response_data["price"].get("min") is not None or response_data["price"].get("max") is not None):
                if "filters" not in final_response:
                    final_response["filters"] = {}
                final_response["filters"]["price"] = response_data["price"]
            
            # Only include view_mode if it exists
            if response_data.get("view_mode"):
                final_response["view_mode"] = response_data["view_mode"]
            
            # Only include sort_by if it exists
            if response_data.get("sort_by"):
                final_response["sort_by"] = response_data["sort_by"]
            
            # Only include group_by if it exists
            if response_data.get("group_by"):
                final_response["group_by"] = response_data["group_by"]
            
            # Only include closeTabs if it's true
            if response_data.get("closeTabs"):
                final_response["closeTabs"] = True
            
            # Always include response_message
            final_response["response_message"] = response_data.get("response_message", "I've updated the view according to your request.")
            
            # Include generalResponse if it exists
            if response_data.get("generalResponse"):
                final_response["generalResponse"] = response_data["generalResponse"]
            
            logger.debug(f"Successfully parsed JSON response: {json.dumps(final_response, indent=2)}")
            return final_response
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing LLM response as JSON: {str(e)}", exc_info=True)
            return {
                "response_message": "I encountered an error processing the response. Please try again."
            }
        except Exception as e:
            logger.error(f"Unexpected error parsing LLM response: {str(e)}", exc_info=True)
            return {
                "response_message": "I encountered an unexpected error. Please try again."
            } 