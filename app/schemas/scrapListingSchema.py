from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import List, Optional
from datetime import datetime, timezone
# SaaS Standard: Import centralized UTC serializer
from app.e_auction.utils.serialization import datetime_to_utc_iso

# --- HELPER SCHEMAS (FIXED: MATCH DB COLUMN NAMES) ---
class CategoryOut(BaseModel):
    id: int
    material_category: str 
    scrap_type: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class MaterialOut(BaseModel):
    id: int
    material_name: str 

    model_config = ConfigDict(from_attributes=True)

class FormOut(BaseModel):
    id: int
    form_name: str

    model_config = ConfigDict(from_attributes=True)

class GradeOut(BaseModel):
    id: int
    grade_name: str

    model_config = ConfigDict(from_attributes=True)

# --- IMAGE SCHEMAS ---
class ScrapImageBase(BaseModel):
    image_url: str
    is_active: bool = True

class ScrapImageResponse(ScrapImageBase):
    id: int
    scrap_listing_id: int
    created_at: Optional[datetime] = None 

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: datetime_to_utc_iso}
    )

# --- LISTING SCHEMAS ---
class ScrapListingBase(BaseModel):
    seller_name: str
    company_name: Optional[str] = None
    gst_number: Optional[str] = None
    email: EmailStr
    phone: str
    alternate_phone: Optional[str] = None
    
    category_id: int
    material_id: int
    form_id: Optional[int] = None 
    grade_id: Optional[int] = None

    scrap_type: str               
    grade: Optional[str] = None 
    
    description: Optional[str] = None
    quantity: float
    unit: str
    price_per_unit: float
    price_unit: str
    monthly_capacity: Optional[str] = None
    
    address: str
    pickup_conditions: Optional[str] = None

class ScrapListingCreate(ScrapListingBase):
    is_admin_entry: bool = False

class ScrapListingResponse(ScrapListingBase):
    id: int
    is_admin_entry: bool
    created_at: datetime
    
    category_ref: Optional[CategoryOut] = None
    material_ref: Optional[MaterialOut] = None
    form_ref: Optional[FormOut] = None     
    grade_ref: Optional[GradeOut] = None

    images: List[ScrapImageResponse] = []
    
    # SaaS Standard: Include server_time for frontend synchronization
    server_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: datetime_to_utc_iso}
    )

# =======================================================
# NEW: HIERARCHY SCHEMAS (For Dropdown Menus)
# =======================================================

class GradeHierarchyResponse(BaseModel):
    id: int
    grade_name: str
    is_active: bool = True
    
    model_config = ConfigDict(from_attributes=True)

class FormHierarchyResponse(BaseModel):
    id: int
    form_name: str
    is_active: bool = True
    grades: List[GradeHierarchyResponse] = []
    
    model_config = ConfigDict(from_attributes=True)

class MaterialHierarchyResponse(BaseModel):
    id: int
    material_name: str
    is_active: bool = True
    forms: List[FormHierarchyResponse] = []
    
    model_config = ConfigDict(from_attributes=True)

class CategoryHierarchyResponse(BaseModel):
    id: int
    scrap_type: str
    material_category: str
    is_active: bool = True
    materials: List[MaterialHierarchyResponse] = []
    
    # SaaS Standard: Include server_time for hierarchy synchronization
    server_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: datetime_to_utc_iso}
    )
