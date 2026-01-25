from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime

# Shared properties
class RequirementBase(BaseModel):
    scrapType: str
    category: str
    material: str
    form: str
    grade: str
    locations: str
    description: str
    note: Optional[str] = None
    
    # Guest fields (Optional)
    guestName: Optional[str] = None
    guestEmail: Optional[EmailStr] = None
    guestPhone: Optional[str] = None
    guestCompany: Optional[str] = None
    guestGst: Optional[str] = None

    # This converts empty strings "" sent from frontend into None (null)
    # so that Optional[EmailStr] accepts them.
    @field_validator('guestEmail', 'guestName', 'guestPhone', 'guestCompany', 'guestGst', 'note', mode='before')
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
    status: str  # OPEN, CLOSED, FULFILLED, DELETED

# Output Schema
class RequirementOut(RequirementBase):
    id: int
    user_id: Optional[int]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
