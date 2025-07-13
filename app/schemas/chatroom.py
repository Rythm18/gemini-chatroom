from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

class ChatroomCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Chatroom name")
    description: Optional[str] = Field(None, max_length=500, description="Optional chatroom description")
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Chatroom name cannot be empty')
        return v.strip()
    
    @validator('description')
    def validate_description(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
        return v

class ChatroomUpdate(BaseModel):
    """Schema for updating a chatroom"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Updated chatroom name")
    description: Optional[str] = Field(None, max_length=500, description="Updated chatroom description")
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Chatroom name cannot be empty')
        return v.strip() if v else v
    
    @validator('description')
    def validate_description(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
        return v

class ChatroomResponse(BaseModel):
    """Schema for chatroom response"""
    id: int
    name: str
    description: Optional[str]
    owner_id: int
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = 0
    last_message_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class ChatroomListResponse(BaseModel):
    """Schema for chatroom list response with metadata"""
    chatrooms: List[ChatroomResponse]
    total_count: int
    has_next: bool = False
    has_previous: bool = False
    page: int = 1
    per_page: int = 10

class ChatroomDetailResponse(BaseModel):
    """Schema for detailed chatroom response with recent messages"""
    id: int
    name: str
    description: Optional[str]
    owner_id: int
    created_at: datetime
    updated_at: datetime
    message_count: int
    recent_messages: List['MessageResponse'] = []
    
    class Config:
        from_attributes = True

class MessageType(str, Enum):
    """Message type enumeration"""
    USER = "user"
    AI = "ai"

class MessageStatus(str, Enum):
    """Message status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"

class MessageCreate(BaseModel):
    """Schema for creating a new message"""
    content: str = Field(..., min_length=1, max_length=4000, description="Message content")
    
    @validator('content')
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError('Message content cannot be empty')
        return v.strip()

class MessageResponse(BaseModel):
    """Schema for message response"""
    id: int
    content: str
    message_type: MessageType
    status: MessageStatus
    user_id: int
    chatroom_id: int
    parent_message_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class MessageListResponse(BaseModel):
    """Schema for message list response with pagination"""
    messages: List[MessageResponse]
    total_count: int
    has_next: bool = False
    has_previous: bool = False
    page: int = 1
    per_page: int = 50

class AIMessageRequest(BaseModel):
    """Schema for AI message processing request"""
    message_id: int
    user_message: str
    chatroom_id: int
    user_id: int

class AIMessageResponse(BaseModel):
    """Schema for AI message response"""
    success: bool
    message: str
    ai_message_id: Optional[int] = None
    processing_time: Optional[float] = None
    error: Optional[str] = None

class UsageResponse(BaseModel):
    """Schema for usage response"""
    daily_usage: int
    daily_limit: int
    remaining_today: int
    subscription_tier: str
    can_send_message: bool

ChatroomDetailResponse.model_rebuild() 