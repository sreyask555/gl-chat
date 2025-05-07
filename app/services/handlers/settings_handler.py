from typing import Dict, Any
import json
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class SettingsHandler:
    def __init__(self, openai_client):
        logger.info("Initializing SettingsHandler")
        self.openai_client = openai_client
        # Default model configuration
        self.model = "gpt-3.5-turbo"
        self.temperature = 0.7
        self.max_tokens = 250

    def process_query(self, query: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a settings-related chat query and return a simple response without actions.
        This method is specifically for the settings page chat assistant.
        """
        try:
            logger.info("Processing settings query")
            
            # Build system prompt based on available context
            system_prompt = "You are a helpful assistant for the settings page of a Goodlife shopping application. "
            system_prompt += "Provide concise, friendly responses about the user's profile, credit cards, and memberships. "
            
            # Add context about the user profile if available
            if context_data.get('profile'):
                profile = context_data['profile']
                system_prompt += f"The user's name is {profile.get('firstName', '')} {profile.get('lastName', '')}. "
                system_prompt += f"Their email is {profile.get('email', '')}. "
            
            # Add detailed context about credit cards if available
            if context_data.get('creditCards'):
                cards = context_data['creditCards']
                if cards.get('userCards') and len(cards.get('userCards', [])) > 0:
                    user_cards = cards['userCards']
                    system_prompt += f"The user has {len(user_cards)} saved credit card(s): "
                    card_names = []
                    for card in user_cards:
                        card_info = card.get('creditCardId', {}).get('cardInfo', {})
                        card_name = card_info.get('cardName', '')
                        card_issuer = card_info.get('cardIssuer', '')
                        card_network = card_info.get('cardNetwork', '')
                        if card_name:
                            card_detail = card_name
                            if card_issuer:
                                card_detail += f" from {card_issuer}"
                            if card_network:
                                card_detail += f" ({card_network})"
                            card_names.append(card_detail)
                    
                    system_prompt += ", ".join(card_names) + ". "
                
                if cards.get('availableCards') and len(cards.get('availableCards', [])) > 0:
                    available_cards = cards['availableCards']
                    system_prompt += f"There are {len(available_cards)} available credit card types that could be added. "
                    # Include some examples of available cards
                    if len(available_cards) > 0:
                        example_cards = [card.get('cardInfo', {}).get('cardName', '') for card in available_cards[:3] if card.get('cardInfo', {}).get('cardName', '')]
                        if example_cards:
                            system_prompt += f"Examples include: {', '.join(example_cards)}. "
            
            # Add context about memberships if available
            if context_data.get('memberships'):
                memberships = context_data['memberships']
                active_memberships = [m for m in memberships if m.get('active') == True]
                inactive_memberships = [m for m in memberships if m.get('active') == False]
                
                if active_memberships:
                    membership_details = []
                    for m in active_memberships:
                        name = m.get('membership_id', {}).get('membership_name', '')
                        tier = m.get('tier', '')
                        if name and tier and tier != "Not a member":
                            membership_details.append(f"{name} ({tier})")
                        elif name:
                            membership_details.append(name)
                    
                    if membership_details:
                        system_prompt += f"The user has active memberships with: {', '.join(membership_details)}. "
                
                if inactive_memberships:
                    inactive_names = [m.get('membership_id', {}).get('membership_name', '') for m in inactive_memberships if m.get('membership_id', {}).get('membership_name', '')]
                    if inactive_names:
                        system_prompt += f"The user previously had memberships with: {', '.join(inactive_names)} (now inactive). "
            
            # Add instructions for response generation
            system_prompt += """
            Guidelines for your responses:
            1. Be concise and direct - provide helpful information about the user's settings.
            2. Answer questions about their profile, credit cards, and memberships accurately.
            3. For credit card questions, provide specific information about their cards when relevant.
            4. For membership questions, mention their active memberships and relevant benefits.
            5. Do not suggest making changes to settings directly - only provide information.
            6. If asked about card benefits or rewards, provide general information about the types of cards they have.
            7. Keep responses brief but informative, focusing on answering the user's question directly.
            8. If asked about a card or membership they don't have, acknowledge this and suggest alternatives if appropriate.
            9. Personalize your responses using their name occasionally.
            10. Do not invent details that aren't provided in the context.
            11. If the user asks about a specific detail not provided in the context, say you don't have that specific information.
            """
            
            # Prepare messages for OpenAI chat completion
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add last conversation context if available
            last_conversation = context_data.get('lastConversation', {})
            last_query = last_conversation.get('query')
            last_response = last_conversation.get('response')
            
            if last_query and last_response:
                logger.info("Adding last conversation to chat context")
                messages.append({"role": "user", "content": last_query})
                messages.append({"role": "assistant", "content": last_response})
            
            # Add current query
            messages.append({"role": "user", "content": query})
            
            # Call OpenAI for chat completion
            client = self.openai_client
            completion = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            # Extract the response content
            response_content = completion.choices[0].message.content.strip()
            logger.debug(f"OpenAI response: {response_content}")
            
            # Return response in consistent format
            return {
                "generalResponse": response_content
            }
            
        except Exception as e:
            logger.error(f"Error in process_query: {str(e)}", exc_info=True)
            return {
                "generalResponse": "I'm sorry, I encountered an error while processing your request. Please try again later."
            } 