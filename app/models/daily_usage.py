from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from datetime import datetime, date
from app.core.database import Base

class DailyUsage(Base):
    __tablename__ = "daily_usages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, default=date.today)
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="daily_usages")
    
    def __repr__(self):
        return f"<DailyUsage(user_id={self.user_id}, date={self.date}, count={self.message_count})>" 