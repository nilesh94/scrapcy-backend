from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String, index=True)  # 'bidder' or 'company'
    
    # Common Fields
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique=True, index=True)
    phone = Column(String)
    hashed_password = Column(String)
    
    # Company Specific Fields (Nullable)
    company_name = Column(String, nullable=True)
    business_type = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    turnover = Column(String, nullable=True)
    gst_number = Column(String, nullable=True)
    pan_number = Column(String, nullable=True)
    
    # Address
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    pincode = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
