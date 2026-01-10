from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base
# Import for relationship mapping
from .scrapCategories import ScrapCategory, ScrapMaterial, ScrapGrade

class ScrapListing(Base):
    __tablename__ = "scrap_listings"

    id = Column(Integer, primary_key=True, index=True)
    
    # Seller Details
    # Note: Added lengths (e.g. 255) which are required for Oracle VARCHAR2
    seller_name = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=True)
    gst_number = Column(String(50), nullable=True)
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    alternate_phone = Column(String(50), nullable=True)
    
    # --- NEW ID COLUMNS (Levels 2, 3, 4) ---
    category_id = Column(Integer, ForeignKey("scrap_categories.id"), nullable=True)
    material_id = Column(Integer, ForeignKey("scrap_materials.id"), nullable=True)
    grade_id = Column(Integer, ForeignKey("scrap_grades.id"), nullable=True)

    # Legacy Columns (Auto-filled for backward compatibility)
    scrap_type = Column(String(100), nullable=False)
    grade = Column(String(100), nullable=True)
    
    description = Column(Text, nullable=True)
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    monthly_capacity = Column(String(100), nullable=True) 
    price_per_unit = Column(Float, nullable=False)
    price_unit = Column(String(50), nullable=False)
    
    address = Column(Text, nullable=False)
    pickup_conditions = Column(Text, nullable=True)
    
    is_admin_entry = Column(Boolean, default=False)
    added_by = Column(String(50), default="admin")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    images = relationship("ScrapImage", back_populates="listing", cascade="all, delete-orphan")
    
    # Relationships to Categories (Optional usage)
    category_ref = relationship("ScrapCategory")
    material_ref = relationship("ScrapMaterial")
    grade_ref = relationship("ScrapGrade")

class ScrapImage(Base):
    __tablename__ = "scrap_images"
    
    id = Column(Integer, primary_key=True, index=True)
    scrap_listing_id = Column(Integer, ForeignKey("scrap_listings.id"))
    
    seller_email = Column(String(255))
    image_url = Column(Text) # Using Text for URLs to avoid length limits
    drive_file_id = Column(String(255), nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    listing = relationship("ScrapListing", back_populates="images")
