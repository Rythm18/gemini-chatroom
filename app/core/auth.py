from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthUtils:
    """Utility class for authentication operations"""
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token
        
        Args:
            data: The payload data to encode in the token
            expires_delta: Optional expiration time delta
            
        Returns:
            str: The encoded JWT token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
        
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.JWT_SECRET, 
            algorithm=settings.JWT_ALGORITHM
        )
        
        return encoded_jwt
    
    @staticmethod
    def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT access token
        
        Args:
            token: The JWT token to verify
            
        Returns:
            dict: The decoded token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token, 
                settings.JWT_SECRET, 
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt
        
        Args:
            password: The plain text password
            
        Returns:
            str: The hashed password
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash
        
        Args:
            plain_password: The plain text password
            hashed_password: The hashed password
            
        Returns:
            bool: True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def create_user_token(user_id: int, mobile_number: str) -> str:
        """
        Create a JWT token for a user
        
        Args:
            user_id: The user's ID
            mobile_number: The user's mobile number
            
        Returns:
            str: The JWT token
        """
        token_data = {
            "user_id": user_id,
            "mobile_number": mobile_number,
            "type": "access"
        }
        return AuthUtils.create_access_token(token_data) 