from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

# ==========================
# 1. IMAGE SCHEMAS
# ==========================

class ScrapImageBase(BaseModel):
    image_url: str
    is_active: bool = True

class ScrapImageCreate(ScrapImageBase):
    pass

class ScrapImageResponse(ScrapImageBase):
    id: int
    scrap_listing_id: int
    uploaded_at: datetime

    class Config:
        from_attributes = True  # Allows Pydantic to read SQLAlchemy models

# ==========================
# 2. LISTING SCHEMAS
# ==========================

# Shared properties
class ScrapListingBase(BaseModel):
    seller_name: str
    company_name: Optional[str] = None
    gst_number: Optional[str] = None
    email: EmailStr  # Validates that it is a proper email format
    phone: str
    scrap_type: str  # e.g. "Ferrous", "Non-Ferrous"
    quantity: float
    price_per_unit: float
    unit: str        # e.g. "Kg", "Tons"

# Properties to receive on item creation (if using JSON body)
# Note: Your current route uses Form(...), but this is good to have.
class ScrapListingCreate(ScrapListingBase):
    is_admin_entry: bool = False

# Properties to return to client (The Response)
class ScrapListingResponse(ScrapListingBase):
    id: int
    is_admin_entry: bool
    created_at: datetime

    # NESTED IMAGES: This automatically fetches the related images
    images: List[ScrapImageResponse] = []

    class Config:
        from_attributes = True
