from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

# Import Database and Models
from app.database.connection import get_db
from app.models.market_data import ScrapPriceHistory, Location
# Import Category Models for Lookups
from app.models.scrapCategories import ScrapCategory, ScrapMaterial, ScrapGrade
# Import Schemas
from app.schemas.market_data import MarketPriceCreate, MarketPriceResponse

router = APIRouter(
    prefix="/market-prices",
    tags=["Market Prices"]
)

# --- 1. NEW: Schema for Google Sheet Rows ---
class SheetRow(BaseModel):
    DATE: str
    TIME: str
    SCRAP_TYPE: str
    CATEGORY: str
    MATERIAL: str
    GRADE: Optional[str] = None
    LOCATION: str
    PRICE: float
    CURRENCY: str = "INR" # Default if column missing
    PER_UNIT: str = "MT"  # Default if column missing

# --- 2. NEW: Bulk Sync Endpoint ---
@router.post("/bulk-sheet-sync")
def sync_google_sheet(rows: List[SheetRow], db: Session = Depends(get_db)):
    """
    Receives raw rows from Google Sheets, maps names to IDs, and inserts into DB.
    Handles multiple tabs sent as one big list.
    """
    # A. Pre-fetch Maps (Optimization to avoid 1000 DB calls)
    # We convert DB names to lowercase for case-insensitive matching
    try:
        loc_map = {l.location_name.strip().lower(): l.id for l in db.query(Location).all()}
        cat_map = {c.material_category.strip().lower(): c.id for c in db.query(ScrapCategory).all()}
        mat_map = {m.material_name.strip().lower(): m.id for m in db.query(ScrapMaterial).all()}
        grade_map = {g.grade_name.strip().lower(): g.id for g in db.query(ScrapGrade).all()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load reference data: {str(e)}")

    new_entries = []
    errors = []

    # B. Loop through Incoming Rows
    for i, row in enumerate(rows):
        try:
            # Normalize Inputs (trim and lowercase)
            loc_name = row.LOCATION.strip().lower()
            cat_name = row.CATEGORY.strip().lower()
            mat_name = row.MATERIAL.strip().lower()
            grade_name = row.GRADE.strip().lower() if row.GRADE else None

            # Get IDs from Maps
            loc_id = loc_map.get(loc_name)
            cat_id = cat_map.get(cat_name)
            mat_id = mat_map.get(mat_name)
            
            # Grade is optional in DB, so if not found in map, check if it was provided
            grade_id = None
            if grade_name:
                grade_id = grade_map.get(grade_name)
                # If grade provided but not found, you might want to log it or skip. 
                # For now, we proceed with None or log error if strict.

            # Validation: Critical IDs must exist
            if not loc_id:
                errors.append(f"Row {i+1}: Location '{row.LOCATION}' not found in DB.")
                continue
            if not cat_id:
                errors.append(f"Row {i+1}: Category '{row.CATEGORY}' not found in DB.")
                continue
            if not mat_id:
                errors.append(f"Row {i+1}: Material '{row.MATERIAL}' not found in DB.")
                continue

            # Parse Timestamp (Date + Time columns)
            # Incoming: "2026-01-17" and "14:00:00" or "14:00"
            dt_str = f"{row.DATE} {row.TIME}"
            try:
                # Try standard format
                recorded_at = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
            except ValueError:
                try:
                    # Try with seconds if Excel adds them
                    recorded_at = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    # Fallback to now if format is totally broken
                    recorded_at = datetime.now()

            # Create Record Object
            new_entries.append(ScrapPriceHistory(
                location_id=loc_id,
                category_id=cat_id,
                material_id=mat_id,
                grade_id=grade_id,
                price_per_mt=row.PRICE,
                currency=row.CURRENCY,
                unit=row.PER_UNIT,
                recorded_at=recorded_at
            ))

        except Exception as e:
            errors.append(f"Row {i+1}: processing error - {str(e)}")

    # C. Bulk Insert
    if new_entries:
        try:
            db.add_all(new_entries)
            db.commit()
        except Exception as e:
            db.rollback()
            return {"status": "error", "detail": f"Database Insert Failed: {str(e)}", "errors": errors}

    return {
        "status": "success", 
        "inserted": len(new_entries), 
        "failed_count": len(errors),
        "errors": errors
    }

# --- 3. EXISTING: Single Add Endpoint (Used by Admin UI) ---
@router.post("/add", response_model=MarketPriceResponse)
def add_market_price(price_data: MarketPriceCreate, db: Session = Depends(get_db)):
    """
    Record a new market price entry into SCRAP_PRICES_HISTORY.
    """
    # 1. Create Model Instance
    new_price = ScrapPriceHistory(
        category_id=price_data.category_id,
        material_id=price_data.material_id,
        grade_id=price_data.grade_id,
        location_id=price_data.location_id,
        price_per_mt=price_data.price_per_mt,
        # Use provided date or default to NOW()
        recorded_at=price_data.recorded_at if price_data.recorded_at else func.now()
    )
    
    try:
        db.add(new_price)
        db.commit()
        db.refresh(new_price)
        return new_price
    except Exception as e:
        db.rollback()
        print(f"Error adding price: {str(e)}") # Debugging log
        raise HTTPException(status_code=500, detail="Failed to save market price.")

# --- 4. EXISTING: History Endpoint ---
@router.get("/history", response_model=List[MarketPriceResponse])
def get_price_history(limit: int = 50, db: Session = Depends(get_db)):
    """
    Fetch latest prices (Optional for Admin View)
    """
    prices = db.query(ScrapPriceHistory).order_by(ScrapPriceHistory.recorded_at.desc()).limit(limit).all()
    return prices
