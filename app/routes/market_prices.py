from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List
from app.database.connection import get_db
from app.models.market_data import ScrapPriceHistory
from app.schemas.market_data import MarketPriceCreate, MarketPriceResponse

router = APIRouter(
    prefix="/market-prices",
    tags=["Market Prices"]
)

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

@router.get("/history", response_model=List[MarketPriceResponse])
def get_price_history(limit: int = 50, db: Session = Depends(get_db)):
    """
    Fetch latest prices (Optional for Admin View)
    """
    prices = db.query(ScrapPriceHistory).order_by(ScrapPriceHistory.recorded_at.desc()).limit(limit).all()
    return prices
