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
from app.models.message import Message

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
    Send a message to a chatroom and get task ID for background AI response
    
    **Rate Limiting:**
    - **Basic tier**: 5 messages per day
    - **Pro tier**: Unlimited messages
    
    **Returns:** Task ID to track AI response progress
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
        
        from app.tasks.message_tasks import process_ai_message
        task = process_ai_message.delay(
            message_id=user_message.id,
            user_message=message_data.content,
            chatroom_id=chatroom_id,
            user_id=current_user.id
        )
        
        user_message_response = MessageResponse.from_orm(user_message)
        
        return SuccessResponse(
            success=True,
            message="Message sent successfully. AI response is being generated in background.",
            data={
                "user_message": user_message_response.dict(),
                "task_id": task.id,
                "task_status": "processing",
                "check_status_url": f"/api/v1/chatroom/task/{task.id}/status"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Send message error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )

@router.get("/task/{task_id}/status", response_model=SuccessResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get the status of a background AI response task
    
    **Returns:** Task status and result if completed
    """
    
    try:
        from app.core.redis_client import redis_client
        import json
        
        task_data_str = redis_client.get(f"task:{task_id}:status")
        if not task_data_str:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found or expired"
            )
        
        try:
            task_data = json.loads(task_data_str)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid task data format"
            )
        
        task_user_id = task_data.get("user_id")
        if not task_user_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Task data is incomplete"
            )
            
        if task_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this task"
            )
        
        response_data = {
            "task_id": task_id,
            "status": task_data.get("status", "unknown"),
        }
        
        if task_data.get("status") == "completed":
            ai_message = db.query(Message).filter(
                Message.id == task_data.get("ai_message_id")
            ).first()
            
            if ai_message:
                ai_message_response = MessageResponse.from_orm(ai_message)
                response_data.update({
                    "ai_response": ai_message_response.dict(),
                    "processing_time": task_data.get("processing_time"),
                    "model": task_data.get("model")
                })
        
        elif task_data.get("status") == "failed":
            response_data["error"] = task_data.get("error", "Unknown error")
        
        elif task_data.get("status") == "processing":
            response_data["message"] = "AI response is still being generated"
        
        return SuccessResponse(
            success=True,
            message=f"Task status: {task_data.get('status', 'unknown')}",
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get task status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get task status"
        ) 