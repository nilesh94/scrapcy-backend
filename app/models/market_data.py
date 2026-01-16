from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base
# Ensure you import your existing models to resolve ForeignKeys
from .scrapCategories import ScrapCategory, ScrapMaterial, ScrapGrade

class Location(Base):
    __tablename__ = "LOCATIONS"

    id = Column("ID", Integer, primary_key=True, index=True)
    location_name = Column("LOCATION_NAME", String(100), nullable=False)
    city = Column("CITY", String(100), nullable=True)
    state = Column("STATE", String(100), nullable=True)
    country = Column("COUNTRY", String(100), nullable=True)
    pincode = Column("PINCODE", String(20), nullable=True)
    geographic_zone = Column("GEOGRAPHIC_ZONE", String(50), nullable=True)
    
    # Using Float for Oracle NUMBER(10,8)
    latitude = Column("LATITUDE", Float, nullable=True)
    longitude = Column("LONGITUDE", Float, nullable=True)
    
    # 1 for Active, 0 for Inactive
    is_active = Column("IS_ACTIVE", Integer, default=1)
    
    state_gst_code = Column("STATE_GST_CODE", String(2), nullable=True)
    search_aliases = Column("SEARCH_ALIASES", String(500), nullable=True)
    
    created_at = Column("CREATED_AT", DateTime(timezone=True), server_default=func.now())

    # Relationship to Price History
    prices = relationship("ScrapPriceHistory", back_populates="location")


class ScrapPriceHistory(Base):
    __tablename__ = "SCRAP_PRICES_HISTORY"

    id = Column("ID", Integer, primary_key=True, index=True)
    
    category_id = Column("CATEGORY_ID", Integer, ForeignKey("scrap_categories.id"), nullable=False)
    material_id = Column("MATERIAL_ID", Integer, ForeignKey("scrap_materials.id"), nullable=False)
    grade_id = Column("GRADE_ID", Integer, ForeignKey("scrap_grades.id"), nullable=True)
    location_id = Column("LOCATION_ID", Integer, ForeignKey("LOCATIONS.ID"), nullable=False)
    
    price_per_mt = Column("PRICE_PER_MT", Float, nullable=False)
    
    # recorded_at is the "effective time" of the price
    recorded_at = Column("RECORDED_AT", DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column("CREATED_AT", DateTime(timezone=True), server_default=func.now())

    # Relationships
    location = relationship("Location", back_populates="prices")
    
    # Lazy='joined' helps fetch names automatically when querying history
    category = relationship("ScrapCategory", lazy="joined")
    material = relationship("ScrapMaterial", lazy="joined")
    grade = relationship("ScrapGrade", lazy="joined")
