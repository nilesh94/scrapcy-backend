from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime, timezone
# SaaS Standard: Import centralized UTC serializer
from app.e_auction.utils.serialization import datetime_to_utc_iso

class LocationBase(BaseModel):
    location_name: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "India"
    pincode: Optional[str] = None
    geographic_zone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # --- ADDED NEW FIELDS ---
    location_type: Optional[str] = None
    state_gst_code: Optional[str] = None
    search_aliases: Optional[str] = None

class LocationCreate(LocationBase):
    pass

class LocationResponse(LocationBase):
    id: int
    is_active: int
    created_at: Optional[datetime]
    
    # SaaS Standard: Include server_time for frontend synchronization
    server_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # UPDATED: Using Pydantic V2 model_config
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: datetime_to_utc_iso}
    )
