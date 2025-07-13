from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import SessionLocal
from app.core.auth import AuthUtils
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()

def get_db():
    """
    Database dependency to get database session
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Authentication dependency to get current user from JWT token
    
    Args:
        credentials: JWT token credentials
        db: Database session
        
    Returns:
        User: The authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        token = credentials.credentials
        
        payload = AuthUtils.verify_access_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to get current active user
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: The active user
        
    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is inactive"
        )
    return current_user

def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optional authentication dependency - returns None if no valid token
    
    Args:
        credentials: Optional JWT token credentials
        db: Database session
        
    Returns:
        Optional[User]: The authenticated user or None
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = AuthUtils.verify_access_token(token)
        if not payload:
            return None
        
        user_id = payload.get("user_id")
        if not user_id:
            return None
        
        user = db.query(User).filter(
            User.id == user_id,
            User.is_active == True
        ).first()
        
        return user
        
    except Exception as e:
        logger.error(f"Optional authentication error: {e}")
        return None
