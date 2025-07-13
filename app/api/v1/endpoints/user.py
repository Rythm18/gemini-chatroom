from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.deps import get_db, get_current_active_user
from app.schemas.user import UserResponse
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user information
    
    Returns detailed information about the currently authenticated user:
    - User ID
    - Mobile number
    - Account status
    - Subscription tier
    - Account creation and update timestamps
    """
    logger.info(f"User info request for: {current_user.mobile_number}")
    
    try:
        user_response = UserResponse.from_orm(current_user)
        
        return user_response
        
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user information"
        ) 