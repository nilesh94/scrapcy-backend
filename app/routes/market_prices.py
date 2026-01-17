from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
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

# ==========================================
# 0. PYDANTIC MODELS (Input Validation)
# ==========================================

class SheetRow(BaseModel):
    Date: str              
    Time_Slot: str = "00:00" 
    SCRAP_TYPE: str        
    CATEGORY: str          
    Material: str          
    Grade: Optional[str] = None 
    Location: str          
    Price: Optinal[float] = None           
    Currency: str = "INR"  
    PER_UNIT: str = "MT"   

# ==========================================
# 1. GOOGLE SHEET SYNC (With Duplicate Prevention)
# ==========================================

@router.post("/bulk-sheet-sync")
def sync_google_sheet(rows: List[SheetRow], db: Session = Depends(get_db)):
    """
    Receives raw rows from Google Sheets.
    - Maps names to IDs using Aliases.
    - PREVENTS DUPLICATES: Checks if (Location, Material, Grade, Time) exists.
    - If exists -> Updates Price (Upsert).
    - If new -> Inserts.
    """
    
    # --- A. Pre-fetch Maps (Optimization) ---
    try:
        # 1. Build Location Map
        loc_map = {}
        all_locations = db.query(Location).all()
        for loc in all_locations:
            if loc.location_name: loc_map[loc.location_name.strip().lower()] = loc.id
            if loc.city: loc_map[loc.city.strip().lower()] = loc.id
            if loc.search_aliases:
                aliases = [a.strip().lower() for a in loc.search_aliases.split(',') if a.strip()]
                for alias in aliases: loc_map[alias] = loc.id

        # 2. Build Category/Material/Grade Maps
        cat_map = {c.material_category.strip().lower(): c.id for c in db.query(ScrapCategory).all()}
        mat_map = {m.material_name.strip().lower(): m.id for m in db.query(ScrapMaterial).all()}
        grade_map = {g.grade_name.strip().lower(): g.id for g in db.query(ScrapGrade).all()}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load reference data: {str(e)}")

    processed_count = 0
    updated_count = 0
    inserted_count = 0
    skipped_row_count = 0
    errors = []

    # --- B. Loop through Rows ---
    for i, row in enumerate(rows):
        try:
            #--Skipping row when price is null
            if(row.Price is None):
                skipped_row_count += 1
                continue
            # Normalize Inputs
            raw_loc = row.Location.strip().lower()
            raw_cat = row.CATEGORY.strip().lower()
            raw_mat = row.Material.strip().lower()
            raw_grade = row.Grade.strip().lower() if row.Grade else None

            # Lookups
            loc_id = loc_map.get(raw_loc)
            cat_id = cat_map.get(raw_cat)
            mat_id = mat_map.get(raw_mat)
            grade_id = grade_map.get(raw_grade) if raw_grade else None

            # Validation
            if not loc_id:
                errors.append(f"Row {i+1}: Location '{row.Location}' not found in DB.")
                continue
            if not cat_id:
                errors.append(f"Row {i+1}: Category '{row.CATEGORY}' not found in DB.")
                continue
            if not mat_id:
                errors.append(f"Row {i+1}: Material '{row.Material}' not found in DB.")
                continue
            if raw_grade and not grade_id:
                 errors.append(f"Row {i+1}: Grade '{row.Grade}' not found in DB.")
                 continue

            # Parse Timestamp
            dt_str = f"{row.Date} {row.Time_Slot}"
            try:
                recorded_at = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
            except ValueError:
                try:
                    recorded_at = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    recorded_at = datetime.now()

            # --- C. UPSERT LOGIC (The Fix) ---
            # Check if this exact price record already exists
            existing_record = db.query(ScrapPriceHistory).filter(
                ScrapPriceHistory.location_id == loc_id,
                ScrapPriceHistory.material_id == mat_id,
                ScrapPriceHistory.grade_id == grade_id,
                ScrapPriceHistory.recorded_at == recorded_at
            ).first()

            if existing_record:
                # UPDATE existing record (No Duplicate)
                existing_record.price_per_mt = row.Price
                existing_record.currency = row.Currency
                existing_record.unit = row.PER_UNIT
                updated_count += 1
            else:
                # INSERT new record
                new_entry = ScrapPriceHistory(
                    location_id=loc_id,
                    category_id=cat_id,
                    material_id=mat_id,
                    grade_id=grade_id,
                    price_per_mt=row.Price,
                    currency=row.Currency,
                    unit=row.PER_UNIT,
                    recorded_at=recorded_at
                )
                db.add(new_entry)
                inserted_count += 1
            
            processed_count += 1

        except Exception as e:
            errors.append(f"Row {i+1}: processing error - {str(e)}")

    # --- D. Commit Changes ---
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        return {"status": "error", "detail": f"Database Commit Failed: {str(e)}", "errors": errors}

    return {
        "status": "success", 
        "processed": processed_count,
        "inserted": inserted_count,
        "updated": updated_count,
        "skipped_rows": skipped_row_count,
        "failed_count": len(errors),
        "errors": errors
    }


# ==========================================
# 2. UNIVERSAL SEARCH (For AI/WhatsApp)
# ==========================================

