"""
Lots (Auction Items) Routes
API endpoints for managing individual auction lots
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from pydantic import BaseModel

from app.database.connection import get_db
from app.e_auction.models.auction_item import AuctionItem
from app.e_auction.models.auction import Auction # Assuming Auction model exists for permission check
from app.e_auction.routes.auth_dependencies import RequireAuth

router = APIRouter(prefix="/api/v1/e-auction/lots", tags=["Lots"])

# --- Schemas for Request/Response (Simple inline definition for focus) ---
# ideally these would be in app/e_auction/schemas/auction_item.py

class LotUpdateRequest(BaseModel):
    item_name: Optional[str] = None
    item_type: Optional[str] = None
    lot_number: Optional[str] = None
    scrap_type: Optional[str] = None
    category: Optional[str] = None
    material: Optional[str] = None
    grade: Optional[str] = None
    form: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    location_city: Optional[str] = None
    location_state: Optional[str] = None
    location_address: Optional[str] = None
    pickup_conditions: Optional[str] = None
    starting_bid_amount: Optional[float] = None
    reserve_price: Optional[float] = None
    min_increment_amount: Optional[float] = None
    buy_now_price: Optional[float] = None
    seller_notes: Optional[str] = None
    condition_rating: Optional[int] = None

    class Config:
        orm_mode = True

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/{lot_id}")
async def get_lot_details(
    lot_id: int,
    db: Session = Depends(get_db)
):
    """
    Get details of a specific lot
    """
    lot = db.query(AuctionItem).filter(AuctionItem.id == lot_id).first()
    if not lot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lot with ID {lot_id} not found"
        )
    return lot


@router.put("/{lot_id}")
async def update_lot(
    lot_id: int,
    lot_data: LotUpdateRequest,
    current_user: dict = Depends(RequireAuth),
    db: Session = Depends(get_db)
):
    """
    Update a specific lot details.
    
    RBAC Rules:
    - ADMIN: Can edit any lot.
    - SELLER: Can edit ONLY if they created the parent auction AND it is not yet approved/live.
    """
    # 1. Fetch Lot
    lot = db.query(AuctionItem).filter(AuctionItem.id == lot_id).first()
    if not lot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Lot not found"
        )

    # 2. Fetch Parent Auction for Permission Check
    auction = db.query(Auction).filter(Auction.id == lot.auction_id).first()
    if not auction:
        raise HTTPException(status_code=404, detail="Parent auction not found")

    # 3. RBAC & Status Check
    user_id = current_user.id if hasattr(current_user, 'id') else current_user.get('id')
    user_role = current_user.role if hasattr(current_user, 'role') else current_user.get('role')

    if user_role != "admin":
        # Check ownership
        if auction.created_by != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to edit this lot."
            )
        
        # Check Auction Status (Lock editing if approved or live)
        # Assuming approval_status values: PENDING, L1_APPROVED, L2_APPROVED, REJECTED
        locked_statuses = ["L1_APPROVED", "L2_APPROVED"] 
        if auction.approval_status in locked_statuses or auction.status == "LIVE":
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Cannot edit lot: Auction is already approved or live."
            )

    # 4. Apply Updates
    update_data = lot_data.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(lot, key, value)

    try:
        db.commit()
        db.refresh(lot)
        return lot
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update lot: {str(e)}"
        )
