import random
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.otp import OTP, OTPType
from app.core.redis_client import redis_client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class OTPService:
    
    @staticmethod
    def generate_otp(length: int = 6) -> str:
        """
        Generate a random OTP
        
        Args:
            length: Length of the OTP (default: 6)
            
        Returns:
            str: The generated OTP
        """
        return ''.join(random.choices(string.digits, k=length))
    
    @staticmethod
    def create_otp_key(mobile_number: str, otp_type: OTPType) -> str:
        """
        Create a Redis key for OTP storage
        
        Args:
            mobile_number: The mobile number
            otp_type: The type of OTP
            
        Returns:
            str: The Redis key
        """
        return f"otp:{mobile_number}:{otp_type.value}"
    
    @staticmethod
    def send_otp(mobile_number: str, otp_type: OTPType, db: Session) -> Dict[str, Any]:
        """
        Generate and send OTP to mobile number
        
        Args:
            mobile_number: The mobile number to send OTP to
            otp_type: The type of OTP (login, forgot_password)
            db: Database session
            
        Returns:
            dict: Response with OTP details and success status
        """
        try:
            otp_code = OTPService.generate_otp()
            
            expires_at = datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRATION_MINUTES)
            
            db_otp = OTP(
                mobile_number=mobile_number,
                otp_code=otp_code,
                otp_type=otp_type,
                expires_at=expires_at
            )
            db.add(db_otp)
            db.commit()
            db.refresh(db_otp)
            
            otp_data = {
                "otp_code": otp_code,
                "mobile_number": mobile_number,
                "otp_type": otp_type.value,
                "expires_at": expires_at.isoformat(),
                "created_at": datetime.utcnow().isoformat()
            }
            
            redis_key = OTPService.create_otp_key(mobile_number, otp_type)
            redis_client.set(
                redis_key, 
                otp_data, 
                expire_seconds=settings.OTP_EXPIRATION_MINUTES * 60
            )
            
            logger.info(f"OTP generated for {mobile_number}, type: {otp_type.value}")
            
            return {
                "success": True,
                "message": "OTP sent successfully",
                "otp_code": otp_code,
                "expires_in_minutes": settings.OTP_EXPIRATION_MINUTES,
                "mobile_number": mobile_number
            }
            
        except Exception as e:
            logger.error(f"Error generating OTP: {e}")
            db.rollback()
            return {
                "success": False,
                "message": "Failed to generate OTP",
                "error": str(e)
            }
    
    @staticmethod
    def verify_otp(mobile_number: str, otp_code: str, otp_type: OTPType, db: Session) -> Dict[str, Any]:
        """
        Verify OTP code
        
        Args:
            mobile_number: The mobile number
            otp_code: The OTP code to verify
            otp_type: The type of OTP
            db: Database session
            
        Returns:
            dict: Verification result
        """
        try:
            redis_key = OTPService.create_otp_key(mobile_number, otp_type)
            cached_otp = redis_client.get_json(redis_key)
            
            if cached_otp:
                if cached_otp["otp_code"] == otp_code:
                    db_otp = db.query(OTP).filter(
                        OTP.mobile_number == mobile_number,
                        OTP.otp_code == otp_code,
                        OTP.otp_type == otp_type,
                        OTP.is_verified == False
                    ).first()
                    
                    if db_otp and db_otp.is_valid():
                        db_otp.is_verified = True
                        db.commit()
                        
                        redis_client.delete(redis_key)
                        
                        logger.info(f"OTP verified successfully for {mobile_number}")
                        
                        return {
                            "success": True,
                            "message": "OTP verified successfully",
                            "mobile_number": mobile_number
                        }
            
            db_otp = db.query(OTP).filter(
                OTP.mobile_number == mobile_number,
                OTP.otp_code == otp_code,
                OTP.otp_type == otp_type,
                OTP.is_verified == False
            ).first()
            
            if not db_otp:
                return {
                    "success": False,
                    "message": "Invalid OTP code",
                    "error": "OTP not found or already used"
                }
            
            if not db_otp.is_valid():
                return {
                    "success": False,
                    "message": "OTP has expired",
                    "error": "Please request a new OTP"
                }

            db_otp.is_verified = True
            db.commit()
            
            redis_client.delete(redis_key)
            
            logger.info(f"OTP verified successfully for {mobile_number}")
            
            return {
                "success": True,
                "message": "OTP verified successfully",
                "mobile_number": mobile_number
            }
            
        except Exception as e:
            logger.error(f"Error verifying OTP: {e}")
            return {
                "success": False,
                "message": "Failed to verify OTP",
                "error": str(e)
            }
    
    @staticmethod
    def cleanup_expired_otps(db: Session) -> int:
        """
        Clean up expired OTPs from database
        
        Args:
            db: Database session
            
        Returns:
            int: Number of cleaned up OTPs
        """
        try:
            expired_otps = db.query(OTP).filter(
                OTP.expires_at < datetime.utcnow()
            ).all()
            
            count = len(expired_otps)
            
            for otp in expired_otps:
                db.delete(otp)
            
            db.commit()
            
            logger.info(f"Cleaned up {count} expired OTPs")
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired OTPs: {e}")
            db.rollback()
            return 0 