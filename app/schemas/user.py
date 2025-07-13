from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from enum import Enum

class SubscriptionTierEnum(str, Enum):
    """Subscription tier enumeration"""
    BASIC = "basic"
    PRO = "pro"

class UserCreate(BaseModel):
    """Schema for user registration"""
    mobile_number: str = Field(..., description="Mobile number for registration")
    
    @validator('mobile_number')
    def validate_mobile_number(cls, v):
        if not v:
            raise ValueError('Mobile number is required')
        
        v = v.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        if not v.isdigit() or len(v) < 10 or len(v) > 15:
            raise ValueError('Invalid mobile number format')
        
        return v

class UserResponse(BaseModel):
    """Schema for user response"""
    id: int
    mobile_number: str
    is_active: bool
    subscription_tier: SubscriptionTierEnum
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class OTPRequest(BaseModel):
    """Schema for OTP request"""
    mobile_number: str = Field(..., description="Mobile number to send OTP to")
    
    @validator('mobile_number')
    def validate_mobile_number(cls, v):
        if not v:
            raise ValueError('Mobile number is required')
        
        v = v.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        if not v.isdigit() or len(v) < 10 or len(v) > 15:
            raise ValueError('Invalid mobile number format')
        
        return v

class OTPResponse(BaseModel):
    """Schema for OTP response"""
    success: bool
    message: str
    otp_code: Optional[str] = None
    expires_in_minutes: Optional[int] = None
    mobile_number: str

class OTPVerification(BaseModel):
    """Schema for OTP verification"""
    mobile_number: str = Field(..., description="Mobile number")
    otp_code: str = Field(..., description="OTP code to verify")
    
    @validator('mobile_number')
    def validate_mobile_number(cls, v):
        if not v:
            raise ValueError('Mobile number is required')
        
        v = v.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        if not v.isdigit() or len(v) < 10 or len(v) > 15:
            raise ValueError('Invalid mobile number format')
        
        return v
    
    @validator('otp_code')
    def validate_otp_code(cls, v):
        if not v:
            raise ValueError('OTP code is required')
        
        if not v.isdigit() or len(v) != 6:
            raise ValueError('OTP code must be 6 digits')
        
        return v

class LoginResponse(BaseModel):
    """Schema for login response"""
    success: bool
    message: str
    access_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in_hours: Optional[int] = None
    user: Optional[UserResponse] = None

class PasswordReset(BaseModel):
    """Schema for password reset with OTP verification"""
    mobile_number: str = Field(..., description="Mobile number")
    otp_code: str = Field(..., description="OTP code from forgot password")
    
    @validator('mobile_number')
    def validate_mobile_number(cls, v):
        if not v:
            raise ValueError('Mobile number is required')
        
        v = v.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        if not v.isdigit() or len(v) < 10 or len(v) > 15:
            raise ValueError('Invalid mobile number format')
        
        return v
    
    @validator('otp_code')
    def validate_otp_code(cls, v):
        if not v:
            raise ValueError('OTP code is required')
        
        if not v.isdigit() or len(v) != 6:
            raise ValueError('OTP code must be 6 digits')
        
        return v

class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = True
    message: str
    data: Optional[dict] = None

class ErrorResponse(BaseModel):
    """Generic error response"""
    success: bool = False
    message: str
    error: Optional[str] = None
    errors: Optional[list] = None 