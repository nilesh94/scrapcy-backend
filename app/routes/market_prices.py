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

# --- 1. UPDATED Schema (Matches Your Google Sheet Headers Exactly) ---
class SheetRow(BaseModel):
    Date: str              # Matches sheet header "Date"
    Time_Slot: str = "00:00" # Matches sheet header "Time_Slot"
    SCRAP_TYPE: str        # Matches sheet header "SCRAP_TYPE"
    CATEGORY: str          # Matches sheet header "CATEGORY"
    Material: str          # Matches sheet header "Material"
    Grade: Optional[str] = None # Matches sheet header "Grade"
    Location: str          # Matches sheet header "Location"
    Price: float           # Matches sheet header "Price"
    Currency: str = "INR"  # Matches sheet header "Currency"
    PER_UNIT: str = "MT"   # Matches sheet header "PER_UNIT"

# --- 2. Bulk Sync Endpoint (With Alias Support) ---
@router.post("/bulk-sheet-sync")
def sync_google_sheet(rows: List[SheetRow], db: Session = Depends(get_db)):
    """
    Receives raw rows from Google Sheets, maps names to IDs, and inserts into DB.
    Handles multiple tabs sent as one big list.
    Checks SEARCH_ALIASES for location matching.
    """
    
    # --- A. Pre-fetch Maps (Optimization) ---
    try:
        # 1. Build Location Map (Name + Aliases)
        loc_map = {}
        all_locations = db.query(Location).all()
        
        for loc in all_locations:
            # Map Primary Name (e.g. "mandi gobindgarh" -> 55)
            primary_name = loc.location_name.strip().lower()
            loc_map[primary_name] = loc.id
            
            # Map Aliases (e.g. "mandi" -> 55)
            if loc.search_aliases:
                # Split by comma, strip spaces, lowercase
                aliases = [a.strip().lower() for a in loc.search_aliases.split(',') if a.strip()]
                for alias in aliases:
                    loc_map[alias] = loc.id

        # 2. Build Maps for Categories, Materials, Grades
        cat_map = {c.material_category.strip().lower(): c.id for c in db.query(ScrapCategory).all()}
        mat_map = {m.material_name.strip().lower(): m.id for m in db.query(ScrapMaterial).all()}
        grade_map = {g.grade_name.strip().lower(): g.id for g in db.query(ScrapGrade).all()}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load reference data: {str(e)}")

    new_entries = []
    errors = []

    # --- B. Loop through Incoming Rows ---
    for i, row in enumerate(rows):
        try:
            # Normalize Inputs (Using NEW Variable Names)
            loc_name = row.Location.strip().lower()     # Changed to .Location
            cat_name = row.CATEGORY.strip().lower()     # Kept .CATEGORY
            mat_name = row.Material.strip().lower()     # Changed to .Material
            grade_name = row.Grade.strip().lower() if row.Grade else None # Changed to .Grade

            # Lookups (loc_map now checks Aliases too!)
            loc_id = loc_map.get(loc_name)
            cat_id = cat_map.get(cat_name)
            mat_id = mat_map.get(mat_name)
            grade_id = grade_map.get(grade_name) if grade_name else None

            # Validation: Critical IDs must exist
            if not loc_id:
                errors.append(f"Row {i+1}: Location '{row.Location}' not found (checked aliases too).")
                continue
            if not cat_id:
                errors.append(f"Row {i+1}: Category '{row.CATEGORY}' not found in DB.")
                continue
            if not mat_id:
                errors.append(f"Row {i+1}: Material '{row.Material}' not found in DB.")
                continue

            # Parse Timestamp (Using .Date and .Time_Slot)
            dt_str = f"{row.Date} {row.Time_Slot}"
            try:
                # Try standard format YYYY-MM-DD HH:MM
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
                price_per_mt=row.Price,         # Changed to .Price
                currency=row.Currency,          # Changed to .Currency
                unit=row.PER_UNIT,              # Kept .PER_UNIT
                recorded_at=recorded_at
            ))

        except Exception as e:
            errors.append(f"Row {i+1}: processing error - {str(e)}")

    # --- C. Bulk Insert ---
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

