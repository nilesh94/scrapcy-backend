from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
import datetime

from app.database.connection import Base 

class ScrapListing(Base):
    __tablename__ = "scrap_listings"

    id = Column(Integer, primary_key=True)
    
    # Seller Details
    seller_name = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=True)
    gst_number = Column(String(50), unique=True, nullable=True)
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    
    # Scrap Details
    scrap_type = Column(String(100), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)       # e.g., 'Tons', 'Kg', 'Liters'
    
    price_per_unit = Column(Float, nullable=False)
    price_unit = Column(String(50), nullable=False) # NEW COLUMN: e.g., 'Per Ton', 'Per Kg'
    
    # Metadata
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
