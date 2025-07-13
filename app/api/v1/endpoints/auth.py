from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.deps import get_db, get_current_active_user
from app.schemas.user import (
    UserCreate, OTPRequest, OTPResponse, OTPVerification, 
    LoginResponse, UserResponse, PasswordReset, SuccessResponse
)
from app.services.user_service import UserService
from app.services.otp_service import OTPService
from app.models.otp import OTPType
from app.models.user import User
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/signup", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    user_create: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user with mobile number
    
    - **mobile_number**: User's mobile number (required)
    """
    logger.info(f"Signup attempt for mobile: {user_create.mobile_number}")
    
    try:
        result = UserService.create_user(user_create, db)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return SuccessResponse(
            success=True,
            message="User registered successfully. Please verify your mobile number with OTP.",
            data={
                "mobile_number": user_create.mobile_number,
                "next_step": "Send OTP to verify your mobile number"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/send-otp", response_model=OTPResponse)
async def send_otp(
    otp_request: OTPRequest,
    db: Session = Depends(get_db)
):
    """
    Send OTP to mobile number for login
    
    - **mobile_number**: Mobile number to send OTP to
    """
    logger.info(f"OTP request for mobile: {otp_request.mobile_number}")
    
    try:
        user = UserService.get_user_by_mobile(otp_request.mobile_number, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found. Please register first."
            )
        
        result = OTPService.send_otp(otp_request.mobile_number, OTPType.LOGIN, db)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"]
            )
        
        return OTPResponse(
            success=True,
            message="OTP sent successfully",
            otp_code=result["otp_code"] if settings.DEBUG else None,
            expires_in_minutes=result["expires_in_minutes"],
            mobile_number=otp_request.mobile_number
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Send OTP error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP"
        )

@router.post("/verify-otp", response_model=LoginResponse)
async def verify_otp(
    otp_verification: OTPVerification,
    db: Session = Depends(get_db)
):
    """
    Verify OTP and return JWT token
    
    - **mobile_number**: Mobile number
    - **otp_code**: 6-digit OTP code
    """
    logger.info(f"OTP verification for mobile: {otp_verification.mobile_number}")
    
    try:
        otp_result = OTPService.verify_otp(
            otp_verification.mobile_number,
            otp_verification.otp_code,
            OTPType.LOGIN,
            db
        )
        
        if not otp_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=otp_result["message"]
            )
        
        auth_result = UserService.authenticate_user(otp_verification.mobile_number, db)
        
        if not auth_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=auth_result["message"]
            )
        
        user_response = UserResponse.from_orm(auth_result["user"])
        
        return LoginResponse(
            success=True,
            message="Login successful",
            access_token=auth_result["access_token"],
            token_type="bearer",
            expires_in_hours=settings.JWT_EXPIRATION_HOURS,
            user=user_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Verify OTP error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OTP verification failed"
        )

@router.post("/forgot-password", response_model=OTPResponse)
async def forgot_password(
    otp_request: OTPRequest,
    db: Session = Depends(get_db)
):
    """
    Send OTP for password reset
    
    - **mobile_number**: Mobile number for password reset
    """
    logger.info(f"Password reset OTP request for mobile: {otp_request.mobile_number}")
    
    try:
        user = UserService.get_user_by_mobile(otp_request.mobile_number, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        result = OTPService.send_otp(otp_request.mobile_number, OTPType.FORGOT_PASSWORD, db)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"]
            )
        
        return OTPResponse(
            success=True,
            message="Password reset OTP sent successfully",
            otp_code=result["otp_code"] if settings.DEBUG else None,
            expires_in_minutes=result["expires_in_minutes"],
            mobile_number=otp_request.mobile_number
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Forgot password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send password reset OTP"
        )

@router.post("/change-password", response_model=SuccessResponse)
async def change_password(
    password_reset: PasswordReset,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change user password using OTP verification (requires authentication)
    
    - **mobile_number**: User's mobile number
    - **otp_code**: OTP code from forgot password
    """
    logger.info(f"Password reset request for authenticated user: {current_user.mobile_number}")
    
    try:
        # Verify that the mobile number matches the authenticated user
        if password_reset.mobile_number != current_user.mobile_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mobile number does not match authenticated user"
            )
        
        otp_result = OTPService.verify_otp(
            password_reset.mobile_number,
            password_reset.otp_code,
            OTPType.FORGOT_PASSWORD,
            db
        )
        
        if not otp_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=otp_result["message"]
            )
        
        logger.info(f"Password reset successful for authenticated user: {current_user.mobile_number}")
        
        return SuccessResponse(
            success=True,
            message="Password changed successfully",
            data={
                "mobile_number": current_user.mobile_number,
                "message": "Password has been changed successfully"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        ) 