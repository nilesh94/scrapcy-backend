from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.connection import Base


class ProductCategory(Base):
    __tablename__ = "PRODUCT_CATEGORIES"
    __table_args__ = {"schema": "SCRAPCY_APP"}

    id = Column("ID", Integer, primary_key=True, index=True)
    category_name = Column("CATEGORY_NAME", String(200), nullable=False)
    category_type = Column("CATEGORY_TYPE", String(30), nullable=False)
    display_label = Column("DISPLAY_LABEL", String(200), nullable=True)
    is_active = Column("IS_ACTIVE", Integer, default=1)
    created_at = Column("CREATED_AT", DateTime(timezone=True), server_default=func.current_timestamp())

    families = relationship("MaterialFamily", back_populates="category")


class MaterialFamily(Base):
    __tablename__ = "MATERIAL_FAMILIES"
    __table_args__ = {"schema": "SCRAPCY_APP"}

    id = Column("ID", Integer, primary_key=True, index=True)
    category_id = Column("CATEGORY_ID", Integer, ForeignKey("SCRAPCY_APP.PRODUCT_CATEGORIES.ID"), nullable=False)
    family_name = Column("FAMILY_NAME", String(200), nullable=False)
    is_active = Column("IS_ACTIVE", Integer, default=1)
    created_at = Column("CREATED_AT", DateTime(timezone=True), server_default=func.current_timestamp())

    category = relationship("ProductCategory", back_populates="families")
    types = relationship("MaterialType", back_populates="family")


class MaterialType(Base):
    __tablename__ = "MATERIAL_TYPES"
    __table_args__ = {"schema": "SCRAPCY_APP"}

    id = Column("ID", Integer, primary_key=True, index=True)
    family_id = Column("FAMILY_ID", Integer, ForeignKey("SCRAPCY_APP.MATERIAL_FAMILIES.ID"), nullable=False)
    type_name = Column("TYPE_NAME", String(200), nullable=False)
    is_active = Column("IS_ACTIVE", Integer, default=1)
    created_at = Column("CREATED_AT", DateTime(timezone=True), server_default=func.current_timestamp())

    family = relationship("MaterialFamily", back_populates="types")
    products = relationship("ProductCatalog", back_populates="type")
    forms = relationship("ProductForm", back_populates="type")


class ProductCatalog(Base):
    __tablename__ = "PRODUCT_CATALOG"
    __table_args__ = {"schema": "SCRAPCY_APP"}

    id = Column("ID", Integer, primary_key=True, index=True)
    type_id = Column("TYPE_ID", Integer, ForeignKey("SCRAPCY_APP.MATERIAL_TYPES.ID"), nullable=False)
    product_name = Column("PRODUCT_NAME", String(250), nullable=False)
    product_code = Column("PRODUCT_CODE", String(100), nullable=False)
    is_active = Column("IS_ACTIVE", Integer, default=1)
    created_at = Column("CREATED_AT", DateTime(timezone=True), server_default=func.current_timestamp())

    type = relationship("MaterialType", back_populates="products")
    grades = relationship("ProductGrade", back_populates="product")
    # Relationship to ScrapPrice (one-to-many)
    prices = relationship("ScrapPrice", back_populates="product")


class ProductGrade(Base):
    __tablename__ = "PRODUCT_GRADES"
    __table_args__ = {"schema": "SCRAPCY_APP"}

    id = Column("ID", Integer, primary_key=True, index=True)
    product_id = Column("PRODUCT_ID", Integer, ForeignKey("SCRAPCY_APP.PRODUCT_CATALOG.ID"), nullable=False)
    grade_name = Column("GRADE_NAME", String(150), nullable=False)
    grade_code = Column("GRADE_CODE", String(100), nullable=True)
    is_active = Column("IS_ACTIVE", Integer, default=1)
    created_at = Column("CREATED_AT", DateTime(timezone=True), server_default=func.current_timestamp())

    product = relationship("ProductCatalog", back_populates="grades")
    dimensions = relationship("ProductDimension", back_populates="grade")


class ProductDimension(Base):
    __tablename__ = "PRODUCT_DIMENSIONS"
    __table_args__ = {"schema": "SCRAPCY_APP"}

    id = Column("ID", Integer, primary_key=True, index=True)
    grade_id = Column("GRADE_ID", Integer, ForeignKey("SCRAPCY_APP.PRODUCT_GRADES.ID"), nullable=False)
    dimension_value = Column("DIMENSION_VALUE", String(100), nullable=False)
    unit_type = Column("UNIT_TYPE", String(50), nullable=True)
    is_active = Column("IS_ACTIVE", Integer, default=1)
    created_at = Column("CREATED_AT", DateTime(timezone=True), server_default=func.current_timestamp())

    grade = relationship("ProductGrade", back_populates="dimensions")


class ProductForm(Base):
    __tablename__ = "PRODUCT_FORMS"
    __table_args__ = {"schema": "SCRAPCY_APP"}

    id = Column("ID", Integer, primary_key=True, index=True)
    type_id = Column("TYPE_ID", Integer, ForeignKey("SCRAPCY_APP.MATERIAL_TYPES.ID"), nullable=False)
    form_name = Column("FORM_NAME", String(120), nullable=False)
    is_active = Column("IS_ACTIVE", Integer, default=1)
    created_at = Column("CREATED_AT", DateTime(timezone=True), server_default=func.current_timestamp())

    type = relationship("MaterialType", back_populates="forms")


