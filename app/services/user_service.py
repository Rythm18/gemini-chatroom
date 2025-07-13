from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from app.models.user import User, SubscriptionTier
from app.schemas.user import UserCreate
from app.core.auth import AuthUtils
import logging

logger = logging.getLogger(__name__)

class UserService:
    
    @staticmethod
    def get_user_by_id(user_id: int, db: Session) -> Optional[User]:
        """
        Get user by ID
        
        Args:
            user_id: The user ID
            db: Database session
            
        Returns:
            Optional[User]: The user if found, None otherwise
        """
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_mobile(mobile_number: str, db: Session) -> Optional[User]:
        """
        Get user by mobile number
        
        Args:
            mobile_number: The mobile number
            db: Database session
            
        Returns:
            Optional[User]: The user if found, None otherwise
        """
        return db.query(User).filter(User.mobile_number == mobile_number).first()
    
    @staticmethod
    def create_user(user_create: UserCreate, db: Session) -> Dict[str, Any]:
        """
        Create a new user
        
        Args:
            user_create: User creation data
            db: Database session
            
        Returns:
            dict: Result with user data or error
        """
        try:
            existing_user = UserService.get_user_by_mobile(user_create.mobile_number, db)
            if existing_user:
                return {
                    "success": False,
                    "message": "User already exists with this mobile number",
                    "error": "User already exists"
                }
            
            db_user = User(
                mobile_number=user_create.mobile_number,
                is_active=True,
                subscription_tier=SubscriptionTier.BASIC
            )
            
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            
            logger.info(f"User created successfully: {user_create.mobile_number}")
            
            return {
                "success": True,
                "message": "User created successfully",
                "user": db_user
            }
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            db.rollback()
            return {
                "success": False,
                "message": "Failed to create user",
                "error": str(e)
            }
    
    @staticmethod
    def authenticate_user(mobile_number: str, db: Session) -> Dict[str, Any]:
        """
        Authenticate user and generate JWT token
        
        Args:
            mobile_number: The mobile number
            db: Database session
            
        Returns:
            dict: Authentication result with token
        """
        try:
            user = UserService.get_user_by_mobile(mobile_number, db)
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "error": "User does not exist"
                }
            
            if not user.is_active:
                return {
                    "success": False,
                    "message": "User account is inactive",
                    "error": "Account inactive"
                }
                
            access_token = AuthUtils.create_user_token(user.id, user.mobile_number)
            
            logger.info(f"User authenticated successfully: {mobile_number}")
            
            return {
                "success": True,
                "message": "Authentication successful",
                "access_token": access_token,
                "user": user
            }
            
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return {
                "success": False,
                "message": "Authentication failed",
                "error": str(e)
            }
    
    @staticmethod
    def update_user_subscription(user_id: int, subscription_tier: SubscriptionTier, db: Session) -> Dict[str, Any]:
        """
        Update user subscription tier
        
        Args:
            user_id: The user ID
            subscription_tier: New subscription tier
            db: Database session
            
        Returns:
            dict: Update result
        """
        try:
            user = UserService.get_user_by_id(user_id, db)
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "error": "User does not exist"
                }
            
            user.subscription_tier = subscription_tier
            db.commit()
            db.refresh(user)
            
            logger.info(f"User subscription updated: {user.mobile_number} -> {subscription_tier.value}")
            
            return {
                "success": True,
                "message": "Subscription updated successfully",
                "user": user
            }
            
        except Exception as e:
            logger.error(f"Error updating subscription: {e}")
            db.rollback()
            return {
                "success": False,
                "message": "Failed to update subscription",
                "error": str(e)
            }
    
    @staticmethod
    def deactivate_user(user_id: int, db: Session) -> Dict[str, Any]:
        """
        Deactivate a user account
        
        Args:
            user_id: The user ID
            db: Database session
            
        Returns:
            dict: Deactivation result
        """
        try:
            user = UserService.get_user_by_id(user_id, db)
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "error": "User does not exist"
                }
            
            user.is_active = False
            db.commit()
            db.refresh(user)
            
            logger.info(f"User deactivated: {user.mobile_number}")
            
            return {
                "success": True,
                "message": "User deactivated successfully",
                "user": user
            }
            
        except Exception as e:
            logger.error(f"Error deactivating user: {e}")
            db.rollback()
            return {
                "success": False,
                "message": "Failed to deactivate user",
                "error": str(e)
            } 