"""
Auction Routes
API endpoints for auction management
All endpoints have RBAC placeholders (commented for testing)
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database.connection import get_db
from app.e_auction.services import AuctionService
from app.e_auction.schemas.auction import *
from app.e_auction.routes.auth_dependencies import (
    get_current_user_id,
    get_current_user,
    RequireAuth,
    RequireSeller,
    RequireAdmin,
    RequireL1Approver,
    RequireL2Approver
)

router = APIRouter(prefix="/api/v1/e-auction/auctions", tags=["Auctions"])


# ============================================================================
# PUBLIC ENDPOINTS (No auth required)
# ============================================================================

@router.get("/browse", response_model=AuctionListResponse)
async def browse_auctions(
    status: Optional[str] = None,
    category: Optional[str] = None,
    region: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Browse auctions (public - no auth required)
    Shows only LIVE auctions
    """
    filters = AuctionFilterParams(
        status=AuctionStatus.LIVE if not status else status,
        category=category,
        region=region,
        search=search
    )
    
    return AuctionService.list_auctions(
        db=db,
        filters=filters,
        page=page,
        page_size=page_size
    )


@router.get("/{auction_id}", response_model=AuctionDetailResponse)
async def get_auction_detail(
    auction_id: int,
    db: Session = Depends(get_db)
):
    """
    Get auction details (public)
    """
    auction = AuctionService.get_by_id(db, auction_id)
    # UPDATED: model_validate is the Pydantic V2 equivalent of from_orm
    return AuctionDetailResponse.model_validate(auction)


# ============================================================================
# AUTHENTICATED ENDPOINTS (Require login)
# ============================================================================

@router.get("", response_model=AuctionListResponse)
async def list_my_auctions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    # ==== RBAC: Requires authenticated user ====
    # current_user: dict = RequireAuth,  # Uncomment when auth ready
    current_user_id: int = Depends(get_current_user_id),  # Testing only
    db: Session = Depends(get_db)
):
    """
    List my auctions (seller's own auctions)
    
    RBAC: Requires authentication
    """
    filters = AuctionFilterParams(
        created_by_me=True,
        status=status
    )
    
    return AuctionService.list_auctions(
        db=db,
        filters=filters,
        page=page,
        page_size=page_size,
        user_id=current_user_id
    )


# ============================================================================
# SELLER ENDPOINTS (Create, Update, Delete)
# ============================================================================

@router.post("", response_model=AuctionDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_auction(
    auction_data: AuctionCreateRequest,
    # ==== RBAC: Only SELLER or ADMIN can create ====
    # current_user: dict = RequireSeller,  # Uncomment when auth ready
    current_user_id: int = Depends(get_current_user_id),  # Testing only
    db: Session = Depends(get_db)
):
    """
    Create new auction
    
    RBAC: Requires SELLER or ADMIN role
    """
    auction = AuctionService.create_auction(
        db=db,
        auction_data=auction_data,
        created_by_user_id=current_user_id
    )
    
    return AuctionDetailResponse.model_validate(auction)


@router.put("/{auction_id}", response_model=AuctionDetailResponse)
async def update_auction(
    auction_id: int,
    auction_data: AuctionUpdateRequest,
    # ==== RBAC: Only auction creator can update ====
    # current_user: dict = RequireAuth,  # Uncomment when auth ready
    current_user_id: int = Depends(get_current_user_id),  # Testing only
    db: Session = Depends(get_db)
):
    """
    Update auction
    
    RBAC: Only auction creator can update
    Service validates ownership
    """
    auction = AuctionService.update_auction(
        db=db,
        auction_id=auction_id,
        auction_data=auction_data,
        user_id=current_user_id
    )
    
    return AuctionDetailResponse.model_validate(auction)


@router.delete("/{auction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_auction(
    auction_id: int,
    # ==== RBAC: Only auction creator can delete ====
    # current_user: dict = RequireAuth,  # Uncomment when auth ready
    current_user_id: int = Depends(get_current_user_id),  # Testing only
    db: Session = Depends(get_db)
):
    """
    Delete auction (only DRAFT auctions)
    
    RBAC: Only auction creator can delete
    """
    AuctionService.delete_auction(
        db=db,
        auction_id=auction_id,
        user_id=current_user_id
    )
    
    return None


@router.post("/{auction_id}/submit-for-approval", response_model=AuctionActionResponse)
async def submit_auction_for_approval(
    auction_id: int,
    # ==== RBAC: Only auction creator ====
    # current_user: dict = RequireAuth,  # Uncomment when auth ready
    current_user_id: int = Depends(get_current_user_id),  # Testing only
    db: Session = Depends(get_db)
):
    """
    Submit auction for L1/L2 approval
    
    RBAC: Only auction creator
    """
    auction = AuctionService.submit_for_approval(
        db=db,
        auction_id=auction_id,
        user_id=current_user_id
    )
    
    return AuctionActionResponse(
        success=True,
        message="Auction submitted for approval",
        auction_id=auction.id,
        new_status=auction.status,
        new_approval_status=auction.approval_status
    )


@router.post("/{auction_id}/cancel", response_model=AuctionActionResponse)
async def cancel_auction(
    auction_id: int,
    request: CancelAuctionRequest,
    # ==== RBAC: Only auction creator or admin ====
    # current_user: dict = RequireAuth,  # Uncomment when auth ready
    current_user_id: int = Depends(get_current_user_id),  # Testing only
    db: Session = Depends(get_db)
):
    """
    Cancel auction
    
    RBAC: Only auction creator or ADMIN
    """
    auction = AuctionService.cancel_auction(
        db=db,
        auction_id=auction_id,
        user_id=current_user_id,
        reason=request.cancellation_reason
    )
    
    return AuctionActionResponse(
        success=True,
        message="Auction cancelled successfully",
        auction_id=auction.id,
        new_status=auction.status
    )


# ============================================================================
# ADMIN ENDPOINTS (Approval workflow)
# ============================================================================

@router.get("/admin/pending-approval", response_model=AuctionListResponse)
async def get_pending_auctions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    # ==== RBAC: Only L1/L2 approvers or admins ====
    # current_user: dict = RequireAdmin,  # Uncomment when auth ready
    db: Session = Depends(get_db)
):
    """
    Get auctions pending approval
    
    RBAC: Requires L1_APPROVER, L2_APPROVER, or ADMIN role
    """
    filters = AuctionFilterParams(
        status=AuctionStatus.PENDING_APPROVAL
    )
    
    return AuctionService.list_auctions(
        db=db,
        filters=filters,
        page=page,
        page_size=page_size
    )


