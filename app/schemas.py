from pydantic import BaseModel, EmailStr
from typing import Optional

# Base Schema
class UserBase(BaseModel):
    firstName: str
    lastName: str
    email: EmailStr
    phone: str
    role: str

# Schema for creating a user (Incoming Data)
class UserCreate(UserBase):
    password: str
    confirmPassword: str
    
    # Optional Company Fields
    companyName: Optional[str] = None
    businessType: Optional[str] = None
    industry: Optional[str] = None
    turnover: Optional[str] = None
    gstNumber: Optional[str] = None
    panNumber: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None

# Schema for reading a user (Response Data)
class UserOut(UserBase):
    id: int
    companyName: Optional[str] = None

    class Config:
        from_attributes = True
