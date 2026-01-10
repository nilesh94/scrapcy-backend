from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

# --- HELPER SCHEMAS FOR NESTED RELATIONS ---
# These are used to serialize the relationship objects (level 1, 2, 3)
class CategoryOut(BaseModel):
    id: int
    name: str
    
    class Config:
        from_attributes = True

class MaterialOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

class GradeOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

# --- IMAGE SCHEMAS ---
class ScrapImageBase(BaseModel):
    image_url: str
    is_active: bool = True

class ScrapImageResponse(ScrapImageBase):
    id: int
    scrap_listing_id: int
    # Note: Ensure your DB model uses 'created_at' or 'uploaded_at' consistently.
    # Based on previous context, SQLAlchemy usually defaults to created_at.
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
    
    # --- NEW ID FIELDS (Required by Oracle DB) ---
    # These correspond to the foreign keys in your DB
    category_id: int
    material_id: int
    grade_id: Optional[int] = None

    # Legacy Fields (Kept for backward compatibility)
    scrap_type: str            # You can eventually make this Optional or auto-fill it from category_id
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
    
    # --- NESTED RELATIONSHIP OBJECTS ---
    # These allow the frontend to access names (e.g., item.category_ref.name)
    category_ref: Optional[CategoryOut] = None
    material_ref: Optional[MaterialOut] = None
    grade_ref: Optional[GradeOut] = None

    images: List[ScrapImageResponse] = []

    class Config:
        from_attributes = True
