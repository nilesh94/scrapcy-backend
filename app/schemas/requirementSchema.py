from pydantic import BaseModel, EmailStr, field_validator, Field, ConfigDict
from typing import Optional
from datetime import datetime

# Shared properties
class RequirementBase(BaseModel):
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

    # CONFIG: Critical for mapping DB objects to this schema
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    # VALIDATOR: Convert empty strings to None
    @field_validator('guest_email', 'guest_name', 'guest_phone', 'guest_company', 'guest_gst', 'note', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

# Input for Creation
class RequirementCreate(RequirementBase):
    pass

# Input for Status Update
class RequirementUpdateStatus(BaseModel):
    status: str 

# Output Schema
class RequirementOut(RequirementBase):
    id: int
    user_id: Optional[int]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
