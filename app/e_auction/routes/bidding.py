"""
Bidding Routes
API endpoints for bidding operations
All endpoints have RBAC placeholders (commented for testing)
"""
from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database.connection import get_db
from app.e_auction.services import BiddingService
from app.e_auction.schemas.bid import *
from app.e_auction.routes.auth_dependencies import (
    get_current_user_id,
    RequireAuth,
    RequireBuyer
)
from app.e_auction.websockets.bid_handler import broadcast_bid_placed, broadcast_outbid, broadcast_extension

router = APIRouter(prefix="/api/v1/e-auction/bidding", tags=["Bidding"])


# ============================================================================
# PUBLIC ENDPOINTS (View bid history)
# ============================================================================

@router.get("/lots/{lot_id}/history", response_model=List[BidResponse])
async def get_lot_bid_history(
    lot_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get bid history for a lot (public)
    Shows all bids in descending order
    """
    bids = BiddingService.get_bid_history(
        db=db,
        auction_item_id=lot_id,
        page=page,
        page_size=page_size
    )
    
    # UPDATED: model_validate for Pydantic V2
    return [BidResponse.model_validate(bid) for bid in bids]


# ============================================================================
# BUYER ENDPOINTS (Place bids)
# ============================================================================

@router.post("/lots/{lot_id}/bid", response_model=BidSuccessResponse)
async def place_bid(
    lot_id: int,
    bid_request: PlaceBidRequest,
    request: Request,
    # ==== RBAC: Only BUYER or ADMIN can bid ====
    current_user: dict = Depends(RequireBuyer),
    db: Session = Depends(get_db)
):
    """
    Place a bid on a lot
    
    RBAC: Requires BUYER or ADMIN role
    
    Validations:
    - User must be registered for auction
    - Lot must be LIVE
    - Bid amount must meet minimum requirements
    - Seller cannot bid on own lot
    """
    # Get IP address
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    
    # Get ID from model attribute or dict key
    user_id = getattr(current_user, "id", None) or current_user.get("id")

    # Capture the lot and current winner before the new bid for broadcast logic
    from app.e_auction.models import AuctionItem
    lot_before = db.query(AuctionItem).filter(AuctionItem.id == lot_id).first()
    old_winner_id = lot_before.winner_user_id if lot_before else None

    bid = BiddingService.place_bid(
        db=db,
        auction_item_id=lot_id,
        user_id=user_id,
        bid_amount=bid_request.bid_amount,
        ip_address=ip_address,
        device_info=user_agent
    )
    
    # Get lot for updated metadata
    lot = db.query(AuctionItem).filter(AuctionItem.id == lot_id).first()
    
    # REAL-TIME BROADCAST: Notify all watchers of new high bid
    await broadcast_bid_placed(
        lot_id=lot_id,
        bid_id=bid.id,
        bid_amount=float(bid.bid_amount),
        bidder_user_id=user_id,
        total_bids=lot.total_bids_count or 0,
        unique_bidders=lot.unique_bidders_count or 0
    )

    # SURGICAL DYNAMIC UPDATE: Uses exact duration from DB config
    if getattr(bid, 'is_extended', False):
        ext_mins = getattr(bid, 'extension_minutes', 0)
        if ext_mins > 0:
            await broadcast_extension(lot_id=lot_id, extension_minutes=ext_mins)

    # REAL-TIME NOTIFICATION: Specifically notify the person who was just outbid
    if old_winner_id and old_winner_id != user_id:
        await broadcast_outbid(
            lot_id=lot_id,
            outbid_user_id=old_winner_id,
            new_highest_bid=float(bid.bid_amount)
        )

    return BidSuccessResponse(
        success=True,
        message="Bid placed successfully",
        bid_id=bid.id,
        bid_amount=bid.bid_amount,
        is_winning=bool(bid.is_winning_bid),
        previous_highest_bid=lot.highest_bid_amount if lot else None,
        min_next_bid=lot.min_next_bid if lot else bid.bid_amount
    )


@router.post("/lots/{lot_id}/auto-bid", response_model=AutoBidSuccessResponse)
async def create_auto_bid(
    lot_id: int,
    auto_bid_request: AutoBidCreateRequest,
    # ==== RBAC: Only BUYER or ADMIN ====
    current_user: dict = Depends(RequireBuyer),
    db: Session = Depends(get_db)
):
    """
    Create auto-bid (proxy bidding)
    
    RBAC: Requires BUYER or ADMIN role
    
    System will automatically bid up to max_bid_amount
    """
    # Get ID from model attribute or dict key
    user_id = getattr(current_user, "id", None) or current_user.get("id")

    auto_bid = BiddingService.create_auto_bid(
        db=db,
        auction_item_id=lot_id,
        user_id=user_id,
        max_bid_amount=auto_bid_request.max_bid_amount
    )
    
    # Get current highest bid
    from app.e_auction.models import AuctionItem
    lot = db.query(AuctionItem).filter(AuctionItem.id == lot_id).first()
    
    return AutoBidSuccessResponse(
        success=True,
        message="Auto-bid activated successfully",
        auto_bid_id=auto_bid.id,
        max_bid_amount=auto_bid.max_bid_amount,
        current_highest_bid=lot.highest_bid_amount if lot else None
    )


@router.put("/auto-bids/{auto_bid_id}", response_model=AutoBidSuccessResponse)
async def update_auto_bid(
    auto_bid_id: int,
    update_request: AutoBidUpdateRequest,
    # ==== RBAC: Only bid owner ====
    current_user: dict = Depends(RequireAuth),
    db: Session = Depends(get_db)
):
    """
    Update auto-bid max amount
    
    RBAC: Only auto-bid owner can update
    """
    from app.e_auction.models import AutoBid, AuctionItem
    
    # Get ID from model attribute or dict key
    user_id = getattr(current_user, "id", None) or current_user.get("id")

    auto_bid = db.query(AutoBid).filter(AutoBid.id == auto_bid_id).first()
    if not auto_bid:
        raise HTTPException(status_code=404, detail="Auto-bid not found")
    
    # Verify ownership
    if auto_bid.user_id != user_id:
         raise HTTPException(status_code=403, detail="Not authorized")
    
    auto_bid.max_bid_amount = update_request.max_bid_amount
    db.commit()
    db.refresh(auto_bid)
    
    lot = db.query(AuctionItem).filter(AuctionItem.id == auto_bid.auction_item_id).first()
    
    return AutoBidSuccessResponse(
        success=True,
        message="Auto-bid updated successfully",
        auto_bid_id=auto_bid.id,
        max_bid_amount=auto_bid.max_bid_amount,
        current_highest_bid=lot.highest_bid_amount if lot else None
    )


@router.delete("/auto-bids/{auto_bid_id}", status_code=204)
async def cancel_auto_bid(
    auto_bid_id: int,
    # ==== RBAC: Only bid owner ====
    current_user: dict = Depends(RequireAuth),
    db: Session = Depends(get_db)
):
    """
    Cancel auto-bid
    
    RBAC: Only auto-bid owner can cancel
    """
    from app.e_auction.models import AutoBid
    from app.e_auction.utils.enums import AutoBidStatus
    
    # Get ID from model attribute or dict key
    user_id = getattr(current_user, "id", None) or current_user.get("id")

    auto_bid = db.query(AutoBid).filter(AutoBid.id == auto_bid_id).first()
    if not auto_bid:
        raise HTTPException(status_code=404, detail="Auto-bid not found")
    
    # Verify ownership
    if auto_bid.user_id != user_id:
         raise HTTPException(status_code=403, detail="Not authorized")
    
    auto_bid.status = AutoBidStatus.CANCELLED
    db.commit()
    
    return None


# ============================================================================
# USER BID MANAGEMENT
# ============================================================================

@router.get("/my-bids", response_model=MyBidsResponse)
async def get_my_bids(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    # ==== RBAC: Authenticated user ====
    current_user: dict = Depends(RequireAuth),
    db: Session = Depends(get_db)
):
    """
    Get my bids with statistics
    
    RBAC: Requires authentication
    """
    # Get ID from model attribute or dict key
    user_id = getattr(current_user, "id", None) or current_user.get("id")

    return BiddingService.get_my_bids(
        db=db,
        user_id=user_id,
        page=page,
        page_size=page_size
    )


@router.get("/my-auto-bids", response_model=AutoBidListResponse)
async def get_my_auto_bids(
    # ==== RBAC: Authenticated user ====
    current_user: dict = Depends(RequireAuth),
    db: Session = Depends(get_db)
):
    """
    Get my active auto-bids
    
    RBAC: Requires authentication
    """
    from app.e_auction.models import AutoBid
    from sqlalchemy import and_
    
    # Get ID from model attribute or dict key
    user_id = getattr(current_user, "id", None) or current_user.get("id")

    auto_bids = db.query(AutoBid).filter(
        and_(
            AutoBid.user_id == user_id,
            AutoBid.status == "ACTIVE"
        )
    ).all()
    
    return AutoBidListResponse(
        total=len(auto_bids),
        active_count=len(auto_bids),
        auto_bids=[AutoBidResponse.model_validate(ab) for ab in auto_bids]
    )


@router.get("/lots/{lot_id}/my-bid-summary", response_model=LotBidSummary)
async def get_lot_bid_summary(
    lot_id: int,
    # ==== RBAC: Authenticated user ====
    current_user: dict = Depends(RequireAuth),
    db: Session = Depends(get_db)
):
    """
    Get bid summary for a specific lot (user's participation)
    
    RBAC: Requires authentication
    """
    from app.e_auction.models import AuctionItem, Bid, AutoBid
    from sqlalchemy import func, and_
    
    # Get ID from model attribute or dict key
    user_id = getattr(current_user, "id", None) or current_user.get("id")

    lot = db.query(AuctionItem).filter(AuctionItem.id == lot_id).first()
    if not lot:
        raise HTTPException(status_code=404, detail="Lot not found")
    
    # User's highest bid
    user_highest = db.query(func.max(Bid.bid_amount)).filter(
        and_(Bid.auction_item_id == lot_id, Bid.user_id == user_id)
    ).scalar()
    
    # Check if user is winning
    is_winning = lot.winner_user_id == user_id if lot.winner_user_id else False
    
    # Check if has auto-bid
    has_auto_bid = db.query(AutoBid).filter(
        and_(
            AutoBid.auction_item_id == lot_id,
            AutoBid.user_id == user_id,
            AutoBid.status == "ACTIVE"
        )
    ).first() is not None
    
    return LotBidSummary(
        auction_item_id=lot.id,
        item_name=lot.item_name,
        total_bids=lot.total_bids_count or 0,
        unique_bidders=lot.unique_bidders_count or 0,
        starting_bid=lot.starting_bid_amount,
        current_highest_bid=lot.highest_bid_amount,
        reserve_price=lot.reserve_price,
        last_bid_time=lot.last_bid_time,
        user_has_bid=user_highest is not None,
        user_highest_bid=user_highest,
        user_is_winning=is_winning,
        user_has_auto_bid=has_auto_bid
    )


@router.get("/stats/my-bidding", response_model=BidStatsResponse)
async def get_my_bidding_stats(
    # ==== RBAC: Authenticated user ====
    current_user: dict = Depends(RequireAuth),
    db: Session = Depends(get_db)
):
    """
    Get bidding statistics for current user
    
    RBAC: Requires authentication
    """
    from app.e_auction.models import Bid, AutoBid
    from sqlalchemy import func, and_
    from decimal import Decimal
    
    # Get ID from model attribute or dict key
    user_id = getattr(current_user, "id", None) or current_user.get("id")

    # Total bids
    total_bids = db.query(func.count(Bid.id)).filter(Bid.user_id == user_id).scalar()
    
    # Total amount bid
    total_amount = db.query(func.sum(Bid.bid_amount)).filter(
        Bid.user_id == user_id
    ).scalar() or Decimal('0.00')
    
    # Active bids (winning)
    active_bids = db.query(func.count(Bid.id)).filter(
        and_(Bid.user_id == user_id, Bid.is_winning_bid == 1)
    ).scalar()
    
    # Active auto-bids
    active_auto_bids = db.query(func.count(AutoBid.id)).filter(
        and_(AutoBid.user_id == user_id, AutoBid.status == "ACTIVE")
    ).scalar()
    
    return BidStatsResponse(
        total_bids_placed=total_bids or 0,
        total_amount_bid=total_amount,
        active_bids=active_bids or 0,
        won_auctions=0,  # Calculate from closed lots
        lost_auctions=0,
        active_auto_bids=active_auto_bids or 0,
        auto_bids_triggered=0,
        win_rate=0.0
    )
