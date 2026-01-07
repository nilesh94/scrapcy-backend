from sqlalchemy import Column, Integer, String, TIMESTAMP, text
from app.database.connection import Base

class User(Base):
    # If you created the table as "USERS" in the "ADMIN" schema:
    __tablename__ = "USERS"
    # If the above fails, try: __tablename__ = "users" 
    # (Oracle usually defaults unquoted names to uppercase, 
    # but since you used quotes in creation, we must match carefully).

    # Explicit Mapping: Python Variable = Column("EXACT_DB_COLUMN_NAME", Type)
    id = Column("ID", Integer, primary_key=True)
    role = Column("ROLE", String(50), nullable=False)
    
    first_name = Column("FIRST_NAME", String(100), nullable=False)
    last_name = Column("LAST_NAME", String(100), nullable=False)
    email = Column("EMAIL", String(255), unique=True, index=True, nullable=False)
    phone = Column("PHONE", String(20), nullable=False)
    
    # IMPORTANT: Map 'hashed_password' to "HASHED_PASSWORD"
    hashed_password = Column("HASHED_PASSWORD", String(255), nullable=False)
    
    # Optional Fields (Nullable)
    company_name = Column("COMPANY_NAME", String(255), nullable=True)
    business_type = Column("BUSINESS_TYPE", String(100), nullable=True)
    industry = Column("INDUSTRY", String(100), nullable=True)
    turnover = Column("TURNOVER", String(100), nullable=True)
    
    gst_number = Column("GST_NUMBER", String(50), nullable=True)
    pan_number = Column("PAN_NUMBER", String(50), nullable=True)
    
    address = Column("ADDRESS", String(500), nullable=True)
    city = Column("CITY", String(100), nullable=True)
    state = Column("STATE", String(100), nullable=True)
    pincode = Column("PINCODE", String(20), nullable=True)
    
    # Timestamp with default value
    created_at = Column("CREATED_AT", TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
