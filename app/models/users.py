from sqlalchemy import Column, Integer, String, TIMESTAMP, text
from app.database.connection import Base

class User(Base):
    __tablename__ = "USERS"
    
    id = Column("ID", Integer, primary_key=True, index=True)
    role = Column("ROLE", String(50), nullable=False)
    
    first_name = Column("FIRST_NAME", String(100), nullable=False)
    last_name = Column("LAST_NAME", String(100), nullable=False)
    email = Column("EMAIL", String(255), unique=True, index=True, nullable=False)
    phone = Column("PHONE", String(20), nullable=False)
    
    # Mapped to "HASHED_PASSWORD"
    hashed_password = Column("HASHED_PASSWORD", String(255), nullable=False)
    
    # Optional Fields (Nullable)
    company_name = Column("COMPANY_NAME", String(255), nullable=True)
    business_type = Column("BUSINESS_TYPE", String(100), nullable=True)
    industry = Column("INDUSTRY", String(255), nullable=True)
    turnover = Column("TURNOVER", String(100), nullable=True)
    
    gst_number = Column("GST_NUMBER", String(50), nullable=True)
    pan_number = Column("PAN_NUMBER", String(50), nullable=True)
    
    address = Column("ADDRESS", String(500), nullable=True)
    city = Column("CITY", String(100), nullable=True)
    state = Column("STATE", String(100), nullable=True)
    pincode = Column("PINCODE", String(20), nullable=True)
    
    is_active = Column("IS_ACTIVE", Integer, default=1)
    email_verified = Column("EMAIL_VERIFIED", Integer, default=0)
    gst_verified = Column("GST_VERIFIED", Integer, default=0)

    created_at = Column("CREATED_AT", TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column("UPDATED_AT", TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))
    last_login_at = Column("LAST_LOGIN_AT", TIMESTAMP, nullable=True)