class ScrapPrice(Base):
    """
    SCRAP_PRICES table - lean, leaf-level FKs only.
    
    IMPORTANT: 
    - product_code is trigger-managed (server_default), NEVER set from Python
    - effective_to is trigger-managed, NEVER set from Python
    - updated_at is trigger-managed, NEVER set from Python
    - NO category_id, family_id, type_id columns exist in the table
    """
    __tablename__ = "SCRAP_PRICES"
    __table_args__ = {"schema": "SCRAPCY_APP"}

    id = Column("ID", Integer, primary_key=True, index=True, autoincrement=True)
    # Leaf-level FKs only - no category_id, family_id, type_id
    product_id = Column("PRODUCT_ID", Integer, ForeignKey("SCRAPCY_APP.PRODUCT_CATALOG.ID"), nullable=False)
    grade_id = Column("GRADE_ID", Integer, ForeignKey("SCRAPCY_APP.PRODUCT_GRADES.ID"), nullable=False)
    dimension_id = Column("DIMENSION_ID", Integer, ForeignKey("SCRAPCY_APP.PRODUCT_DIMENSIONS.ID"), nullable=True)
    form_id = Column("FORM_ID", Integer, ForeignKey("SCRAPCY_APP.PRODUCT_FORMS.ID"), nullable=True)
    # product_code is trigger-managed - map as read-only
    product_code = Column("PRODUCT_CODE", String(100), nullable=True, insert_default=None)
    location_id = Column("LOCATION_ID", Integer, ForeignKey("LOCATIONS.ID"), nullable=False)
    base_price = Column("BASE_PRICE", Numeric(12, 2), nullable=False)
    price_unit = Column("PRICE_UNIT", String(20), nullable=False, default='INR/MT')
    currency = Column("CURRENCY", String(10), nullable=False, default='INR')
    effective_from = Column("EFFECTIVE_FROM", DateTime(timezone=True), server_default=func.now(), nullable=False)
    # effective_to is trigger-managed - NEVER set from Python
    effective_to = Column("EFFECTIVE_TO", DateTime(timezone=True), nullable=True)
    is_active = Column("IS_ACTIVE", Integer, default=1)
    source = Column("SOURCE", String(30), default="MANUAL")
    created_by = Column("CREATED_BY", String(100), nullable=True)
    created_at = Column("CREATED_AT", DateTime(timezone=True), server_default=func.current_timestamp())
    # updated_at is trigger-managed - NEVER set from Python
    updated_at = Column("UPDATED_AT", DateTime(timezone=True), nullable=True)

    # Relationships - leaf-level only
    product = relationship("ProductCatalog", back_populates="prices")
    grade = relationship("ProductGrade")
    dimension = relationship("ProductDimension")
    form = relationship("ProductForm")
    location = relationship("Location")
    # One-to-many relationship with ScrapPriceSource
    price_sources = relationship("ScrapPriceSource", back_populates="price", cascade="all, delete-orphan")


class ScrapPriceSource(Base):
    """
    SCRAP_PRICE_SOURCES table - child table for multi-source price tracking.
    
    One row per source per price. Allows tracking prices from multiple sources
    (e.g., WhatsApp, MM, other apps) for the same base price entry.
    
    IMPORTANT:
    - UNIQUE constraint on (PRICE_ID, SOURCE_NAME)
    - variance is computed in Python: SOURCE_PRICE - BASE_PRICE
    - price_unit and currency NULL = inherit from parent SCRAP_PRICES row
    - ON DELETE CASCADE from parent SCRAP_PRICES
    """
    __tablename__ = "SCRAP_PRICE_SOURCES"
    __table_args__ = (
        {"schema": "SCRAPCY_APP"}
    )

    id = Column("ID", Integer, primary_key=True, index=True, autoincrement=True)
    price_id = Column("PRICE_ID", Integer, ForeignKey("SCRAPCY_APP.SCRAP_PRICES.ID", ondelete="CASCADE"), nullable=False)
    source_name = Column("SOURCE_NAME", String(100), nullable=False)  # e.g., 'SR_WHATSAPP', 'SR_MM'
    source_price = Column("SOURCE_PRICE", Numeric(12, 2), nullable=False)
    price_unit = Column("PRICE_UNIT", String(20), nullable=True)  # NULL = inherit from parent
    currency = Column("CURRENCY", String(10), nullable=True)  # NULL = inherit from parent
    variance = Column("VARIANCE", Numeric(12, 2), nullable=True)  # Computed: SOURCE_PRICE - BASE_PRICE
    notes = Column("NOTES", String(500), nullable=True)
    recorded_at = Column("RECORDED_AT", DateTime(timezone=True), server_default=func.current_timestamp())
    created_at = Column("CREATED_AT", DateTime(timezone=True), server_default=func.current_timestamp())

    # Relationship back to ScrapPrice
    price = relationship("ScrapPrice", back_populates="price_sources")
