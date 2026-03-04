from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base
# Import for relationship mapping (Updated to include ScrapForm)
from .scrapCategories import ScrapCategory, ScrapMaterial, ScrapForm, ScrapGrade

class ScrapListing(Base):
    __tablename__ = "scrap_listings"

    id = Column(Integer, primary_key=True, index=True)
    
    # Seller Details
    seller_name = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=True)
    gst_number = Column(String(50), nullable=True)
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    alternate_phone = Column(String(50), nullable=True)
    
    # --- UPDATED: Match Oracle Constraints & New Hierarchy ---
    category_id = Column(Integer, ForeignKey("scrap_categories.id"), nullable=False) 
    material_id = Column(Integer, ForeignKey("scrap_materials.id"), nullable=False)
    form_id = Column(Integer, ForeignKey("scrap_form.id"), nullable=True) # Added Form ID
    grade_id = Column(Integer, ForeignKey("scrap_grades.id"), nullable=True)

    # Legacy Columns (Keep for backward compatibility)
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
    # SaaS Standard: Using timezone-aware DateTime with high-precision timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp())
    
    # Relationships
    images = relationship("ScrapImage", back_populates="listing", cascade="all, delete-orphan")
    
    # Relationships for Pydantic Serialization
    category_ref = relationship("ScrapCategory", lazy="joined")
    material_ref = relationship("ScrapMaterial", lazy="joined")
    form_ref = relationship("ScrapForm", lazy="joined") # Added Form Ref
    grade_ref = relationship("ScrapGrade", lazy="joined")


# --- THIS CLASS WAS MISSING ---
class ScrapImage(Base):
    __tablename__ = "scrap_images"
    
    id = Column(Integer, primary_key=True, index=True)
    scrap_listing_id = Column(Integer, ForeignKey("scrap_listings.id"))
    
    seller_email = Column(String(255))
    image_url = Column(Text) # Using Text for URLs to avoid length limits
    drive_file_id = Column(String(255), nullable=True)
    
    is_active = Column(Boolean, default=True)
    # SaaS Standard: Using timezone-aware DateTime with high-precision timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp())
    
    listing = relationship("ScrapListing", back_populates="images")
