from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from app.core.database import Base

class SubscriptionTier(Enum):
    BASIC = "basic"
    PRO = "pro"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    mobile_number = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    subscription_tier = Column(SQLEnum(SubscriptionTier), default=SubscriptionTier.BASIC)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    chatrooms = relationship("Chatroom", back_populates="owner")
    messages = relationship("Message", back_populates="user")
    daily_usages = relationship("DailyUsage", back_populates="user")