@router.get("/search")
def search_price(
    location: Optional[str] = None,
    query_term: Optional[str] = None, # Material OR Category
    db: Session = Depends(get_db)
):
    """
    Universal Search Logic with Robust Moving Average.
    FIXED: Uses Distinct Material Query to avoid getting buried by duplicates.
    """
    
    # --- A. Sanitize Inputs ---
    # Treat empty strings or "All" as None (Global Search)
    if location and location.strip().lower() in ["", "all locations", "all", "saare location", "everywhere", "sab jagah"]:
        location = None
        
    base_filters = []
    location_name_display = "All Locations"

    # --- B. Resolve Location (If specific city requested) ---
    if location:
        loc_search = location.strip().lower()
        location_obj = db.query(Location).filter(
            (func.lower(Location.location_name) == loc_search) |
            (func.lower(Location.city) == loc_search) |
            (func.lower(Location.search_aliases).like(f"%{loc_search}%"))
        ).first()

        if location_obj:
            # Add Location Filter
            base_filters.append(ScrapPriceHistory.location_id == location_obj.id)
            location_name_display = location_obj.location_name
        else:
            return {"status": "error", "message": f"Location '{location}' not found."}

    # --- C. Resolve Material (Fuzzy Match Logic) ---
    if query_term:
        term = query_term.strip().lower()
        
        # 1. Try Exact Match
        mat_obj = db.query(ScrapMaterial).filter(
            (func.lower(ScrapMaterial.material_name) == term) | 
            (func.lower(ScrapMaterial.material_name).like(f"%{term}%")) 
        ).first()
        
        # 2. Try Category Match (if no material found)
        if not mat_obj:
            cat_obj = db.query(ScrapCategory).filter(
                func.lower(ScrapCategory.material_category) == term
            ).first()
            if cat_obj:
                base_filters.append(ScrapPriceHistory.category_id == cat_obj.id)
        
        # 3. Fuzzy Fallback (Fix for "End Cutting Metal Scrap")
        # We check if the DB Name (e.g., "End Cutting") is inside the User Query
        if not mat_obj and 'cat_obj' not in locals():
            all_materials = db.query(ScrapMaterial).all()
            for m in all_materials:
                if m.material_name.lower() in term: 
                    mat_obj = m
                    break
        
        # Apply Material Filter
        if mat_obj:
            base_filters.append(ScrapPriceHistory.material_id == mat_obj.id)
        elif 'cat_obj' not in locals():
            return {"status": "error", "message": f"No material found for '{query_term}'"}

    # --- D. The "Show All" Fix ---
    # Query: "Get every unique (Material, Location) pair matching our filters"
    # This guarantees we get Mandi AND Raipur AND Alang
    distinct_pairs = db.query(
        ScrapPriceHistory.material_id, 
        ScrapPriceHistory.location_id
    ).filter(*base_filters).distinct().all()

    if not distinct_pairs:
         return {"status": "no_data", "message": "No pricing data found."}

    results = []

    # --- E. Loop Through Each Pair ---
    for mat_id, loc_id in distinct_pairs:
        # Get the latest price for THIS specific city + material
        latest_record = db.query(ScrapPriceHistory).filter(
            ScrapPriceHistory.material_id == mat_id,
            ScrapPriceHistory.location_id == loc_id
        ).order_by(ScrapPriceHistory.recorded_at.desc()).first()

        if latest_record:
            process_record(latest_record, db, results)

    return {
        "status": "success",
        "search_context": location_name_display,
        "count": len(results),
        "data": results
    }

# --- Helper Function for Processing Records ---
def process_record(record, db, results_list):
    """
    Helper to calculate 5-day average and format output.
    """
    loc_name = db.query(Location).get(record.location_id).location_name
    mat_name = db.query(ScrapMaterial).get(record.material_id).material_name
    grade_name = record.grade.grade_name if record.grade else "General"

    # 5-Day Avg Logic
    end_date = record.recorded_at
    start_date = end_date - timedelta(days=5)
    
    avg_price = db.query(func.avg(ScrapPriceHistory.price_per_mt)).filter(
        ScrapPriceHistory.location_id == record.location_id,
        ScrapPriceHistory.material_id == record.material_id,
        ScrapPriceHistory.recorded_at >= start_date,
        ScrapPriceHistory.recorded_at <= end_date
    ).scalar()
    
    avg_price_val = round(avg_price, 2) if avg_price else record.price_per_mt
    
    if record.price_per_mt > avg_price_val:
        trend = "HIGHER"
    elif record.price_per_mt < avg_price_val:
        trend = "LOWER"
    else:
        trend = "STABLE"

    results_list.append({
        "location": loc_name,
        "material": mat_name,
        "grade": grade_name,
        "price": record.price_per_mt,
        "unit": record.unit,
        "currency": record.currency,
        "date": record.recorded_at.strftime("%Y-%m-%d"),
        "avg_5d": avg_price_val,
        "trend_indicator": trend
    })

# ==========================================
# 3. ADMIN ENDPOINTS
# ==========================================

@router.post("/add", response_model=MarketPriceResponse)
def add_market_price(price_data: MarketPriceCreate, db: Session = Depends(get_db)):
    new_price = ScrapPriceHistory(
        category_id=price_data.category_id,
        material_id=price_data.material_id,
        grade_id=price_data.grade_id,
        location_id=price_data.location_id,
        price_per_mt=price_data.price_per_mt,
        recorded_at=price_data.recorded_at if price_data.recorded_at else func.now()
    )
    try:
        db.add(new_price)
        db.commit()
        db.refresh(new_price)
        return new_price
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save market price.")

@router.get("/history", response_model=List[MarketPriceResponse])
def get_price_history(limit: int = 50, db: Session = Depends(get_db)):
    prices = db.query(ScrapPriceHistory).order_by(ScrapPriceHistory.recorded_at.desc()).limit(limit).all()
    return prices
