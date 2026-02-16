"""
Lots (Auction Items) Routes
API endpoints for managing individual auction lots
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.database.connection import get_db
from app.e_auction.models.auction_item import AuctionItem
from app.e_auction.models.auction import Auction
from app.e_auction.utils.enums import AuctionStatus, ApprovalStatus
from app.e_auction.routes.auth_dependencies import RequireAuth

router = APIRouter(prefix="/api/v1/e-auction/lots", tags=["Lots"])

# --- Schemas for Request/Response ---
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
        from_attributes = True

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/{lot_id}")
async def get_lot_details(
    lot_id: int,
    # RBAC: Authentication required to view full lot details (like reserve price)
    current_user: dict = Depends(RequireAuth),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific lot.
    
    RBAC Rules:
    - ADMIN: Can view any lot.
    - SELLER: Can view ONLY their own lots.
    - BUYER: Restricted (403 Forbidden).
    """
    # 1. Fetch Lot
    lot = db.query(AuctionItem).filter(AuctionItem.id == lot_id).first()
    if not lot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lot with ID {lot_id} not found"
        )

    # 2. Fetch Parent Auction for Permission Check
    auction = db.query(Auction).filter(Auction.id == lot.auction_id).first()
    if not auction:
        raise HTTPException(status_code=404, detail="Parent auction not found")

    # 3. RBAC Check (Fixed: Access attributes via dot notation)
    # RequireAuth returns a User object, not a dict
    user_id = current_user.id
    user_role = current_user.role

    if user_role != "admin":
        # Check ownership
        if auction.created_by != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view details for this lot."
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
    - SELLER: Can edit ONLY if they created the parent auction AND it is DRAFT/REJECTED.
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

    # 3. RBAC & Status Check (Fixed: Access attributes via dot notation)
    user_id = current_user.id 
    user_role = current_user.role

    if user_role != "admin":
        # Check ownership
        if auction.created_by != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to edit this lot."
            )
        
        # Check Auction Status using Enums
        # Allow edits only if DRAFT or REJECTED
        allowed_statuses = [AuctionStatus.DRAFT, AuctionStatus.REJECTED]
        
        # Or alternatively check forbidden statuses (Approved/Live)
        locked_approval_statuses = [ApprovalStatus.L1_APPROVED, ApprovalStatus.L2_APPROVED]
        
        if (auction.status not in allowed_statuses) or \
           (auction.approval_status in locked_approval_statuses) or \
           (auction.status == AuctionStatus.LIVE):
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Cannot update lot unless parent auction is in DRAFT or REJECTED state."
            )

    # 4. Apply Updates
    update_data = lot_data.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        if hasattr(lot, key): # Safety check
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
