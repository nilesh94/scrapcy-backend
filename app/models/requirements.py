from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey, text
from app.database.connection import Base

class BuyerRequirement(Base):
    __tablename__ = "BUYER_REQUIREMENTS"

    id = Column("ID", Integer, primary_key=True, index=True)
    user_id = Column("USER_ID", Integer, ForeignKey("USERS.ID"), nullable=True)
    
    scrap_type = Column("SCRAP_TYPE", String(100))
    category = Column("CATEGORY", String(100))
    material = Column("MATERIAL", String(100))
    form = Column("FORM", String(100))
    grade = Column("GRADE", String(100))
    locations = Column("PREFERRED_LOCATIONS", String(1000))
    
    description = Column("DESCRIPTION", Text)
    note = Column("NOTE_TO_SELLER", String(1000), nullable=True)
    
    # Guest Fields
    guest_name = Column("GUEST_NAME", String(100), nullable=True)
    guest_email = Column("GUEST_EMAIL", String(255), nullable=True)
    guest_phone = Column("GUEST_PHONE", String(20), nullable=True)
    guest_company = Column("GUEST_COMPANY", String(255), nullable=True)
    guest_gst = Column("GUEST_GST", String(50), nullable=True)
    
    # Status including 'DELETED'
    status = Column("STATUS", String(20), default="OPEN")
    
    created_at = Column("CREATED_AT", TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column("UPDATED_AT", TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))
