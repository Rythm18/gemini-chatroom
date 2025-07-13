from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database configuration
    DB_HOST: str
    DB_PORT: int = 5432
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    
    # Redis configuration
    REDIS_URL: str
    
    # JWT configuration
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # Google Gemini API configuration
    GOOGLE_API_KEY: str
    
    # OTP configuration
    OTP_EXPIRATION_MINUTES: int = 5
    
    # Rate limiting for Basic tier
    BASIC_TIER_DAILY_LIMIT: int = 5
    
    # Caching configuration
    CACHE_TTL_SECONDS: int = 300  # 5 minutes
    
    # Application settings
    APP_NAME: str = "Gemini-Style Chatroom"
    DEBUG: bool = True
    
    # Celery configuration
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # Stripe Configuration - with better error handling
    STRIPE_TEST_SECRET_KEY: Optional[str] = None
    STRIPE_TEST_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_TEST_PRICE_ID_PRO: Optional[str] = None
    
    # Webhook configuration
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    def validate_stripe_config(self):
        """Validate that all required Stripe environment variables are set"""
        missing_vars = []
        if not self.STRIPE_TEST_SECRET_KEY:
            missing_vars.append("STRIPE_TEST_SECRET_KEY")
        if not self.STRIPE_TEST_PUBLISHABLE_KEY:
            missing_vars.append("STRIPE_TEST_PUBLISHABLE_KEY")
        if not self.STRIPE_TEST_PRICE_ID_PRO:
            missing_vars.append("STRIPE_TEST_PRICE_ID_PRO")
        if not self.STRIPE_WEBHOOK_SECRET:
            missing_vars.append("STRIPE_WEBHOOK_SECRET")
        
        if missing_vars:
            raise ValueError(f"Missing required Stripe environment variables: {', '.join(missing_vars)}")

    class Config:
        env_file = '.env'
        extra = 'ignore'

settings = Settings()