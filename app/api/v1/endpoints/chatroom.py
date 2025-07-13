from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.deps import get_db, get_current_active_user
from app.schemas.chatroom import (
    ChatroomCreate, ChatroomResponse, ChatroomListResponse, 
    ChatroomDetailResponse, MessageCreate, MessageResponse,
    AIMessageResponse, UsageResponse
)
from app.schemas.user import SuccessResponse
from app.services.chatroom_service import ChatroomService
from app.services.message_service import MessageService
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_chatroom(
    chatroom_data: ChatroomCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new chatroom
    
    - **name**: Chatroom name (required, 1-100 characters)
    - **description**: Optional description (max 500 characters)
    """
    logger.info(f"Creating chatroom '{chatroom_data.name}' for user: {current_user.mobile_number}")
    
    try:
        result = ChatroomService.create_chatroom(current_user.id, chatroom_data, db)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        chatroom_response = ChatroomResponse.from_orm(result["chatroom"])
        
        return SuccessResponse(
            success=True,
            message="Chatroom created successfully",
            data={
                "chatroom": chatroom_response.dict(),
                "next_steps": "You can now send messages to start a conversation with AI"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create chatroom error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chatroom"
        )

@router.get("", response_model=ChatroomListResponse)
async def list_chatrooms(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=50, description="Items per page"),
    use_cache: bool = Query(True, description="Use Redis cache for faster response"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get user's chatrooms with pagination and caching
    
    **Query Parameters:**
    - **page**: Page number (default: 1)
    - **per_page**: Items per page (max: 50, default: 10)
    - **use_cache**: Enable/disable caching (default: true)
    """
    try:
        result = ChatroomService.get_user_chatrooms(
            user_id=current_user.id,
            db=db,
            page=page,
            per_page=per_page,
            use_cache=use_cache
        )
        
        return ChatroomListResponse(**result)
        
    except Exception as e:
        logger.error(f"List chatrooms error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chatrooms"
        )

@router.get("/{chatroom_id}", response_model=SuccessResponse)
async def get_chatroom_detail(
    chatroom_id: int,
    include_messages: bool = Query(True, description="Include recent messages"),
    message_limit: int = Query(20, ge=1, le=100, description="Number of recent messages to include"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed chatroom information with recent messages
    
    **Query Parameters:**
    - **include_messages**: Include recent messages (default: true)
    - **message_limit**: Number of recent messages (max: 100, default: 20)
    """
    
    try:
        result = ChatroomService.get_chatroom_detail(
            chatroom_id=chatroom_id,
            user_id=current_user.id,
            db=db,
            include_messages=include_messages,
            message_limit=message_limit
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["message"]
            )
        
        return SuccessResponse(
            success=True,
            message="Chatroom retrieved successfully",
            data=result["chatroom"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get chatroom detail error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chatroom details"
        )

@router.post("/{chatroom_id}/message", response_model=SuccessResponse)
async def send_message(
    chatroom_id: int,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Send a message to a chatroom and get AI response immediately
    
    **Rate Limiting:**
    - **Basic tier**: 5 messages per day
    - **Pro tier**: Unlimited messages
    """
    
    try:
        result = MessageService.create_user_message(
            user_id=current_user.id,
            chatroom_id=chatroom_id,
            message_data=message_data,
            db=db
        )
        
        if not result["success"]:
            if "Rate limit exceeded" in result.get("error", ""):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=result["message"]
                )
            elif "Invalid chatroom" in result.get("error", ""):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result["message"]
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result["message"]
                )
        
        user_message = result["user_message"]
        
        ai_response_result = await MessageService.generate_ai_response_sync(
            user_message_id=user_message.id,
            user_message_content=message_data.content,
            chatroom_id=chatroom_id,
            user_id=current_user.id,
            db=db
        )
        
        user_message_response = MessageResponse.from_orm(user_message)
        
        response_data = {
            "user_message": user_message_response.dict(),
        }
        
        if ai_response_result["success"]:
            ai_message_response = MessageResponse.from_orm(ai_response_result["ai_message"])
            response_data["ai_response"] = ai_message_response.dict()
            return SuccessResponse(
                success=True,
                message="Message sent and AI response generated successfully",
                data=response_data
            )
        else:
            response_data["ai_response"] = {
                "error": "AI response generation failed",
                "fallback_message": "I apologize, but I'm unable to respond at the moment. Please try again."
            }
            return SuccessResponse(
                success=True,
                message="Message sent successfully, but AI response failed",
                data=response_data
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Send message error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        ) 