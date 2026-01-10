from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
import datetime

from app.database.connection import Base 

class ScrapListing(Base):
    __tablename__ = "scrap_listings"

    id = Column(Integer, primary_key=True)
    
    # --- Seller Details ---
    seller_name = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=True)
    gst_number = Column(String(50), unique=True, nullable=True)
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    alternate_phone = Column(String(50), nullable=True) # NEW: Alternate Contact
    
    # --- Scrap Details ---
    scrap_type = Column(String(100), nullable=False)
    grade = Column(String(100), nullable=True)          # NEW: Grade (e.g., HMS 1, Grade A)
    description = Column(String(1000), nullable=True)   # NEW: Detailed Description
    
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    
    price_per_unit = Column(Float, nullable=False)
    price_unit = Column(String(50), nullable=False)

    monthly_capacity = Column(String, nullable=True)
    
    # --- Location & Pickup ---
    address = Column(String(500), nullable=False)       # NEW: Detailed Location
    pickup_conditions = Column(String(500), nullable=True) # NEW: Pickup rules
    
    # --- Metadata ---
    is_admin_entry = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationship
    images = relationship("ScrapImage", back_populates="listing")

class ScrapImage(Base):
    __tablename__ = "scrap_images"

    id = Column(Integer, primary_key=True)
    scrap_listing_id = Column(Integer, ForeignKey("scrap_listings.id"), nullable=False)
    
    seller_email = Column(String(255), nullable=False)
    image_url = Column(String(500), nullable=False) 
    drive_file_id = Column(String(255), nullable=True)
    
    is_active = Column(Boolean, default=True)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

    listing = relationship("ScrapListing", back_populates="images")
