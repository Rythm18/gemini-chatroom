from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, date
from app.models.chatroom import Chatroom
from app.models.message import Message
from app.models.user import User, SubscriptionTier
from app.schemas.chatroom import ChatroomCreate, ChatroomUpdate, ChatroomResponse
from app.core.redis_client import redis_client
from app.core.config import settings
import json
import logging

logger = logging.getLogger(__name__)

class ChatroomService:
    
    @staticmethod
    def create_cache_key(user_id: int, key_type: str, **kwargs) -> str:
        """Create a standardized cache key for chatrooms"""
        if key_type == "user_chatrooms":
            return f"chatrooms:user:{user_id}:list"
        elif key_type == "chatroom_detail":
            chatroom_id = kwargs.get('chatroom_id')
            return f"chatroom:{chatroom_id}:detail"
        elif key_type == "chatroom_messages":
            chatroom_id = kwargs.get('chatroom_id')
            page = kwargs.get('page', 1)
            return f"chatroom:{chatroom_id}:messages:page:{page}"
        return f"chatrooms:{user_id}:{key_type}"
    
    @staticmethod
    def invalidate_user_cache(user_id: int) -> None:
        """Invalidate all cache entries for a specific user"""
        try:
            cache_key = ChatroomService.create_cache_key(user_id, "user_chatrooms")
            redis_client.delete(cache_key)
            logger.info(f"Invalidated chatroom cache for user: {user_id}")
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
    
    @staticmethod
    def check_chatroom_limits(user_id: int, db: Session) -> Dict[str, Any]:
        """
        Check if user can create more chatrooms based on their subscription tier
        
        Args:
            user_id: The user ID
            db: Database session
            
        Returns:
            dict: Chatroom limit check result
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
                    "can_create_chatroom": True,
                    "current_chatrooms": 0,
                    "chatroom_limit": -1,
                    "remaining_chatrooms": -1,
                    "subscription_tier": user.subscription_tier.value
                }
            
            current_chatrooms = db.query(Chatroom).filter(
                Chatroom.owner_id == user_id
            ).count()
            
            chatroom_limit = 3
            remaining = max(0, chatroom_limit - current_chatrooms)
            can_create = current_chatrooms < chatroom_limit
            
            return {
                "success": True,
                "can_create_chatroom": can_create,
                "current_chatrooms": current_chatrooms,
                "chatroom_limit": chatroom_limit,
                "remaining_chatrooms": remaining,
                "subscription_tier": user.subscription_tier.value,
                "message": f"Basic tier users can create up to {chatroom_limit} chatrooms. You have {current_chatrooms}/{chatroom_limit} chatrooms. Upgrade to Pro for unlimited chatrooms." if not can_create else None
            }
            
        except Exception as e:
            logger.error(f"Error checking chatroom limits: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_user_chatrooms(
        user_id: int, 
        db: Session,
        page: int = 1,
        per_page: int = 10,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get user's chatrooms with caching
        
        Args:
            user_id: The user ID
            db: Database session
            page: Page number for pagination
            per_page: Items per page
            use_cache: Whether to use Redis cache
            
        Returns:
            dict: Chatrooms with pagination metadata
        """
        try:
            cache_key = ChatroomService.create_cache_key(user_id, "user_chatrooms")
            
            if use_cache and redis_client.is_connected():
                cached_data = redis_client.get_json(cache_key)
                if cached_data:
                    logger.info(f"Returning cached chatrooms for user: {user_id}")
                    return cached_data
            
            offset = (page - 1) * per_page
            
            chatrooms_query = db.query(
                Chatroom,
                func.count(Message.id).label('message_count'),
                func.max(Message.created_at).label('last_message_at')
            ).outerjoin(
                Message
            ).filter(
                Chatroom.owner_id == user_id
            ).group_by(
                Chatroom.id
            ).order_by(
                desc(func.coalesce(func.max(Message.created_at), Chatroom.created_at))
            )
            
            total_count = db.query(Chatroom).filter(Chatroom.owner_id == user_id).count()
            
            chatrooms_data = chatrooms_query.offset(offset).limit(per_page).all()
            
            chatrooms = []
            for chatroom, message_count, last_message_at in chatrooms_data:
                chatroom_dict = {
                    "id": chatroom.id,
                    "name": chatroom.name,
                    "description": chatroom.description,
                    "owner_id": chatroom.owner_id,
                    "created_at": chatroom.created_at.isoformat(),
                    "updated_at": chatroom.updated_at.isoformat(),
                    "message_count": message_count or 0,
                    "last_message_at": last_message_at.isoformat() if last_message_at else None
                }
                chatrooms.append(chatroom_dict)
            
            response_data = {
                "chatrooms": chatrooms,
                "total_count": total_count,
                "has_next": offset + per_page < total_count,
                "has_previous": page > 1,
                "page": page,
                "per_page": per_page
            }
            
            if use_cache and redis_client.is_connected():
                redis_client.set(
                    cache_key, 
                    response_data, 
                    expire_seconds=settings.CACHE_TTL_SECONDS
                )
                logger.info(f"Cached chatrooms for user: {user_id}")
            
            return response_data
            
        except Exception as e:
            logger.error(f"Error getting user chatrooms: {e}")
            return {
                "chatrooms": [],
                "total_count": 0,
                "has_next": False,
                "has_previous": False,
                "page": page,
                "per_page": per_page
            }
    
    @staticmethod
    def create_chatroom(user_id: int, chatroom_data: ChatroomCreate, db: Session) -> Dict[str, Any]:
        """
        Create a new chatroom
        
        Args:
            user_id: The owner user ID
            chatroom_data: Chatroom creation data
            db: Database session
            
        Returns:
            dict: Creation result with chatroom data
        """
        try:
            tier_check = ChatroomService.check_chatroom_limits(user_id, db)
            if not tier_check.get("can_create_chatroom"):
                return {
                    "success": False,
                    "message": tier_check.get("message"),
                    "error": "Chatroom limit exceeded",
                    "tier_info": tier_check
                }
            
            db_chatroom = Chatroom(
                name=chatroom_data.name,
                description=chatroom_data.description,
                owner_id=user_id
            )
            
            db.add(db_chatroom)
            db.commit()
            db.refresh(db_chatroom)
            
            ChatroomService.invalidate_user_cache(user_id)
            
            logger.info(f"Chatroom created: {chatroom_data.name} by user: {user_id}")
            
            return {
                "success": True,
                "message": "Chatroom created successfully",
                "chatroom": db_chatroom
            }
            
        except Exception as e:
            logger.error(f"Error creating chatroom: {e}")
            db.rollback()
            return {
                "success": False,
                "message": "Failed to create chatroom",
                "error": str(e)
            }
    
    @staticmethod
    def get_chatroom_by_id(chatroom_id: int, user_id: int, db: Session) -> Optional[Chatroom]:
        """
        Get chatroom by ID (only if user is the owner)
        
        Args:
            chatroom_id: The chatroom ID
            user_id: The user ID (must be owner)
            db: Database session
            
        Returns:
            Optional[Chatroom]: The chatroom if found and user is owner
        """
        return db.query(Chatroom).filter(
            Chatroom.id == chatroom_id,
            Chatroom.owner_id == user_id
        ).first()
    
    @staticmethod
    def get_chatroom_detail(
        chatroom_id: int, 
        user_id: int, 
        db: Session,
        include_messages: bool = True,
        message_limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get detailed chatroom information with recent messages
        
        Args:
            chatroom_id: The chatroom ID
            user_id: The user ID (must be owner)
            db: Database session
            include_messages: Whether to include recent messages
            message_limit: Number of recent messages to include
            
        Returns:
            dict: Chatroom detail result
        """
        try:
            chatroom = ChatroomService.get_chatroom_by_id(chatroom_id, user_id, db)
            if not chatroom:
                return {
                    "success": False,
                    "message": "Chatroom not found or access denied",
                    "error": "Chatroom not accessible"
                }
            
            message_count = db.query(Message).filter(Message.chatroom_id == chatroom_id).count()
            
            response_data = {
                "id": chatroom.id,
                "name": chatroom.name,
                "description": chatroom.description,
                "owner_id": chatroom.owner_id,
                "created_at": chatroom.created_at.isoformat(),
                "updated_at": chatroom.updated_at.isoformat(),
                "message_count": message_count,
                "recent_messages": []
            }
            
            if include_messages:
                recent_messages = db.query(Message).filter(
                    Message.chatroom_id == chatroom_id
                ).order_by(
                    desc(Message.created_at)
                ).limit(message_limit).all()
                
                response_data["recent_messages"] = [
                    {
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
                    for msg in reversed(recent_messages)
                ]
            
            return {
                "success": True,
                "message": "Chatroom retrieved successfully",
                "chatroom": response_data
            }
            
        except Exception as e:
            logger.error(f"Error getting chatroom detail: {e}")
            return {
                "success": False,
                "message": "Failed to retrieve chatroom",
                "error": str(e)
            }
    
    @staticmethod
    def update_chatroom(
        chatroom_id: int, 
        user_id: int, 
        update_data: ChatroomUpdate, 
        db: Session
    ) -> Dict[str, Any]:
        """
        Update a chatroom
        
        Args:
            chatroom_id: The chatroom ID
            user_id: The user ID (must be owner)
            update_data: Update data
            db: Database session
            
        Returns:
            dict: Update result
        """
        try:
            chatroom = ChatroomService.get_chatroom_by_id(chatroom_id, user_id, db)
            if not chatroom:
                return {
                    "success": False,
                    "message": "Chatroom not found or access denied",
                    "error": "Chatroom not accessible"
                }
            
            if update_data.name is not None:
                chatroom.name = update_data.name
            if update_data.description is not None:
                chatroom.description = update_data.description
            
            db.commit()
            db.refresh(chatroom)
            
            ChatroomService.invalidate_user_cache(user_id)
            
            logger.info(f"Chatroom updated: {chatroom_id} by user: {user_id}")
            
            return {
                "success": True,
                "message": "Chatroom updated successfully",
                "chatroom": chatroom
            }
            
        except Exception as e:
            logger.error(f"Error updating chatroom: {e}")
            db.rollback()
            return {
                "success": False,
                "message": "Failed to update chatroom",
                "error": str(e)
            }
    
    @staticmethod
    def delete_chatroom(chatroom_id: int, user_id: int, db: Session) -> Dict[str, Any]:
        """
        Delete a chatroom and all its messages
        
        Args:
            chatroom_id: The chatroom ID
            user_id: The user ID (must be owner)
            db: Database session
            
        Returns:
            dict: Deletion result
        """
        try:
            chatroom = ChatroomService.get_chatroom_by_id(chatroom_id, user_id, db)
            if not chatroom:
                return {
                    "success": False,
                    "message": "Chatroom not found or access denied",
                    "error": "Chatroom not accessible"
                }
            
            db.delete(chatroom)
            db.commit()

            ChatroomService.invalidate_user_cache(user_id)
            
            logger.info(f"Chatroom deleted: {chatroom_id} by user: {user_id}")
            
            return {
                "success": True,
                "message": "Chatroom deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Error deleting chatroom: {e}")
            db.rollback()
            return {
                "success": False,
                "message": "Failed to delete chatroom",
                "error": str(e)
            } 