from pydantic import BaseModel, EmailStr, field_validator, Field, ConfigDict
from typing import Optional
from datetime import datetime, timezone

# Shared properties
class RequirementBase(BaseModel):
    # --- NEW: Add this field ---
    scrap_listing_id: Optional[int] = Field(default=None, alias="scrapListingId")

    # INTERNAL: snake_case (matches DB) | EXTERNAL: camelCase (matches Frontend)
    scrap_type: str = Field(alias="scrapType")
    category: str
    material: str
    form: str
    grade: str
    locations: str 
    description: str
    note: Optional[str] = None
    
    # Guest fields
    guest_name: Optional[str] = Field(default=None, alias="guestName")
    guest_email: Optional[EmailStr] = Field(default=None, alias="guestEmail")
    guest_phone: Optional[str] = Field(default=None, alias="guestPhone")
    guest_company: Optional[str] = Field(default=None, alias="guestCompany")
    guest_gst: Optional[str] = Field(default=None, alias="guestGst")

    # Correct V2 Configuration
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    @field_validator('guest_email', 'guest_name', 'guest_phone', 'guest_company', 'guest_gst', 'note', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

class RequirementCreate(RequirementBase):
    pass

class RequirementUpdateStatus(BaseModel):
    status: str 

class RequirementOut(RequirementBase):
    id: int
    user_id: Optional[int]
    status: str
    created_at: datetime
    # SaaS Standard: Include server_time for frontend synchronization
    server_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # UPDATED: Removed 'class Config' and replaced with V2 standard model_config
    # (Though it inherits from RequirementBase, being explicit ensures the warning disappears)
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
