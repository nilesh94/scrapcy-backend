from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
import datetime

# Correct import from your structure
from app.database.connection import Base 

class ScrapListing(Base):
    __tablename__ = "scrap_listings"

    id = Column(Integer, primary_key=True, index=True)
    
    # Seller Details - ADDED LENGTHS TO ALL STRINGS
    seller_name = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=True)
    gst_number = Column(String(50), unique=True, nullable=True)
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    
    # Scrap Details
    scrap_type = Column(String(100), nullable=False)
    quantity = Column(Float, nullable=False)
    price_per_unit = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False) # 'Kg', 'Tons'
    
    # Metadata
    is_admin_entry = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationship
    images = relationship("ScrapImage", back_populates="listing")

class ScrapImage(Base):
    __tablename__ = "scrap_images"

    id = Column(Integer, primary_key=True, index=True)
    scrap_listing_id = Column(Integer, ForeignKey("scrap_listings.id"), nullable=False)
    
    # Added lengths here too
    seller_email = Column(String(255), nullable=False)
    image_url = Column(String(500), nullable=False) 
    drive_file_id = Column(String(255), nullable=True)
    
    is_active = Column(Boolean, default=True)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Back Reference
    listing = relationship("ScrapListing", back_populates="images")
