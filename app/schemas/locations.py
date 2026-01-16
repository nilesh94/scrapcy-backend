from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# 1. Base Schema (Common fields)
class LocationBase(BaseModel):
    location_name: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "India"
    pincode: Optional[str] = None
    geographic_zone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

# 2. Schema for Creating a Location (Input)
class LocationCreate(LocationBase):
    pass

# 3. Schema for Reading a Location (Output/Response)
class LocationResponse(LocationBase):
    id: int
    is_active: int
    # We include ID and Active status when sending data TO the frontend
    
    class Config:
        # This tells Pydantic to read data even if it's an ORM object (from Database)
        from_attributes = True
