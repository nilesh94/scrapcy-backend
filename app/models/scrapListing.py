from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database.connection import Base
import datetime

class ScrapListing(Base):
    __tablename__ = "scrap_listings"

    id = Column(Integer, primary_key=True, index=True)
    
    # Seller Details
    seller_name = Column(String, nullable=False)
    company_name = Column(String, nullable=True)
    gst_number = Column(String, unique=True, nullable=True)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    
    # Scrap Details
    scrap_type = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    price_per_unit = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    
    # Metadata
    is_admin_entry = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationship to Images
    images = relationship("ScrapImage", back_populates="listing")

class ScrapImage(Base):
    __tablename__ = "scrap_images"

    id = Column(Integer, primary_key=True, index=True)
    
    # Links
    scrap_listing_id = Column(Integer, ForeignKey("scrap_listings.id"), nullable=False)
    seller_email = Column(String, nullable=False) # Using Email to track seller easily
    
    # Image Data
    image_url = Column(String, nullable=False)
    drive_file_id = Column(String, nullable=True) # Optional: Store Drive ID for deletion later
    
    # Status
    is_active = Column(Boolean, default=True)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Back Reference
    listing = relationship("ScrapListing", back_populates="images")
