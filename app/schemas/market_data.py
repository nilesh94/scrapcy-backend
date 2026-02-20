from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

# --- LOCATION SCHEMAS ---
class LocationBase(BaseModel):
    location_name: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "India"
    pincode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geographic_zone: Optional[str] = None

class LocationCreate(LocationBase):
    pass

class LocationResponse(LocationBase):
    id: int
    is_active: int

    # UPDATED for Pydantic V2
    model_config = ConfigDict(from_attributes=True)

# --- MARKET PRICE SCHEMAS ---
class MarketPriceBase(BaseModel):
    category_id: int
    material_id: int
    grade_id: Optional[int] = None
    location_id: int
    price_per_mt: float
    recorded_at: Optional[datetime] = None

class MarketPriceCreate(MarketPriceBase):
    pass

# Nested Objects for readable responses
class CategorySimple(BaseModel):
    id: int
    material_category: str
    
    # UPDATED for Pydantic V2
    model_config = ConfigDict(from_attributes=True)

class MaterialSimple(BaseModel):
    id: int
    material_name: str
    
    # UPDATED for Pydantic V2
    model_config = ConfigDict(from_attributes=True)

class GradeSimple(BaseModel):
    id: int
    grade_name: str
    
    # UPDATED for Pydantic V2
    model_config = ConfigDict(from_attributes=True)

class MarketPriceResponse(MarketPriceBase):
    id: int
    created_at: datetime
    
    # Expand details
    location: Optional[LocationResponse]
    category: Optional[CategorySimple]
    material: Optional[MaterialSimple]
    grade: Optional[GradeSimple]

    # UPDATED for Pydantic V2
    model_config = ConfigDict(from_attributes=True)
