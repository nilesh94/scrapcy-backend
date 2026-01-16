from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database.connection import get_db
from app.models.market_data import Location

# IMPORT THE NEW SCHEMA HERE
from app.schemas.locations import LocationResponse, LocationCreate 

router = APIRouter(
    prefix="/locations",
    tags=["Locations"]
)

# Use List[LocationResponse] to tell FastAPI to format the data as a list of JSON objects
@router.get("/", response_model=List[LocationResponse])
def get_locations(db: Session = Depends(get_db)):
    """Fetch all active locations for dropdowns."""
    locations = db.query(Location).filter(Location.is_active == 1).all()
    return locations

@router.post("/", response_model=LocationResponse)
def create_location(location: LocationCreate, db: Session = Depends(get_db)):
    """Add a new location (Optional helper for you)"""
    new_loc = Location(**location.dict())
    db.add(new_loc)
    db.commit()
    db.refresh(new_loc)
    return new_loc
