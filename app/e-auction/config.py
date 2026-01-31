"""
E-Auction Module Configuration
Loads all environment variables and provides configuration objects
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os
from functools import lru_cache


class Settings(BaseSettings):
    """Main application settings"""
    
    # Application
    APP_NAME: str = "SCRAPCY E-Auction"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_VERSION: str = "v1"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # URLs
    BACKEND_URL: str
    FRONTEND_URL: str
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    
    # Database
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None
    REDIS_MAX_CONNECTIONS: int = 10
    REDIS_CACHE_TTL: int = 3600
    
    # File Storage
    STORAGE_PROVIDER: str = "s3"  # s3, oci, local
    
    # AWS S3
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "ap-south-1"
    AWS_S3_BUCKET: Optional[str] = None
    AWS_S3_PUBLIC_URL: Optional[str] = None
    
    # OCI Object Storage
    OCI_NAMESPACE: Optional[str] = None
    OCI_BUCKET: Optional[str] = None
    OCI_REGION: str = "ap-mumbai-1"
    OCI_COMPARTMENT_ID: Optional[str] = None
    
    # Local Storage
    LOCAL_UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    
    # Payment Gateway (Razorpay)
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = None
    RAZORPAY_ENABLED: bool = False
    PAYMENT_CURRENCY: str = "INR"
    PAYMENT_TIMEOUT_MINUTES: int = 15
    
    # Email
    EMAIL_ENABLED: bool = False
    EMAIL_PROVIDER: str = "sendgrid"
    SENDGRID_API_KEY: Optional[str] = None
    EMAIL_FROM: str = "noreply@scrapcy.com"
    EMAIL_FROM_NAME: str = "SCRAPCY"
    
    # SMS
    SMS_ENABLED: bool = False
    SMS_PROVIDER: str = "msg91"
    MSG91_AUTH_KEY: Optional[str] = None
    MSG91_SENDER_ID: str = "SCRPCY"
    MSG91_ROUTE: str = "4"
    MSG91_TEMPLATE_ID_OTP: Optional[str] = None
    
    # OTP
    OTP_EXPIRY_MINUTES: int = 10
    OTP_LENGTH: int = 6
    OTP_MAX_ATTEMPTS: int = 3
    OTP_RESEND_COOLDOWN_SECONDS: int = 60
    
    # GST Verification
    GST_VERIFICATION_ENABLED: bool = False
    GST_VERIFICATION_PROVIDER: str = "karza"
    GST_API_KEY: Optional[str] = None
    GST_API_URL: Optional[str] = None
    
    # PAN Verification
    PAN_VERIFICATION_ENABLED: bool = False
    PAN_VERIFICATION_PROVIDER: str = "karza"
    PAN_API_KEY: Optional[str] = None
    PAN_API_URL: Optional[str] = None
    
    # Background Scheduler
    SCHEDULER_ENABLED: bool = True
    AUCTION_CHECK_INTERVAL_SECONDS: int = 30
    NOTIFICATION_BATCH_SIZE: int = 100
    
    # Commission
    DEFAULT_SELLER_COMMISSION_PERCENT: float = 2.0
    DEFAULT_BUYER_COMMISSION_PERCENT: float = 1.0
    GST_RATE_PERCENT: float = 18.0
    TDS_RATE_PERCENT: float = 1.0
    
    # Auction Settings
    DEFAULT_EXTENSION_TRIGGER_MINUTES: int = 5
    DEFAULT_EXTENSION_DURATION_MINUTES: int = 5
    MAX_AUCTION_EXTENSIONS: int = 10
    MIN_BID_INCREMENT_PERCENT: float = 1.0
    BID_RATE_LIMIT_PER_MINUTE: int = 10
    
    # WebSocket
    WS_HEARTBEAT_INTERVAL_SECONDS: int = 30
    WS_MAX_CONNECTIONS_PER_USER: int = 3
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    LOG_MAX_BYTES: int = 10485760
    LOG_BACKUP_COUNT: int = 5
    LOG_FORMAT: str = "json"
    
    # Monitoring
    PROMETHEUS_ENABLED: bool = False
    PROMETHEUS_PORT: int = 9090
    SENTRY_DSN: Optional[str] = None
    SENTRY_ENVIRONMENT: str = "development"
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BID_PER_MINUTE: int = 10
    
    # Feature Flags
    FEATURE_AUTO_BIDDING_ENABLED: bool = True
    FEATURE_BUY_NOW_ENABLED: bool = True
    FEATURE_DUTCH_AUCTION_ENABLED: bool = False
    FEATURE_WATCHLIST_ENABLED: bool = True
    FEATURE_RATINGS_ENABLED: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    Using lru_cache to avoid reading .env file multiple times
    """
    return Settings()


# Convenience getters
def get_database_url() -> str:
    """Get database URL"""
    return get_settings().DATABASE_URL


def get_redis_url() -> str:
    """Get Redis URL"""
    return get_settings().REDIS_URL


def is_production() -> bool:
    """Check if running in production"""
    return get_settings().APP_ENV == "production"


def is_development() -> bool:
    """Check if running in development"""
    return get_settings().APP_ENV == "development"


def get_allowed_origins() -> list:
    """Get CORS allowed origins as list"""
    return get_settings().ALLOWED_ORIGINS.split(",")


# Export settings instance
settings = get_settings()
