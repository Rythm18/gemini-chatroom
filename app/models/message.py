from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from app.core.database import Base

class MessageType(Enum):
    USER = "user"
    AI = "ai"

class MessageStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    message_type = Column(SQLEnum(MessageType), nullable=False)
    status = Column(SQLEnum(MessageStatus), default=MessageStatus.PENDING)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    chatroom_id = Column(Integer, ForeignKey("chatrooms.id"), nullable=False)
    parent_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)  
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="messages")
    chatroom = relationship("Chatroom", back_populates="messages")
    parent_message = relationship("Message", remote_side=[id]) 