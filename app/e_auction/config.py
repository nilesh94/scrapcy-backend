"""
E-Auction Module Configuration
Multi-environment support (local, development, staging, production)
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
from functools import lru_cache
from enum import Enum


class Environment(str, Enum):
    """Environment types"""
    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Multi-environment settings"""
    
    # Environment
    APP_ENV: Environment = Environment.LOCAL
    DEBUG: bool = True
    APP_NAME: str = "SCRAPCY E-Auction"
    API_VERSION: str = "v1"
    
    # Database (environment-based)
    LOCAL_DATABASE_URL: str = "oracle+oracledb://SCRAPCY_APP:local@localhost:1521/XEPDB1"
    PROD_DATABASE_URL: Optional[str] = None
    
    @property
    def DATABASE_URL(self) -> str:
        #Check if we are on Render (which uses Environment.PRODUCTION)
        if self.APP_ENV == Environment.PRODUCTION and self.PROD_DATABASE_URL:
            return self.PROD_DATABASE_URL
        return self.LOCAL_DATABASE_URL
    
    # URLs (environment-based)
    LOCAL_BACKEND_URL: str = "http://localhost:8000"
    LOCAL_FRONTEND_URL: str = "http://localhost:3000"
    PROD_BACKEND_URL: str = "https://scrapcy-backend.onrender.com"
    PROD_FRONTEND_URL: str = "https://scrapcy.com"
    
    @property
    def BACKEND_URL(self) -> str:
        return self.PROD_BACKEND_URL if self.APP_ENV == Environment.PRODUCTION else self.LOCAL_BACKEND_URL
    
    @property
    def FRONTEND_URL(self) -> str:
        return self.PROD_FRONTEND_URL if self.APP_ENV == Environment.PRODUCTION else self.LOCAL_FRONTEND_URL
    
    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    
    @property
    def allowed_origins_list(self) -> List[str]:
        if self.APP_ENV == Environment.LOCAL:
            return ["http://localhost:3000", "http://localhost:3001", "http://localhost:8000"]
        return self.ALLOWED_ORIGINS.split(",")
    
    # Redis
    LOCAL_REDIS_URL: str = "redis://localhost:6379/0"
    PROD_REDIS_URL: Optional[str] = None
    
    @property
    def REDIS_URL(self) -> str:
        return self.PROD_REDIS_URL if (self.APP_ENV == Environment.PRODUCTION and self.PROD_REDIS_URL) else self.LOCAL_REDIS_URL
    
    REDIS_PASSWORD: Optional[str] = None
    REDIS_MAX_CONNECTIONS: int = 10
    REDIS_CACHE_TTL: int = 3600
    
    # Storage
    STORAGE_PROVIDER: str = "local"
    LOCAL_UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "ap-south-1"
    AWS_S3_BUCKET: Optional[str] = None
    AWS_S3_PUBLIC_URL: Optional[str] = None
    OCI_NAMESPACE: Optional[str] = None
    OCI_BUCKET: Optional[str] = None
    OCI_REGION: str = "ap-mumbai-1"
    OCI_COMPARTMENT_ID: Optional[str] = None
    OCI_CONFIG_FILE: str = "~/.oci/config"
    OCI_CONFIG_PROFILE: str = "DEFAULT"
    GOOGLE_SHEETS_CREDENTIALS_FILE: Optional[str] = None
    GOOGLE_SHEETS_FOLDER_ID: Optional[str] = None
    
    # Payments
    RAZORPAY_ENABLED: bool = False
    LOCAL_RAZORPAY_KEY_ID: str = "rzp_test_local"
    LOCAL_RAZORPAY_KEY_SECRET: str = "local_secret"
    PROD_RAZORPAY_KEY_ID: Optional[str] = None
    PROD_RAZORPAY_KEY_SECRET: Optional[str] = None
    
    @property
    def RAZORPAY_KEY_ID(self) -> str:
        return self.PROD_RAZORPAY_KEY_ID if (self.APP_ENV == Environment.PRODUCTION and self.PROD_RAZORPAY_KEY_ID) else self.LOCAL_RAZORPAY_KEY_ID
    
    @property
    def RAZORPAY_KEY_SECRET(self) -> str:
        return self.PROD_RAZORPAY_KEY_SECRET if (self.APP_ENV == Environment.PRODUCTION and self.PROD_RAZORPAY_KEY_SECRET) else self.LOCAL_RAZORPAY_KEY_SECRET
    
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = None
    PAYMENT_CURRENCY: str = "INR"
    PAYMENT_TIMEOUT_MINUTES: int = 15
    
    # Email/SMS
    EMAIL_ENABLED: bool = False
    EMAIL_PROVIDER: str = "sendgrid"
    SENDGRID_API_KEY: Optional[str] = None
    EMAIL_FROM: str = "noreply@scrapcy.com"
    EMAIL_FROM_NAME: str = "SCRAPCY"
    SMS_ENABLED: bool = False
    SMS_PROVIDER: str = "msg91"
    MSG91_AUTH_KEY: Optional[str] = None
    MSG91_SENDER_ID: str = "SCRPCY"
    
    # OTP
    OTP_EXPIRY_MINUTES: int = 10
    OTP_LENGTH: int = 6
    OTP_MAX_ATTEMPTS: int = 3
    
    # Verification
    GST_VERIFICATION_ENABLED: bool = False
    PAN_VERIFICATION_ENABLED: bool = False
    
    # Scheduler
    SCHEDULER_ENABLED: bool = True
    AUCTION_CHECK_INTERVAL_SECONDS: int = 30
    
    @property
    def scheduler_interval(self) -> int:
        return 60 if self.APP_ENV == Environment.LOCAL else self.AUCTION_CHECK_INTERVAL_SECONDS
    
    # Commission
    DEFAULT_SELLER_COMMISSION_PERCENT: float = 2.0
    DEFAULT_BUYER_COMMISSION_PERCENT: float = 1.0
    GST_RATE_PERCENT: float = 18.0
    TDS_RATE_PERCENT: float = 1.0
    
    # Auction
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
    
    @property
    def log_level_value(self) -> str:
        if self.APP_ENV == Environment.LOCAL:
            return "DEBUG"
        return "WARNING" if self.APP_ENV == Environment.PRODUCTION else "INFO"
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    
    @property
    def is_rate_limit_enabled(self) -> bool:
        return False if self.APP_ENV == Environment.LOCAL else self.RATE_LIMIT_ENABLED
    
    # Features
    FEATURE_AUTO_BIDDING_ENABLED: bool = True
    FEATURE_BUY_NOW_ENABLED: bool = True
    FEATURE_WATCHLIST_ENABLED: bool = True
    
    # UPDATED: Use SettingsConfigDict for Pydantic V2
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def is_local() -> bool:
    return get_settings().APP_ENV == Environment.LOCAL


def is_production() -> bool:
    return get_settings().APP_ENV == Environment.PRODUCTION


def get_allowed_origins() -> List[str]:
    return get_settings().allowed_origins_list


settings = get_settings()
