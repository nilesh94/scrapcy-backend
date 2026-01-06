# File: app/users/schemas.py

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date

# 1. Base Schema (Shared properties)
class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone: str
    role: str = "user"
    
    # Optional Business Fields
    company_name: Optional[str] = None
    business_type: Optional[str] = None
    industry: Optional[str] = None
    turnover: Optional[str] = None
    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None

# 2. Input Schema (What Frontend sends to /register)
class UserCreate(UserBase):
    password: str

# 3. Output Schema (What we send back to Frontend)
# We exclude the password for security!
class UserOut(UserBase):
    id: int
    is_active: int
    created_at: date

    class Config:
        from_attributes = True