@router.post("/{auction_id}/approve-l1", response_model=AuctionActionResponse)
async def approve_auction_l1(
    auction_id: int,
    request: AuctionApprovalRequest,
    # ==== RBAC: Only L1 approvers or admins ====
    # current_user: dict = RequireL1Approver,  # Uncomment when auth ready
    current_user_id: int = Depends(get_current_user_id),  # Testing only
    db: Session = Depends(get_db)
):
    """
    L1 approval for auction
    
    RBAC: Requires L1_APPROVER or ADMIN role
    """
    auction = AuctionService.approve_l1(
        db=db,
        auction_id=auction_id,
        approver_id=current_user_id,
        remarks=request.remarks,
        approve=request.approve
    )
    
    return AuctionActionResponse(
        success=True,
        message="L1 approval processed" if request.approve else "Auction rejected",
        auction_id=auction.id,
        new_approval_status=auction.approval_status
    )


@router.post("/{auction_id}/approve-l2", response_model=AuctionActionResponse)
async def approve_auction_l2(
    auction_id: int,
    request: AuctionApprovalRequest,
    # ==== RBAC: Only L2 approvers or admins ====
    # current_user: dict = RequireL2Approver,  # Uncomment when auth ready
    current_user_id: int = Depends(get_current_user_id),  # Testing only
    db: Session = Depends(get_db)
):
    """
    L2 approval for auction (final approval)
    
    RBAC: Requires L2_APPROVER or ADMIN role
    """
    auction = AuctionService.approve_l2(
        db=db,
        auction_id=auction_id,
        approver_id=current_user_id,
        remarks=request.remarks,
        approve=request.approve
    )
    
    return AuctionActionResponse(
        success=True,
        message="L2 approval processed - Auction scheduled" if request.approve else "Auction rejected",
        auction_id=auction.id,
        new_approval_status=auction.approval_status,
        new_status=auction.status
    )


@router.post("/{auction_id}/publish", response_model=AuctionActionResponse)
async def publish_auction_manually(
    auction_id: int,
    # ==== RBAC: Only admins ====
    # current_user: dict = RequireAdmin,  # Uncomment when auth ready
    current_user_id: int = Depends(get_current_user_id),  # Testing only
    db: Session = Depends(get_db)
):
    """
    Manually publish auction (make it LIVE)
    Usually done automatically by scheduler
    
    RBAC: Requires ADMIN role
    """
    auction = AuctionService.publish_auction(
        db=db,
        auction_id=auction_id
    )
    
    return AuctionActionResponse(
        success=True,
        message="Auction published successfully",
        auction_id=auction.id,
        new_status=auction.status
    )


# ============================================================================
# STATISTICS ENDPOINTS
# ============================================================================

@router.get("/stats/overview", response_model=AuctionStatsResponse)
async def get_auction_statistics(
    # ==== RBAC: Authenticated user for their stats ====
    # current_user: dict = RequireAuth,  # Uncomment when auth ready
    current_user_id: int = Depends(get_current_user_id),  # Testing only
    db: Session = Depends(get_db)
):
    """
    Get auction statistics for current user
    
    RBAC: Requires authentication
    """
    return AuctionService.get_auction_stats(db=db, user_id=current_user_id)


@router.get("/admin/stats/all", response_model=AuctionStatsResponse)
async def get_all_auction_statistics(
    # ==== RBAC: Only admins can see all stats ====
    # current_user: dict = RequireAdmin,  # Uncomment when auth ready
    db: Session = Depends(get_db)
):
    """
    Get all auction statistics (admin only)
    
    RBAC: Requires ADMIN role
    """
    return AuctionService.get_auction_stats(db=db)
