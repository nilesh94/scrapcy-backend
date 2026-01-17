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
# 1. GOOGLE SHEET SYNC (Bulk Upload)
# ==========================================

class SheetRow(BaseModel):
    Date: str              
    Time_Slot: str = "00:00" 
    SCRAP_TYPE: str        
    CATEGORY: str          
    Material: str          
    Grade: Optional[str] = None 
    Location: str          
    Price: float           
    Currency: str = "INR"  
    PER_UNIT: str = "MT"   

@router.post("/bulk-sheet-sync")
def sync_google_sheet(rows: List[SheetRow], db: Session = Depends(get_db)):
    """
    Receives raw rows from Google Sheets.
    Relies on DB Aliases (e.g., 'Mandi' -> 'Mandi Gobindgarh') and 
    exact DB matches for Materials/Grades.
    """
    try:
        # 1. Build Location Map
        loc_map = {}
        all_locations = db.query(Location).all()
        for loc in all_locations:
            if loc.location_name:
                loc_map[loc.location_name.strip().lower()] = loc.id
            if loc.city:
                loc_map[loc.city.strip().lower()] = loc.id
            if loc.search_aliases:
                aliases = [a.strip().lower() for a in loc.search_aliases.split(',') if a.strip()]
                for alias in aliases:
                    loc_map[alias] = loc.id

        # 2. Build Category/Material/Grade Maps
        cat_map = {c.material_category.strip().lower(): c.id for c in db.query(ScrapCategory).all()}
        mat_map = {m.material_name.strip().lower(): m.id for m in db.query(ScrapMaterial).all()}
        grade_map = {g.grade_name.strip().lower(): g.id for g in db.query(ScrapGrade).all()}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load reference data: {str(e)}")

    new_entries = []
    errors = []

    for i, row in enumerate(rows):
        try:
            raw_loc = row.Location.strip().lower()
            raw_cat = row.CATEGORY.strip().lower()
            raw_mat = row.Material.strip().lower()
            raw_grade = row.Grade.strip().lower() if row.Grade else None

            loc_id = loc_map.get(raw_loc)
            cat_id = cat_map.get(raw_cat)
            mat_id = mat_map.get(raw_mat)
            grade_id = grade_map.get(raw_grade) if raw_grade else None

            if not loc_id:
                errors.append(f"Row {i+1}: Location '{row.Location}' not found in DB (Check Aliases).")
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

            dt_str = f"{row.Date} {row.Time_Slot}"
            try:
                recorded_at = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
            except ValueError:
                try:
                    recorded_at = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    recorded_at = datetime.now()

            new_entries.append(ScrapPriceHistory(
                location_id=loc_id,
                category_id=cat_id,
                material_id=mat_id,
                grade_id=grade_id,
                price_per_mt=row.Price,         
                currency=row.Currency,          
                unit=row.PER_UNIT,              
                recorded_at=recorded_at
            ))

        except Exception as e:
            errors.append(f"Row {i+1}: processing error - {str(e)}")

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
    """
    
    if not location and not query_term:
        return {"status": "error", "message": "Please provide a location or a material name."}

    # --- A. Resolve Location (Optional) ---
    location_id = None
    location_name_display = "All Locations"

    if location:
        loc_search = location.strip().lower()
        location_obj = db.query(Location).filter(
            (func.lower(Location.location_name) == loc_search) |
            (func.lower(Location.city) == loc_search) |
            (func.lower(Location.search_aliases).like(f"%{loc_search}%"))
        ).first()

        if location_obj:
            location_id = location_obj.id
            location_name_display = location_obj.location_name
        else:
            return {"status": "error", "message": f"Location '{location}' not found."}

    # --- B. Resolve Material / Category (Optional) ---
    target_material_id = None
    target_category_id = None
    
    if query_term:
        term = query_term.strip().lower()
        mat_obj = db.query(ScrapMaterial).filter(
            (func.lower(ScrapMaterial.material_name) == term) | 
            (func.lower(ScrapMaterial.material_name).like(f"%{term}%"))
        ).first()
        
        if mat_obj:
            target_material_id = mat_obj.id
        else:
            cat_obj = db.query(ScrapCategory).filter(
                func.lower(ScrapCategory.material_category) == term
            ).first()
            if cat_obj:
                target_category_id = cat_obj.id
            else:
                return {"status": "error", "message": f"No material/category found for '{query_term}'"}

    # --- C. Build Query filters ---
    filters = []
    if location_id:
        filters.append(ScrapPriceHistory.location_id == location_id)
    if target_material_id:
        filters.append(ScrapPriceHistory.material_id == target_material_id)
    elif target_category_id:
        filters.append(ScrapPriceHistory.category_id == target_category_id)

    raw_history = db.query(ScrapPriceHistory).filter(*filters)\
        .order_by(ScrapPriceHistory.recorded_at.desc())\
        .limit(200).all()

    if not raw_history:
        return {"status": "no_data", "message": "No pricing data found."}

    # --- D. Find Latest Entry per Unique (Location + Material) ---
    latest_map = {} 
    for record in raw_history:
        key = f"{record.location_id}-{record.material_id}"
        if key not in latest_map:
            latest_map[key] = record

    results = []

    # --- E. Calculate Stats & Format ---
    for key, record in latest_map.items():
        loc_name = db.query(Location).get(record.location_id).location_name
        mat_name = db.query(ScrapMaterial).get(record.material_id).material_name
        grade_name = record.grade.grade_name if record.grade else "General"

        # -----------------------------------------------------------
        # ROBUST 5-DAY MOVING AVERAGE LOGIC
        # -----------------------------------------------------------
        # If data exists for 5 days, it averages 5 days.
        # If data exists for only 3 days (e.g. Mon, Wed, Fri), it averages those 3.
        # It automatically handles missing days without returning 0.
        # -----------------------------------------------------------
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

        results.append({
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

    return {
        "status": "success",
        "search_context": location_name_display,
        "count": len(results),
        "data": results
    }

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