@router.get("/search")
def search_price(
    location: str,
    query_term: Optional[str] = None, # Can be Material Name OR Category Name OR None
    db: Session = Depends(get_db)
):
    """
    Universal Search:
    - If 'query_term' matches a MATERIAL -> Returns price for that material.
    - If 'query_term' matches a CATEGORY -> Returns prices for ALL materials in that category.
    - If 'query_term' is EMPTY -> Returns ALL prices for the location.
    """
    
    # 1. RESOLVE LOCATION
    loc_search = location.strip().lower()
    location_obj = db.query(Location).filter(
        (func.lower(Location.location_name) == loc_search) |
        (func.lower(Location.city) == loc_search) |
        (func.lower(Location.search_aliases).like(f"%{loc_search}%"))
    ).first()

    if not location_obj:
        return {"status": "error", "message": f"Location '{location}' not found."}

    # 2. DETERMINE SCOPE (Material vs. Category vs. All)
    target_material_id = None
    target_category_id = None
    
    if query_term:
        term = query_term.strip().lower()
        
        # A) Check if it's a MATERIAL (e.g., "HMS Scrap")
        mat_obj = db.query(ScrapMaterial).filter(
            (func.lower(ScrapMaterial.material_name) == term) | 
            (func.lower(ScrapMaterial.material_name).like(f"%{term}%"))
        ).first()
        
        if mat_obj:
            target_material_id = mat_obj.id
        else:
            # B) Check if it's a CATEGORY (e.g., "Ferrous")
            cat_obj = db.query(ScrapCategory).filter(
                func.lower(ScrapCategory.material_category) == term
            ).first()
            if cat_obj:
                target_category_id = cat_obj.id
            else:
                return {"status": "error", "message": f"Could not find material or category matching '{query_term}'"}

    # 3. FETCH PRICES (The "Latest per Material" Logic)
    # We need to fetch the latest price for *each* material relevant to the query.
    
    # Base Filter
    filters = [ScrapPriceHistory.location_id == location_obj.id]
    
    if target_material_id:
        filters.append(ScrapPriceHistory.material_id == target_material_id)
    elif target_category_id:
        filters.append(ScrapPriceHistory.category_id == target_category_id)
        
    # Get all records matching criteria, ordered by date desc
    # (In a real production app, you'd use a subquery to get distinct materials, 
    # but for simplicity, we fetch recent rows and deduce latest in Python)
    raw_history = db.query(ScrapPriceHistory).filter(*filters)\
        .order_by(ScrapPriceHistory.material_id, ScrapPriceHistory.recorded_at.desc())\
        .limit(100).all() # Safety limit

    if not raw_history:
        return {"status": "no_data", "message": f"No data found for {location_obj.location_name}"}

    # 4. GROUP BY MATERIAL (Find latest for each)
    latest_map = {} # Key: MaterialID -> Record
    for record in raw_history:
        if record.material_id not in latest_map:
            latest_map[record.material_id] = record
    
    results = []
    
    # 5. CALCULATE MOVING AVERAGE FOR EACH RESULT
    for mat_id, record in latest_map.items():
        # 5-Day Avg Logic
        end_date = record.recorded_at
        start_date = end_date - timedelta(days=5)
        
        avg_price = db.query(func.avg(ScrapPriceHistory.price_per_mt)).filter(
            ScrapPriceHistory.location_id == location_obj.id,
            ScrapPriceHistory.material_id == mat_id,
            ScrapPriceHistory.recorded_at >= start_date,
            ScrapPriceHistory.recorded_at <= end_date
        ).scalar()
        
        # Resolve Names
        mat_name = db.query(ScrapMaterial).get(mat_id).material_name
        grade_name = record.grade.grade_name if record.grade else "General"

        results.append({
            "material": mat_name,
            "grade": grade_name,
            "price": record.price_per_mt,
            "unit": record.unit,
            "date": record.recorded_at.strftime("%Y-%m-%d"),
            "avg_5d": round(avg_price, 2) if avg_price else record.price_per_mt,
            "trend": "UP" if record.price_per_mt > (avg_price or 0) else "DOWN"
        })

    return {
        "status": "success",
        "location": location_obj.location_name,
        "count": len(results),
        "data": results
    }
