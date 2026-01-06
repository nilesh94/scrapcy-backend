from sqlalchemy import Column, Integer, String, Boolean, DateTime, Identity
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"

    # 1. PRIMARY KEY (Oracle Specific)
    # Using Identity(start=1, cycle=True) tells Oracle to auto-generate this number.
    id = Column(Integer, Identity(start=1), primary_key=True)

    # 2. CORE FIELDS (Required for everyone)
    role = Column(String(50), nullable=False)  # 'bidder' or 'company'
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # 3. COMPANY SPECIFIC FIELDS (Nullable)
    # These are empty for 'bidder', filled for 'company'
    company_name = Column(String(255), nullable=True)
    business_type = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    turnover = Column(String(100), nullable=True)
    gst_number = Column(String(50), nullable=True)
    pan_number = Column(String(50), nullable=True)
    
    # 4. ADDRESS FIELDS
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(20), nullable=True)

    # 5. METADATA
    is_active = Column(Boolean, default=True)
    # server_default=func.now() ensures the DB sets the time, not Python
    created_at = Column(DateTime(timezone=True), server_default=func.now())
