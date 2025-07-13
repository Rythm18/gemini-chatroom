from celery import current_task
from sqlalchemy.orm import Session
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.message import Message, MessageType, MessageStatus
from app.models.user import User
from app.services.gemini_service import gemini_service
from app.services.otp_service import OTPService
from app.core.redis_client import redis_client
from typing import Dict, Any, List
import logging
import asyncio
import time

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_ai_message(self, message_id: int, user_message: str, chatroom_id: int, user_id: int) -> Dict[str, Any]:
    """
    Process AI message generation asynchronously
    
    Args:
        message_id: The user message ID that triggered this task
        user_message: The user's message content
        chatroom_id: The chatroom ID
        user_id: The user ID
        
    Returns:
        dict: Task result with AI response details
    """
    db = SessionLocal()
    
    try:
        
        user_msg = db.query(Message).filter(Message.id == message_id).first()
        if not user_msg:
            raise ValueError(f"Message {message_id} not found")
        
        user_msg.status = MessageStatus.PROCESSING
        db.commit()
        
        conversation_history = _get_conversation_history(chatroom_id, db)
        
        ai_response_result = asyncio.run(
            gemini_service.generate_response(
                user_message=user_message,
                conversation_history=conversation_history
            )
        )
        
        if not ai_response_result.get("success"):
            ai_content = ai_response_result.get("fallback_response", "I apologize, but I'm unable to respond at the moment. Please try again.")
            logger.warning(f"AI generation failed for message {message_id}, using fallback")
        else:
            ai_content = ai_response_result.get("content", "")
        
        ai_message = Message(
            content=ai_content,
            message_type=MessageType.AI,
            status=MessageStatus.COMPLETED,
            user_id=user_id,
            chatroom_id=chatroom_id,
            parent_message_id=message_id
        )
        
        db.add(ai_message)
        
        user_msg.status = MessageStatus.COMPLETED
        
        db.commit()
        db.refresh(ai_message)
        
        logger.info(f"AI response generated successfully for message_id: {message_id}")
        
        return {
            "success": True,
            "message_id": message_id,
            "ai_message_id": ai_message.id,
            "processing_time": ai_response_result.get("processing_time", 0),
            "model": ai_response_result.get("model", "unknown"),
            "ai_content": ai_content[:100] + "..." if len(ai_content) > 100 else ai_content
        }
        
    except Exception as e:
        logger.error(f"Error processing AI message {message_id}: {e}")
        
        try:
            if 'user_msg' in locals() and user_msg:
                user_msg.status = MessageStatus.FAILED
                db.commit()
            
            error_message = Message(
                content="I apologize, but I encountered an error while processing your message. Please try again.",
                message_type=MessageType.AI,
                status=MessageStatus.COMPLETED,
                user_id=user_id,
                chatroom_id=chatroom_id,
                parent_message_id=message_id
            )
            db.add(error_message)
            db.commit()
            
        except Exception as commit_error:
            logger.error(f"Error updating message status: {commit_error}")
            db.rollback()
        
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying AI message processing for message_id: {message_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=e)
        
        return {
            "success": False,
            "message_id": message_id,
            "error": str(e),
            "max_retries_exceeded": True
        }
        
    finally:
        db.close()

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

@celery_app.task
def cleanup_expired_otps() -> Dict[str, Any]:
    """
    Periodic task to clean up expired OTPs
    
    Returns:
        dict: Cleanup result
    """
    db = SessionLocal()
    
    try:
        logger.info("Starting expired OTP cleanup")
        
        cleaned_count = OTPService.cleanup_expired_otps(db)
        
        logger.info(f"Cleaned up {cleaned_count} expired OTPs")
        
        return {
            "success": True,
            "cleaned_count": cleaned_count,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Error during OTP cleanup: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": time.time()
        }
        
    finally:
        db.close()

@celery_app.task
def cleanup_old_cache() -> Dict[str, Any]:
    """
    Periodic task to clean up old cache entries
    
    Returns:
        dict: Cleanup result
    """
    try:
        logger.info("Starting cache cleanup")
        
        if not redis_client.is_connected():
            return {
                "success": False,
                "error": "Redis not connected",
                "timestamp": time.time()
            }
        
        logger.info("Cache cleanup completed")
        
        return {
            "success": True,
            "message": "Cache cleanup completed",
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Error during cache cleanup: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": time.time()
        }