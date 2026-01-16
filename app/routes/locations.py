from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database.connection import get_db
from app.models.market_data import Location
from app.schemas.market_data import LocationResponse, LocationCreate

router = APIRouter(
    prefix="/locations",
    tags=["Locations"]
)

@router.get("/", response_model=List[LocationResponse])
def get_locations(db: Session = Depends(get_db)):
    """Fetch all active locations for dropdowns."""
    locations = db.query(Location).filter(Location.is_active == 1).all()
    return locations

# Optional: Endpoint to seed locations if you need to add them via API
@router.post("/", response_model=LocationResponse)
def create_location(location: LocationCreate, db: Session = Depends(get_db)):
    new_loc = Location(**location.dict())
    db.add(new_loc)
    db.commit()
    db.refresh(new_loc)
    return new_loc
