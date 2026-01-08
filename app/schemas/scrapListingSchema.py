from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

# --- IMAGE SCHEMAS ---
class ScrapImageBase(BaseModel):
    image_url: str
    is_active: bool = True

class ScrapImageResponse(ScrapImageBase):
    id: int
    scrap_listing_id: int
    uploaded_at: datetime

    class Config:
        from_attributes = True

# --- LISTING SCHEMAS ---
class ScrapListingBase(BaseModel):
    seller_name: str
    company_name: Optional[str] = None
    gst_number: Optional[str] = None
    email: EmailStr
    phone: str
    scrap_type: str
    quantity: float
    unit: str               # Quantity Unit
    price_per_unit: float
    price_unit: str         # NEW: Price Unit

class ScrapListingCreate(ScrapListingBase):
    is_admin_entry: bool = False

class ScrapListingResponse(ScrapListingBase):
    id: int
    is_admin_entry: bool
    created_at: datetime
    images: List[ScrapImageResponse] = []

    class Config:
        from_attributes = True
