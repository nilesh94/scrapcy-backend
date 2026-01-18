from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
from pydantic import BaseModel, field_validator

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
    
    # Allow float OR None. 
    Price: Optional[Union[float, None]] = None           
    
    Currency: str = "INR"  
    PER_UNIT: str = "MT"   

    # --- VALIDATOR: FIX THE "STRING AS NUMBER" ERROR ---
    @field_validator('Price', mode='before')
    @classmethod
    def parse_price(cls, v):
        # 1. Handle actual Nulls
        if v is None:
            return None
        
        # 2. Handle Strings (Empty or Numbers in quotes)
        if isinstance(v, str):
            v = v.strip()
            if not v:  # Empty string "" becomes None
                return None
            try:
                # Clean commas just in case ("35,000" -> 35000.0)
                return float(v.replace(',', ''))
            except ValueError:
                # If it's garbage text, treat as None so we skip it
                return None
                
        return v

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
            # -- Skipping row when price is null (Handled by validator above)
            if row.Price is None:
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

            # --- C. UPSERT LOGIC ---
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
# 2. PARAMETER-BASED SEARCH
# ==========================================

@router.get("/search")
def search_price(
    location: Optional[str] = None,
    category: Optional[str] = None,
    material: Optional[str] = None,
    grade: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Parametric Search:
    - Filters by Location AND Category AND Material AND Grade.
    - Groups results by (Location + Material + Grade).
    - Returns the LATEST price for each unique group found.
    - Includes 5-Day Moving Average in response.
    """
    
    filters = []
    search_context_parts = []

    # 1. Location Filter
    # Treat empty/generic strings as None (no filter)
    if location and location.strip().lower() not in ["", "all", "all locations", "saare location", "everywhere", "sab jagah"]:
        loc_search = location.strip().lower()
        loc_obj = db.query(Location).filter(
            (func.lower(Location.location_name) == loc_search) |
            (func.lower(Location.city) == loc_search) |
            (func.lower(Location.search_aliases).like(f"%{loc_search}%"))
        ).first()

        if loc_obj:
            filters.append(ScrapPriceHistory.location_id == loc_obj.id)
            search_context_parts.append(f"Location: {loc_obj.location_name}")
        else:
            return {"status": "error", "message": f"Location '{location}' not found."}

    # 2. Category Filter
    if category:
        cat_term = category.strip().lower()
        cat_obj = db.query(ScrapCategory).filter(
            func.lower(ScrapCategory.material_category) == cat_term
        ).first()

        if cat_obj:
            filters.append(ScrapPriceHistory.category_id == cat_obj.id)
            search_context_parts.append(f"Category: {cat_obj.material_category}")
        else:
            return {"status": "error", "message": f"Category '{category}' not found."}

    # 3. Material Filter
    if material:
        mat_term = material.strip().lower()
        mat_obj = db.query(ScrapMaterial).filter(
            (func.lower(ScrapMaterial.material_name) == mat_term) |
            (func.lower(ScrapMaterial.material_name).like(f"%{mat_term}%"))
        ).first()

        if mat_obj:
            filters.append(ScrapPriceHistory.material_id == mat_obj.id)
            search_context_parts.append(f"Material: {mat_obj.material_name}")
        else:
            return {"status": "error", "message": f"Material '{material}' not found."}

    # 4. Grade Filter
    if grade:
        grade_term = grade.strip().lower()
        grade_obj = db.query(ScrapGrade).filter(
            func.lower(ScrapGrade.grade_name) == grade_term
        ).first()

        if grade_obj:
            filters.append(ScrapPriceHistory.grade_id == grade_obj.id)
            search_context_parts.append(f"Grade: {grade_obj.grade_name}")
        else:
            return {"status": "error", "message": f"Grade '{grade}' not found."}

    # --- FETCH DISTINCT GROUPS ---
    # We want the latest price for every distinct combination of:
    # Location + Material + Grade
    # This ensures that "Ship Breaking" returns separate rows for "Attachment" and "Tukdi"
    
    distinct_groups = db.query(
        ScrapPriceHistory.location_id,
        ScrapPriceHistory.material_id,
        ScrapPriceHistory.grade_id
    ).filter(*filters).distinct().all()

    if not distinct_groups:
         return {"status": "no_data", "message": "No pricing data found for these filters."}

    results = []

    # --- LOOP AND GET LATEST PRICE ---
    for loc_id, mat_id, grade_id in distinct_groups:
        
        # Build filter for this specific group
        group_filters = [
            ScrapPriceHistory.location_id == loc_id,
            ScrapPriceHistory.material_id == mat_id,
            ScrapPriceHistory.grade_id == grade_id
        ]
        
        # Query latest record
        latest_record = db.query(ScrapPriceHistory).filter(*group_filters)\
            .order_by(ScrapPriceHistory.recorded_at.desc())\
            .first()

        if latest_record:
            process_record(latest_record, db, results)

    context_str = " | ".join(search_context_parts) if search_context_parts else "Global Search"

    return {
        "status": "success",
        "search_context": context_str,
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
        ScrapPriceHistory.grade_id == record.grade_id, # Ensure we avg same Grade too
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
