from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date

# Base Schema
class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone: str
    role: str = "user"
    
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

# Input (Register)
class UserCreate(UserBase):
    password: str

# Output (Response)
class UserOut(UserBase):
    id: int
    is_active: int
    created_at: date

    class Config:
        from_attributes = True
