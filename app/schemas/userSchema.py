
# File: app/users/schemas.py

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime  # Changed from date to datetime

# 1. Base Schema (Shared properties)
class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone: str
    role: str = "user"
    
    # Optional Business Fields
    # These default to None, which perfectly matches your DB and Frontend logic
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

# 3. Login Input
class UserLogin(BaseModel):
    email: EmailStr
    password: str
    
# 4. Output Schema (What we send back to Frontend)
class UserOut(UserBase):
    id: int
    # REMOVED: is_active: int  <-- removed because your Oracle Table does not have this column
    created_at: datetime       # Changed to datetime to match SQL TIMESTAMP (includes time)

    class Config:
        from_attributes = True
