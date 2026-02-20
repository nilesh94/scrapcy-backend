# File: app/schemas/userSchema.py

from pydantic import BaseModel, EmailStr, ConfigDict 
from typing import Optional
from datetime import datetime

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

    is_active: Optional[int] = 1
    email_verified: Optional[int] = 0
    gst_verified: Optional[int] = 0

# 2. Input Schema (Frontend -> Backend)
class UserCreate(UserBase):
    password: str

# 3. Login Input
class UserLogin(BaseModel):
    email: EmailStr
    password: str
    
# 4. Output Schema (Backend -> Frontend)
class UserOut(UserBase):
    id: int
    created_at: datetime  # Includes timestamp

    # UPDATED: Replaced legacy class Config with V2 model_config
    model_config = ConfigDict(from_attributes=True)

# 5. Registration Response Schema (Token + User Object)
class UserRegistrationResponse(BaseModel):
    message: str
    access_token: str
    token_type: str
    user: UserOut
