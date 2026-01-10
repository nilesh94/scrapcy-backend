from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

# --- HELPER SCHEMAS (FIXED: MATCH DB COLUMN NAMES) ---
class CategoryOut(BaseModel):
    id: int
    material_category: str 
    # Optional: Include scrap_type if you need it in the nested object
    scrap_type: Optional[str] = None
    
    class Config:
        from_attributes = True

class MaterialOut(BaseModel):
    id: int
    # WAS: name: str
    material_name: str 

    class Config:
        from_attributes = True

class GradeOut(BaseModel):
    id: int
    # WAS: name: str
    grade_name: str

    class Config:
        from_attributes = True

# --- IMAGE SCHEMAS ---
class ScrapImageBase(BaseModel):
    image_url: str
    is_active: bool = True

class ScrapImageResponse(ScrapImageBase):
    id: int
    scrap_listing_id: int
    created_at: Optional[datetime] = None 

    class Config:
        from_attributes = True

# --- LISTING SCHEMAS ---
class ScrapListingBase(BaseModel):
    # Seller
    seller_name: str
    company_name: Optional[str] = None
    gst_number: Optional[str] = None
    email: EmailStr
    phone: str
    alternate_phone: Optional[str] = None
    
    # IDs
    category_id: int
    material_id: int
    grade_id: Optional[int] = None

    # Legacy Fields
    scrap_type: str            
    grade: Optional[str] = None 
    
    # Scrap Details
    description: Optional[str] = None
    quantity: float
    unit: str
    price_per_unit: float
    price_unit: str
    monthly_capacity: Optional[str] = None
    
    # Location
    address: str
    pickup_conditions: Optional[str] = None

class ScrapListingCreate(ScrapListingBase):
    is_admin_entry: bool = False

class ScrapListingResponse(ScrapListingBase):
    id: int
    is_admin_entry: bool
    created_at: datetime
    
    # Nested Relationship Objects
    category_ref: Optional[CategoryOut] = None
    material_ref: Optional[MaterialOut] = None
    grade_ref: Optional[GradeOut] = None

    images: List[ScrapImageResponse] = []

    class Config:
        from_attributes = True
