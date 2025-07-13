from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum as SQLEnum
from datetime import datetime, timedelta
from enum import Enum
from app.core.database import Base

class OTPType(Enum):
    LOGIN = "login"
    FORGOT_PASSWORD = "forgot_password"

class OTP(Base):
    __tablename__ = "otps"

    id = Column(Integer, primary_key=True, index=True)
    mobile_number = Column(String, nullable=False, index=True)
    otp_code = Column(String, nullable=False)
    otp_type = Column(SQLEnum(OTPType), nullable=False)
    is_verified = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def is_expired(self):
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self):
        return not self.is_verified and not self.is_expired() 