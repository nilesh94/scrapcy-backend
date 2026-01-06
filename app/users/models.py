# File: app/users/models.py

from sqlalchemy import Column, Integer, String, Date, SmallInteger, Identity
from sqlalchemy.sql import func
from app.database.connection import Base  # Import Base from our new database file

class User(Base):
    __tablename__ = "users"

    # Primary Key (No Cycle for Oracle compatibility)
    id = Column(Integer, Identity(start=1), primary_key=True)
    
    # Authentication Fields
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="user")
    
    # Personal Info
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    
    # Business Info (Nullable)
    company_name = Column(String(255), nullable=True)
    business_type = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    turnover = Column(String(100), nullable=True)
    gst_number = Column(String(50), nullable=True)
    pan_number = Column(String(50), nullable=True)
    
    # Address Info
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(20), nullable=True)
    
    # System Metadata
    is_active = Column(SmallInteger, default=1)
    created_at = Column(Date, server_default=func.current_date())
