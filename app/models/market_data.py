from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base
# UPDATED IMPORT: Added ScrapForm so the relationship works
from .scrapCategories import ScrapCategory, ScrapMaterial, ScrapForm, ScrapGrade

class Location(Base):
    __tablename__ = "LOCATIONS"

    id = Column("ID", Integer, primary_key=True, index=True)
    location_name = Column("LOCATION_NAME", String(100), nullable=False)
    city = Column("CITY", String(100), nullable=True)
    state = Column("STATE", String(100), nullable=True)
    country = Column("COUNTRY", String(100), nullable=True)
    pincode = Column("PINCODE", String(20), nullable=True)
    geographic_zone = Column("GEOGRAPHIC_ZONE", String(50), nullable=True)
    
    # Matching NUMBER(10,8) and NUMBER(11,8)
    latitude = Column("LATITUDE", Float, nullable=True)
    longitude = Column("LONGITUDE", Float, nullable=True)
    
    # Matching NUMBER(1)
    is_active = Column("IS_ACTIVE", Integer, default=1)
    
    # --- MISSING FIELDS ADDED HERE ---
    location_type = Column("LOCATION_TYPE", String(20), nullable=True) 
    state_gst_code = Column("STATE_GST_CODE", String(2), nullable=True)
    search_aliases = Column("SEARCH_ALIASES", String(500), nullable=True)
    
    # SaaS Standard: UTC-aware creation tracking
    created_at = Column("CREATED_AT", DateTime(timezone=True), server_default=func.current_timestamp())

    # Relationship
    prices = relationship("ScrapPriceHistory", back_populates="location")


class ScrapPriceHistory(Base):
    __tablename__ = "SCRAP_PRICES_HISTORY"

    id = Column("ID", Integer, primary_key=True, index=True)
    
    category_id = Column("CATEGORY_ID", Integer, ForeignKey("scrap_categories.id"), nullable=False)
    material_id = Column("MATERIAL_ID", Integer, ForeignKey("scrap_materials.id"), nullable=False)
    
    # --- NEW FIELD ADDED HERE ---
    form_id = Column("FORM_ID", Integer, ForeignKey("scrap_form.id"), nullable=True)
    
    grade_id = Column("GRADE_ID", Integer, ForeignKey("scrap_grades.id"), nullable=True)
    location_id = Column("LOCATION_ID", Integer, ForeignKey("LOCATIONS.ID"), nullable=False)
    
    price_per_mt = Column("PRICE_PER_MT", Float, nullable=False)
    currency = Column("CURRENCY", String(10), default="INR")
    unit = Column("UNIT", String(20), default="MT")
    
    # SaaS Standard: Ensuring price index history is recorded with UTC standard
    recorded_at = Column("RECORDED_AT", DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False)
    created_at = Column("CREATED_AT", DateTime(timezone=True), server_default=func.current_timestamp())

    # Relationships
    location = relationship("Location", back_populates="prices")
    category = relationship("ScrapCategory", lazy="joined")
    material = relationship("ScrapMaterial", lazy="joined")
    
    # --- NEW RELATIONSHIP ADDED HERE ---
    form = relationship("ScrapForm", lazy="joined")
    
    grade = relationship("ScrapGrade", lazy="joined")
