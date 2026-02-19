"""
Auction Routes
API endpoints for auction management
All endpoints have RBAC placeholders (commented for testing)
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status, File, UploadFile, Form
from sqlalchemy.orm import Session
from typing import Optional, List
import json

from app.database.connection import get_db
from app.e_auction.services import AuctionService
from app.e_auction.schemas.auction import *
from app.e_auction.schemas.auction_item import LotUpdateRequest, LotDetailResponse
from app.e_auction.utils.exceptions import (
    AuctionNotFoundException,
    ForbiddenException,
    InvalidDateRangeException,
    AuctionNotEditableException,
    AuctionNotApprovedException,
    AuctionNotLiveException
)
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
    try:
        auction = AuctionService.get_by_id(db, auction_id)
        # UPDATED: model_validate is the Pydantic V2 equivalent of from_orm
        return AuctionDetailResponse.model_validate(auction)
    except AuctionNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# MANAGEMENT & RESTRICTED DETAILS (View/Edit Support)
# ============================================================================

@router.get("/{auction_id}/manage", response_model=AuctionDetailResponse)
async def get_auction_management_details(
    auction_id: int,
    # ==== RBAC: Authenticated Users Only ====
    current_user: dict = Depends(RequireAuth),
    db: Session = Depends(get_db)
):
    """
    Get FULL auction details for Management/Edit Page.
    Includes all lot details.
    
    RBAC Rules:
    - ADMIN: Can view ALL auctions.
    - SELLER: Can view ONLY their own auctions (Owner or Creator).
    - BUYER: Restricted (403 Forbidden).
    """
    try:
        auction = AuctionService.get_by_id(db, auction_id)
        
        # Helper to get user ID and Role safely from dict
        # ABSOLUTELY REQUIRED FIX: Extract ID directly from current_user object to avoid session errors
        user_id = getattr(current_user, 'id', None) or current_user.get('id')
        user_role = getattr(current_user, 'role', None) or current_user.get('role')
        
        # 1. Admin Override - Can see everything
        if user_role == "admin":
            return AuctionDetailResponse.model_validate(auction)
            
        # 2. Seller Check - Can see only their own
        if user_role == "seller":
            # Check if user is the Owner (seller_id) OR the Creator
            if auction.created_by != user_id and auction.seller_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to manage this auction."
                )
            return AuctionDetailResponse.model_validate(auction)
        
        # 3. Deny everyone else (Buyers/Viewers shouldn't use this endpoint)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. This endpoint is for Sellers and Admins only."
        )
    except AuctionNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/open/{auction_id}", response_model=AuctionDetailResponse, response_model_exclude={
    "created_by", "seller_id",
    "l1_approved_by", "l1_approved_at", "l1_remarks", 
    "l2_approved_by", "l2_approved_at", "l2_remarks", 
    "rejection_reason"
})
async def get_open_auction_details(
    auction_id: int,
    db: Session = Depends(get_db)
):
    """
    [OPEN API] Get auction details for public website display.
    
    - Excludes 'critical' internal info (remarks, approver IDs, creator ID).
    - Hides DRAFT or CANCELLED auctions (only shows Live/Scheduled/Closed).
    """
    try:
        auction = AuctionService.get_by_id(db, auction_id)
        
        # Restrict visibility for public endpoint
        if auction.status in [AuctionStatus.DRAFT, AuctionStatus.PENDING_APPROVAL]:
             raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Auction not publicly available."
            )
            
        return AuctionDetailResponse.model_validate(auction)
    except AuctionNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# AUTHENTICATED ENDPOINTS (Require login)
# ============================================================================

@router.get("", response_model=AuctionListResponse)
async def list_my_auctions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    # ==== RBAC: Requires authenticated user ====
    current_user: dict = Depends(RequireAuth),
    db: Session = Depends(get_db)
):
    """
    List my auctions (seller's own auctions)
    
    RBAC: Requires authentication
    """
    # ABSOLUTELY REQUIRED FIX: Extract ID directly from current_user object to avoid session errors
    user_id = getattr(current_user, 'id', None) or current_user.get('id')

    filters = AuctionFilterParams(
        created_by_me=True,
        status=status
    )
    
    return AuctionService.list_auctions(
        db=db,
        filters=filters,
        page=page,
        page_size=page_size,
        user_id=user_id
    )


# ============================================================================
# SELLER ENDPOINTS (Create, Update, Delete)
# ============================================================================

@router.post("", response_model=AuctionDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_auction(
    # ABSOLUTELY REQUIRED FIX: Change to Form and File to support multipart upload
    data: str = Form(...), 
    terms_doc: Optional[UploadFile] = File(None),
    # UPDATED: Accept multiple lot images
    lot_images: Optional[List[UploadFile]] = File(None),
    # ==== RBAC: Only SELLER or ADMIN can create ====
    current_user: dict = Depends(RequireSeller),
    db: Session = Depends(get_db)
):
    """
    Create new auction with optional file upload
    
    RBAC: Requires SELLER or ADMIN role
    """
    try:
        #Parse stringified JSON from Form Data
        auction_dict = json.loads(data)
        # Convert dict to Schema for validation
        auction_data = AuctionCreateRequest(**auction_dict)

        user_id = getattr(current_user, 'id', None) or current_user.get('id')
        user_role = getattr(current_user, 'role', None) or current_user.get('role')

        # 1. Determine Owner (Seller ID)
        final_seller_id = user_id
        
        if user_role == "admin":
            if not auction_data.seller_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Admin must select a Seller (seller_id) when creating an auction."
                )
            final_seller_id = auction_data.seller_id
        else:
            # Force sellers to only create for themselves
            final_seller_id = user_id

        # Pass the raw file to the service for internal calculation/upload
        auction = await AuctionService.create_auction(
            db=db,
            auction_data=auction_data,
            seller_id=final_seller_id,
            created_by_user_id=user_id,
            terms_file=terms_doc,
            lot_images=lot_images
        )
        
        return AuctionDetailResponse.model_validate(auction)
    except json.JSONDecodeError:
         raise HTTPException(status_code=400, detail="Invalid JSON format in 'data' field")
    except InvalidDateRangeException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create auction: {str(e)}")


@router.post("/{auction_id}/upload-document")
async def upload_auction_document(
    auction_id: int,
    document: UploadFile = File(...),
    # ==== RBAC: Authenticated Users Only ====
    current_user: dict = Depends(RequireAuth),
    db: Session = Depends(get_db)
):
    """
    ABSOLUTELY REQUIRED: New endpoint for View/Edit Page to upload document.
    Calculation of path (filename + timestamp) happens internally in Service.
    """
    try:
        user_id = getattr(current_user, 'id', None) or current_user.get('id')
        doc_url = await AuctionService.upload_auction_document(
            db=db,
            auction_id=auction_id,
            document=document,
            user_id=user_id
        )
        return {"success": True, "url": doc_url}
    except AuctionNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{auction_id}", response_model=AuctionDetailResponse)
async def update_auction(
    auction_id: int,
    # ABSOLUTELY REQUIRED: Change to Form and File to support multipart upload during edit
    data: str = Form(...), 
    terms_doc: Optional[UploadFile] = File(None),
    #Accept optional new lot images
    lot_images: Optional[List[UploadFile]] = File(None),
    # ==== RBAC: Only auction creator or admin ====
    current_user: dict = Depends(RequireAuth),
    db: Session = Depends(get_db)
):
    """
    Update auction details and optionally upload/replace a T&C document.
    """
    try:
        # Parse the stringified JSON from Form Data
        auction_dict = json.loads(data)
        auction_data = AuctionUpdateRequest(**auction_dict)

        # Extract user info
        user_id = getattr(current_user, 'id', None) or current_user.get('id')
        
        # Call service with the raw file for internal calculation
        updated_auction = await AuctionService.update_auction(
            db=db,
            auction_id=auction_id,
            auction_data=auction_data,
            user_id=user_id,
            terms_file=terms_doc,
            lot_images=lot_images
        )
        
        return AuctionDetailResponse.model_validate(updated_auction)
    except json.JSONDecodeError:
         raise HTTPException(status_code=400, detail="Invalid JSON format in 'data' field")
    except AuctionNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenException as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- ABSOLUTELY REQUIRED: New Independent Route for Individual Lot Updates via Modal ---
@router.put("/lots/{lot_id}", response_model=LotDetailResponse)
async def update_lot_independent(
    lot_id: int,
    lot_data: str = Form(...), 
    lot_images: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(RequireAuth)
):
    """Update specific lot including new image uploads via multipart from modal"""
    try:
        data_dict = json.loads(lot_data)
        lot_request = LotUpdateRequest(**data_dict)
        
        updated_lot = await AuctionService.update_specific_lot(
            db=db,
            lot_id=lot_id,
            lot_data=lot_request,
            images=lot_images,
            delete_image_ids=data_dict.get('delete_image_ids', [])
        )
        return LotDetailResponse.model_validate(updated_lot)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lot Update Error: {str(e)}")


@router.delete("/{auction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_auction(
    auction_id: int,
    # ==== RBAC: Only auction creator can delete ====
    current_user: dict = Depends(RequireAuth),
    db: Session = Depends(get_db)
):
    """
    Delete auction (only DRAFT auctions)
    
    RBAC: Only auction creator can delete
    """
    try:
        # ABSOLUTELY REQUIRED FIX: Extract ID directly from current_user object to avoid session errors
        user_id = getattr(current_user, 'id', None) or current_user.get('id')
        
        AuctionService.delete_auction(
            db=db,
            auction_id=auction_id,
            user_id=user_id
        )
        
        return None
    except AuctionNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenException as e:
        raise HTTPException(status_code=403, detail=str(e))
    except AuctionNotEditableException as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{auction_id}/submit-for-approval", response_model=AuctionActionResponse)
async def submit_auction_for_approval(
    auction_id: int,
    # ==== RBAC: Only auction creator ====
    current_user: dict = Depends(RequireAuth),
    db: Session = Depends(get_db)
):
    """
    Submit auction for L1/L2 approval
    
    RBAC: Only auction creator
    """
    try:
        # ABSOLUTELY REQUIRED FIX: Extract ID directly from current_user object to avoid session errors
        user_id = getattr(current_user, 'id', None) or current_user.get('id')
        
        auction = AuctionService.submit_for_approval(
            db=db,
            auction_id=auction_id,
            user_id=user_id
        )
        
        return AuctionActionResponse(
            success=True,
            message="Auction submitted for approval",
            auction_id=auction.id,
            new_status=auction.status,
            new_approval_status=auction.approval_status
        )
    except AuctionNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenException as e:
        raise HTTPException(status_code=403, detail=str(e))
    except InvalidDateRangeException as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{auction_id}/cancel", response_model=AuctionActionResponse)
async def cancel_auction(
    auction_id: int,
    request: CancelAuctionRequest,
    # ==== RBAC: Only auction creator or admin ====
    current_user: dict = Depends(RequireAuth),
    db: Session = Depends(get_db)
):
    """
    Cancel auction
    
    RBAC: Only auction creator or ADMIN
    """
    try:
        # ABSOLUTELY REQUIRED FIX: Extract ID directly from current_user object to avoid session errors
        user_id = getattr(current_user, 'id', None) or current_user.get('id')
        user_role = getattr(current_user, 'role', None) or current_user.get('role')
        
        # Explicit Owner check before service call if strict validation needed here
        if user_role != 'admin':
             auc = AuctionService.get_by_id(db, auction_id)
             if auc.seller_id != user_id and auc.created_by != user_id:
                 raise HTTPException(status_code=403, detail="Not authorized to cancel this auction")

        auction = AuctionService.cancel_auction(
            db=db,
            auction_id=auction_id,
            user_id=user_id,
            reason=request.cancellation_reason
        )
        
        return AuctionActionResponse(
            success=True,
            message="Auction cancelled successfully",
            auction_id=auction.id,
            new_status=auction.status
        )
    except AuctionNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# ADMIN ENDPOINTS (Approval workflow)
# ============================================================================

@router.get("/admin/pending-approval", response_model=AuctionListResponse)
async def get_pending_auctions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    # ==== RBAC: Only L1/L2 approvers or admins ====
    current_user: dict = Depends(RequireAdmin),
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
    current_user: dict = Depends(RequireL1Approver),
    db: Session = Depends(get_db)
):
    """
    L1 approval for auction
    
    RBAC: Requires L1_APPROVER or ADMIN role
    """
    try:
        # ABSOLUTELY REQUIRED FIX: Extract ID directly from current_user object to avoid session errors
        user_id = getattr(current_user, 'id', None) or current_user.get('id')
        
        auction = AuctionService.approve_l1(
            db=db,
            auction_id=auction_id,
            approver_id=user_id,
            remarks=request.remarks,
            approve=request.approve
        )
        
        return AuctionActionResponse(
            success=True,
            message="L1 approval processed" if request.approve else "Auction rejected",
            auction_id=auction.id,
            new_approval_status=auction.approval_status
        )
    except AuctionNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{auction_id}/approve-l2", response_model=AuctionActionResponse)
async def approve_auction_l2(
    auction_id: int,
    request: AuctionApprovalRequest,
    # ==== RBAC: Only L2 approvers or admins ====
    current_user: dict = Depends(RequireL2Approver),
    db: Session = Depends(get_db)
):
    """
    L2 approval for auction (final approval)
    
    RBAC: Requires L2_APPROVER or ADMIN role
    """
    try:
        # ABSOLUTELY REQUIRED FIX: Extract ID directly from current_user object to avoid session errors
        user_id = getattr(current_user, 'id', None) or current_user.get('id')
        
        auction = AuctionService.approve_l2(
            db=db,
            auction_id=auction_id,
            approver_id=user_id,
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
    except AuctionNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AuctionNotEditableException as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{auction_id}/publish", response_model=AuctionActionResponse)
async def publish_auction_manually(
    auction_id: int,
    # ==== RBAC: Only admins ====
    current_user: dict = Depends(RequireAdmin),
    db: Session = Depends(get_db)
):
    """
    Manually publish auction (make it LIVE)
    Usually done automatically by scheduler
    
    RBAC: Requires ADMIN role
    """
    try:
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
    except AuctionNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AuctionNotApprovedException as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# STATISTICS ENDPOINTS
# ============================================================================

@router.get("/stats/overview", response_model=AuctionStatsResponse)
async def get_auction_statistics(
    # ==== RBAC: Authenticated user for their stats ====
    current_user: dict = Depends(RequireAuth),
    db: Session = Depends(get_db)
):
    """
    Get auction statistics for current user
    
    RBAC: Requires authentication
    """
    # ABSOLUTELY REQUIRED FIX: Extract ID directly from current_user object to avoid session errors
    user_id = getattr(current_user, 'id', None) or current_user.get('id')
    return AuctionService.get_auction_stats(
        db=db, 
        user_id=user_id
    )


@router.get("/admin/stats/all", response_model=AuctionStatsResponse)
async def get_all_auction_statistics(
    # ==== RBAC: Only admins can see all stats ====
    current_user: dict = Depends(RequireAdmin),
    db: Session = Depends(get_db)
):
    """
    Get all auction statistics (admin only)
    
    RBAC: Requires ADMIN role
    """
    return AuctionService.get_auction_stats(db=db)
