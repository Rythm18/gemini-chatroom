import google.generativeai as genai
from typing import Optional, Dict, Any, List
from app.core.config import settings
import logging
import asyncio
import time

logger = logging.getLogger(__name__)

class GeminiService:
    
    def __init__(self):
        """Initialize Gemini service with API key"""
        self.model = None
        self.is_configured = False
        self._configure_api()
    
    def _configure_api(self) -> None:
        """Configure Google Gemini API"""
        try:
            if not settings.GOOGLE_API_KEY:
                logger.warning("Google API key not configured. Gemini service will use mock responses.")
                return
            
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self.is_configured = True
            
            logger.info("Google Gemini API configured successfully")
            
        except Exception as e:
            logger.error(f"Failed to configure Gemini API: {e}")
            self.is_configured = False
    
    def is_available(self) -> bool:
        """Check if Gemini service is available"""
        return self.is_configured and self.model is not None
    
    async def generate_response(
        self, 
        user_message: str, 
        conversation_history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate AI response using Google Gemini
        
        Args:
            user_message: The user's message
            conversation_history: Previous messages for context
            system_prompt: Optional system prompt for behavior customization
            
        Returns:
            dict: Response with AI-generated content and metadata
        """
        start_time = time.time()
        
        try:
            if not self.is_available():
                return await self._generate_mock_response(user_message, start_time)
            
            context = self._build_conversation_context(
                user_message, 
                conversation_history, 
                system_prompt
            )
            
            response = await self._call_gemini_api(context)
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "content": response.strip(),
                "processing_time": processing_time,
                "model": "gemini-2.0-flash-lite",
                "token_count": len(response.split()) if response else 0
            }
            
        except Exception as e:
            logger.error(f"Error generating Gemini response: {e}")
            processing_time = time.time() - start_time
            
            return {
                "success": False,
                "error": str(e),
                "processing_time": processing_time,
                "fallback_response": "I apologize, but I'm experiencing technical difficulties. Please try again later."
            }
    
    def _build_conversation_context(
        self, 
        user_message: str, 
        conversation_history: Optional[List[Dict[str, str]]], 
        system_prompt: Optional[str]
    ) -> str:
        """
        Build conversation context for Gemini API
        
        Args:
            user_message: Current user message
            conversation_history: Previous conversation messages
            system_prompt: System behavior prompt
            
        Returns:
            str: Formatted conversation context
        """
        context_parts = []
        
        if system_prompt:
            context_parts.append(f"System: {system_prompt}")
        else:
            context_parts.append(
                "System: You are a helpful AI assistant in a chatroom. "
                "Provide informative, engaging, and helpful responses. "
                "Keep responses concise but comprehensive."
            )
        
        if conversation_history:
            context_parts.append("\nConversation History:")
            for entry in conversation_history[-10:]:
                role = entry.get("role", "user")
                content = entry.get("content", "")
                context_parts.append(f"{role.capitalize()}: {content}")
        
        context_parts.append(f"\nUser: {user_message}")
        context_parts.append("AI Assistant:")
        
        return "\n".join(context_parts)
    
    async def _call_gemini_api(self, context: str) -> str:
        """
        Make async call to Gemini API
        
        Args:
            context: The conversation context
            
        Returns:
            str: AI-generated response
        """
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                self._sync_gemini_call, 
                context
            )
            return response
            
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            raise
    
    def _sync_gemini_call(self, context: str) -> str:
        """
        Synchronous call to Gemini API
        
        Args:
            context: The conversation context
            
        Returns:
            str: AI-generated response
        """
        try:
            response = self.model.generate_content(context)
            
            if response.text:
                return response.text
            else:
                logger.warning("Empty response from Gemini API")
                return "I apologize, but I couldn't generate a response. Please try again."
                
        except Exception as e:
            logger.error(f"Gemini API sync call error: {e}")
            raise
    
    async def _generate_mock_response(self, user_message: str, start_time: float) -> Dict[str, Any]:
        """
        Generate mock response when API is not available
        
        Args:
            user_message: The user's message
            start_time: Request start time
            
        Returns:
            dict: Mock response
        """
        mock_responses = {
            "hello": "Hello! How can I help you today?",
            "hi": "Hi there! What would you like to know?",
            "help": "I'm here to assist you with any questions you have. Feel free to ask me anything!",
            "how are you": "I'm doing well, thank you for asking! How can I assist you today?",
            "what": "That's an interesting question! Could you provide more details so I can give you a better answer?",
            "why": "Great question! Let me think about that and provide you with a comprehensive answer.",
            "when": "Timing can be important! Let me help you understand when this might happen.",
            "where": "Location matters! Let me provide you with relevant information about where to find what you're looking for."
        }
        
        user_lower = user_message.lower()
        response = "Thank you for your message! I understand you're asking about something important. " \
                  "While I'm currently in demo mode, I'd be happy to help you explore this topic further. " \
                  "Could you tell me more about what specifically you'd like to know?"
        
        for keyword, mock_response in mock_responses.items():
            if keyword in user_lower:
                response = mock_response
                break
        
        if "?" in user_message:
            response = f"That's a great question! {response}"
        elif len(user_message.split()) > 10:
            response = "I can see you've shared quite a bit of detail. " + response
        
        processing_time = time.time() - start_time
        
        return {
            "success": True,
            "content": response,
            "processing_time": processing_time,
            "model": "mock-gemini",
            "token_count": len(response.split()),
            "is_mock": True
        }
    
    async def analyze_message_safety(self, message: str) -> Dict[str, Any]:
        """
        Analyze message for safety and content policy compliance
        
        Args:
            message: Message to analyze
            
        Returns:
            dict: Safety analysis result
        """
        try:
            flagged_words = ["spam", "abuse", "harmful", "inappropriate"]
            is_safe = not any(word in message.lower() for word in flagged_words)
            
            return {
                "is_safe": is_safe,
                "confidence": 0.95 if is_safe else 0.8,
                "categories": [] if is_safe else ["potential_spam"],
                "message": "Content appears safe" if is_safe else "Content may need review"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing message safety: {e}")
            return {
                "is_safe": True,
                "confidence": 0.5,
                "categories": [],
                "message": "Safety analysis unavailable"
            }
    
    def get_conversation_context(
        self, 
        messages: List[Dict[str, Any]], 
        max_messages: int = 10
    ) -> List[Dict[str, str]]:
        """
        Convert database messages to conversation context format
        
        Args:
            messages: List of message objects
            max_messages: Maximum number of messages to include
            
        Returns:
            List[Dict]: Formatted conversation history
        """
        try:
            context = []
            
            recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages
            
            for message in recent_messages:
                role = "assistant" if message.get("message_type") == "ai" else "user"
                content = message.get("content", "")
                
                if content.strip():
                    context.append({
                        "role": role,
                        "content": content
                    })
            
            return context
            
        except Exception as e:
            logger.error(f"Error building conversation context: {e}")
            return []

gemini_service = GeminiService() 