from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from app.models.message import Message, MessageType, MessageStatus
from app.models.user import User, SubscriptionTier
from app.models.daily_usage import DailyUsage
from app.models.chatroom import Chatroom
from app.schemas.chatroom import MessageCreate, MessageResponse, AIMessageResponse, UsageResponse
from app.tasks.message_tasks import process_ai_message
from app.services.gemini_service import gemini_service
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class MessageService:
    
    @staticmethod
    def check_daily_usage(user_id: int, db: Session) -> Dict[str, Any]:
        """
        Check user's daily usage and limits
        
        Args:
            user_id: The user ID
            db: Database session
            
        Returns:
            dict: Usage information and whether user can send messages
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {
                    "success": False,
                    "error": "User not found"
                }
            
            if user.subscription_tier == SubscriptionTier.PRO:
                return {
                    "success": True,
                    "can_send_message": True,
                    "daily_usage": 0,
                    "daily_limit": -1,
                    "remaining_today": -1,
                    "subscription_tier": user.subscription_tier.value
                }
            
            today = date.today()
            daily_usage = db.query(DailyUsage).filter(
                DailyUsage.user_id == user_id,
                DailyUsage.date == today
            ).first()
            
            current_usage = daily_usage.message_count if daily_usage else 0
            daily_limit = settings.BASIC_TIER_DAILY_LIMIT
            remaining = max(0, daily_limit - current_usage)
            can_send = current_usage < daily_limit
            
            return {
                "success": True,
                "can_send_message": can_send,
                "daily_usage": current_usage,
                "daily_limit": daily_limit,
                "remaining_today": remaining,
                "subscription_tier": user.subscription_tier.value
            }
            
        except Exception as e:
            logger.error(f"Error checking daily usage: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def increment_daily_usage(user_id: int, db: Session) -> bool:
        """
        Increment user's daily usage count
        
        Args:
            user_id: The user ID
            db: Database session
            
        Returns:
            bool: Success status
        """
        try:
            today = date.today()
            daily_usage = db.query(DailyUsage).filter(
                DailyUsage.user_id == user_id,
                DailyUsage.date == today
            ).first()
            
            if daily_usage:
                daily_usage.message_count += 1
            else:
                daily_usage = DailyUsage(
                    user_id=user_id,
                    date=today,
                    message_count=1
                )
                db.add(daily_usage)
            
            db.commit()
            logger.info(f"Incremented daily usage for user {user_id}: {daily_usage.message_count}")
            return True
            
        except Exception as e:
            logger.error(f"Error incrementing daily usage: {e}")
            db.rollback()
            return False
    
    @staticmethod
    def create_user_message(
        user_id: int, 
        chatroom_id: int, 
        message_data: MessageCreate, 
        db: Session
    ) -> Dict[str, Any]:
        """
        Create a user message and trigger AI response
        
        Args:
            user_id: The user ID
            chatroom_id: The chatroom ID
            message_data: Message creation data
            db: Database session
            
        Returns:
            dict: Message creation result
        """
        try:
            chatroom = db.query(Chatroom).filter(
                Chatroom.id == chatroom_id,
                Chatroom.owner_id == user_id
            ).first()
            
            if not chatroom:
                return {
                    "success": False,
                    "message": "Chatroom not found or access denied",
                    "error": "Invalid chatroom"
                }
            
            usage_check = MessageService.check_daily_usage(user_id, db)
            if not usage_check.get("success"):
                return {
                    "success": False,
                    "message": "Unable to check usage limits",
                    "error": usage_check.get("error")
                }
            
            if not usage_check.get("can_send_message"):
                return {
                    "success": False,
                    "message": f"Daily message limit reached ({usage_check.get('daily_limit')} messages/day). Upgrade to Pro for unlimited messages.",
                    "error": "Rate limit exceeded",
                    "usage_info": usage_check
                }
            
    
            user_message = Message(
                content=message_data.content,
                message_type=MessageType.USER,
                status=MessageStatus.COMPLETED,
                user_id=user_id,
                chatroom_id=chatroom_id
            )
            
            db.add(user_message)
            db.commit()
            db.refresh(user_message)
            
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.subscription_tier == SubscriptionTier.BASIC:
                MessageService.increment_daily_usage(user_id, db)
            
            logger.info(f"User message created: {user_message.id}")
            
            return {
                "success": True,
                "message": "Message created successfully",
                "user_message": user_message
            }
            
        except Exception as e:
            logger.error(f"Error creating user message: {e}")
            db.rollback()
            return {
                "success": False,
                "message": "Failed to send message",
                "error": str(e)
            }
    
    @staticmethod
    async def generate_ai_response_sync(
        user_message_id: int,
        user_message_content: str,
        chatroom_id: int,
        user_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        Generate AI response synchronously and store in database
        
        Args:
            user_message_id: The user message ID
            user_message_content: The user's message content
            chatroom_id: The chatroom ID
            user_id: The user ID
            db: Database session
            
        Returns:
            dict: AI response generation result
        """
        try:
            logger.info(f"Generating AI response for message {user_message_id}")
            
            conversation_history = MessageService._get_conversation_history(chatroom_id, db)
            
            ai_response_result = await gemini_service.generate_response(
                user_message=user_message_content,
                conversation_history=conversation_history
            )
            
            if not ai_response_result.get("success"):
                ai_content = ai_response_result.get("fallback_response", "I apologize, but I'm unable to respond at the moment. Please try again.")
                logger.warning(f"AI generation failed for message {user_message_id}, using fallback")
            else:
                ai_content = ai_response_result.get("content", "")
            
            ai_message = Message(
                content=ai_content,
                message_type=MessageType.AI,
                status=MessageStatus.COMPLETED,
                user_id=user_id,
                chatroom_id=chatroom_id,
                parent_message_id=user_message_id
            )
            
            db.add(ai_message)
            db.commit()
            db.refresh(ai_message)
            
            logger.info(f"AI response generated successfully for message {user_message_id}")
            
            return {
                "success": True,
                "ai_message": ai_message,
                "processing_time": ai_response_result.get("processing_time", 0),
                "model": ai_response_result.get("model", "unknown")
            }
            
        except Exception as e:
            logger.error(f"Error generating AI response for message {user_message_id}: {e}")
            
            try:
                error_message = Message(
                    content="I apologize, but I encountered an error while processing your message. Please try again.",
                    message_type=MessageType.AI,
                    status=MessageStatus.COMPLETED,
                    user_id=user_id,
                    chatroom_id=chatroom_id,
                    parent_message_id=user_message_id
                )
                db.add(error_message)
                db.commit()
                db.refresh(error_message)
                
                return {
                    "success": True,
                    "ai_message": error_message,
                    "processing_time": 0,
                    "model": "error_fallback"
                }
                
            except Exception as commit_error:
                logger.error(f"Error creating fallback message: {commit_error}")
                db.rollback()
                
                return {
                    "success": False,
                    "error": str(e)
                }
    
    @staticmethod
    def _get_conversation_history(chatroom_id: int, db: Session, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent conversation history for context
        
        Args:
            chatroom_id: The chatroom ID
            db: Database session
            limit: Number of recent messages to fetch
            
        Returns:
            List[Dict]: Conversation history
        """
        try:
            recent_messages = db.query(Message).filter(
                Message.chatroom_id == chatroom_id,
                Message.status == MessageStatus.COMPLETED
            ).order_by(
                Message.created_at.desc()
            ).limit(limit).all()
            
            conversation = []
            for msg in reversed(recent_messages):
                role = "assistant" if msg.message_type == MessageType.AI else "user"
                conversation.append({
                    "role": role,
                    "content": msg.content
                })
            
            return conversation
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []
    
    @staticmethod
    def get_chatroom_messages(
        chatroom_id: int, 
        user_id: int, 
        db: Session,
        page: int = 1,
        per_page: int = 50,
        include_pending: bool = True
    ) -> Dict[str, Any]:
        """
        Get messages for a specific chatroom
        
        Args:
            chatroom_id: The chatroom ID
            user_id: The user ID (must be owner)
            db: Database session
            page: Page number for pagination
            per_page: Messages per page
            include_pending: Whether to include pending messages
            
        Returns:
            dict: Messages with pagination metadata
        """
        try:
            chatroom = db.query(Chatroom).filter(
                Chatroom.id == chatroom_id,
                Chatroom.owner_id == user_id
            ).first()
            
            if not chatroom:
                return {
                    "success": False,
                    "message": "Chatroom not found or access denied",
                    "error": "Invalid chatroom"
                }
            
            query = db.query(Message).filter(Message.chatroom_id == chatroom_id)
            
            if not include_pending:
                query = query.filter(Message.status.in_([MessageStatus.COMPLETED, MessageStatus.FAILED]))
            
            total_count = query.count()
            
            offset = (page - 1) * per_page
            messages = query.order_by(Message.created_at.asc()).offset(offset).limit(per_page).all()

            message_responses = []
            for msg in messages:
                message_dict = {
                    "id": msg.id,
                    "content": msg.content,
                    "message_type": msg.message_type.value,
                    "status": msg.status.value,
                    "user_id": msg.user_id,
                    "chatroom_id": msg.chatroom_id,
                    "parent_message_id": msg.parent_message_id,
                    "created_at": msg.created_at.isoformat(),
                    "updated_at": msg.updated_at.isoformat()
                }
                message_responses.append(message_dict)
            
            return {
                "success": True,
                "messages": message_responses,
                "total_count": total_count,
                "has_next": offset + per_page < total_count,
                "has_previous": page > 1,
                "page": page,
                "per_page": per_page
            }
            
        except Exception as e:
            logger.error(f"Error getting chatroom messages: {e}")
            return {
                "success": False,
                "message": "Failed to retrieve messages",
                "error": str(e)
            }
    
    @staticmethod
    def get_message_by_id(message_id: int, user_id: int, db: Session) -> Optional[Message]:
        """
        Get a specific message by ID (user must own the chatroom)
        
        Args:
            message_id: The message ID
            user_id: The user ID
            db: Database session
            
        Returns:
            Optional[Message]: The message if found and accessible
        """
        try:
            message = db.query(Message).join(Chatroom).filter(
                Message.id == message_id,
                Chatroom.owner_id == user_id
            ).first()
            
            return message
            
        except Exception as e:
            logger.error(f"Error getting message by ID: {e}")
            return None
    
    @staticmethod
    def get_message_status(message_id: int, user_id: int, db: Session) -> Dict[str, Any]:
        """
        Get status of a specific message and its AI response
        
        Args:
            message_id: The message ID
            user_id: The user ID
            db: Database session
            
        Returns:
            dict: Message status information
        """
        try:
            user_message = MessageService.get_message_by_id(message_id, user_id, db)
            if not user_message:
                return {
                    "success": False,
                    "message": "Message not found or access denied",
                    "error": "Invalid message"
                }
            
            ai_response = db.query(Message).filter(
                Message.parent_message_id == message_id,
                Message.message_type == MessageType.AI
            ).first()
            
            result = {
                "success": True,
                "user_message": {
                    "id": user_message.id,
                    "content": user_message.content,
                    "status": user_message.status.value,
                    "created_at": user_message.created_at.isoformat()
                }
            }
            
            if ai_response:
                result["ai_response"] = {
                    "id": ai_response.id,
                    "content": ai_response.content,
                    "status": ai_response.status.value,
                    "created_at": ai_response.created_at.isoformat()
                }
            else:
                result["ai_response"] = None
                result["ai_status"] = "processing" if user_message.status == MessageStatus.PROCESSING else "queued"
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting message status: {e}")
            return {
                "success": False,
                "message": "Failed to get message status",
                "error": str(e)
            }
    
    @staticmethod
    def get_user_usage_stats(user_id: int, db: Session, days: int = 30) -> Dict[str, Any]:
        """
        Get user's usage statistics
        
        Args:
            user_id: The user ID
            db: Database session
            days: Number of days to look back
            
        Returns:
            dict: Usage statistics
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {
                    "success": False,
                    "error": "User not found"
                }
            
            today_usage = MessageService.check_daily_usage(user_id, db)
            
            from datetime import timedelta
            start_date = date.today() - timedelta(days=days-1)
            
            usage_history = db.query(DailyUsage).filter(
                DailyUsage.user_id == user_id,
                DailyUsage.date >= start_date
            ).order_by(DailyUsage.date.desc()).all()
            
            total_messages = db.query(func.sum(Message.id)).filter(
                Message.user_id == user_id,
                Message.message_type == MessageType.USER
            ).scalar() or 0
            
            return {
                "success": True,
                "user_id": user_id,
                "subscription_tier": user.subscription_tier.value,
                "today_usage": today_usage,
                "usage_history": [
                    {
                        "date": usage.date.isoformat(),
                        "message_count": usage.message_count
                    }
                    for usage in usage_history
                ],
                "total_messages_sent": total_messages,
                "account_created": user.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            return {
                "success": False,
                "error": str(e)
            }
