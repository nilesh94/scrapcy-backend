"""
E-Auction Admin Routes
"""
from fastapi import APIRouter, Depends, HTTPException, Body, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime
from typing import Optional, List
import logging

from app.database.connection import get_db
from app.e_auction.models import (
    Auction, AuctionItem, Bid, AuctionParticipant, 
    Payment, Settlement, AuditLog
)
from app.models.users import User
from app.e_auction.utils.enums import AuctionStatus, ApprovalStatus

# UPDATED: Pointing to internal auth_dependencies and using RequireAdmin
from app.e_auction.routes.auth_dependencies import get_current_user, RequireAdmin

# Setup logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


# ============================================================================
# STATISTICS & DASHBOARD
# ============================================================================

@router.get("/stats")
async def get_admin_stats(
    db: Session = Depends(get_db),
    current_user = Depends(RequireAdmin)
):
    """
    Get comprehensive admin statistics for dashboard
    """
    try:
        # Total auctions
        total_auctions = db.query(Auction).count()
        
        # Live auctions
        live_auctions = db.query(Auction).filter(
            Auction.status == AuctionStatus.LIVE
        ).count()
        
        # Pending approval
        pending_approval = db.query(Auction).filter(
            Auction.approval_status == ApprovalStatus.PENDING
        ).count()
        
        # Total bids
        total_bids = db.query(Bid).count()
        
        # Active bidders (unique users who have placed bids)
        active_bidders = db.query(Bid.user_id).distinct().count()
        
        # Total revenue (sum of all settlements)
        total_revenue = db.query(
            func.sum(Settlement.final_bid_amount)
        ).scalar() or 0
        
        # Average bid value
        avg_bid_value = db.query(
            func.avg(Bid.bid_amount)
        ).scalar() or 0
        
        return {
            "total_auctions": total_auctions,
            "live_auctions": live_auctions,
            "pending_approval": pending_approval,
            "total_bids": total_bids,
            "active_bidders": active_bidders,
            "total_revenue": float(total_revenue),
            "avg_bid_value": float(avg_bid_value)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auctions")
async def get_all_auctions_admin(
    status: Optional[str] = None,
    approval_status: Optional[str] = None,
    search: Optional[str] = None,
    category: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user = Depends(RequireAdmin)
):
    """
    Get all auctions with admin filters
    """
    query = db.query(Auction)
    
    # Apply filters
    if status:
        query = query.filter(Auction.status == status)
    
    if approval_status:
        query = query.filter(Auction.approval_status == approval_status)
    
    if search:
        query = query.filter(
            Auction.auction_title.ilike(f"%{search}%")
        )
    
    if category:
        query = query.filter(Auction.category == category)
    
    if date_from:
        query = query.filter(Auction.scheduled_start_time >= date_from)
    
    if date_to:
        query = query.filter(Auction.scheduled_start_time <= date_to)
    
    # Order by created date (newest first)
    query = query.order_by(Auction.created_at.desc())
    
    # Pagination
    total = query.count()
    offset = (page - 1) * page_size
    auctions = query.offset(offset).limit(page_size).all()
    
    return {
        "items": auctions,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


# ============================================================================
# DELETE AUCTION (WITH AUDIT TRAIL)
# ============================================================================

@router.delete("/auctions/{auction_id}")
async def delete_auction(
    auction_id: int,
    reason: str = Body(..., embed=True),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user = Depends(RequireAdmin)
):
    """
    Delete auction with audit trail
    Requires reason for deletion
    """
    # Find auction
    auction = db.query(Auction).filter(Auction.id == auction_id).first()
    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")
    
    # Check if can delete (only DRAFT or CANCELLED auctions should be deletable)
    if auction.status in [AuctionStatus.LIVE, AuctionStatus.CLOSED]:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete live or closed auctions. Archive instead."
        )
    
    # Create audit log
    audit_log = AuditLog(
        auction_id=auction_id,
        action="DELETED",
        performed_by=current_user.id if hasattr(current_user, 'id') else current_user.get('id'),
        performed_by_name=current_user.name if hasattr(current_user, 'name') else f"User {current_user.get('id')}",
        reason=reason,
        timestamp=datetime.now(),
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    db.add(audit_log)
    
    # TODO: Send notification to auction creator
    # await send_notification(
    #      user_id=auction.created_by,
    #      type="AUCTION_DELETED",
    #      message=f"Your auction '{auction.auction_title}' has been deleted by admin",
    #      reason=reason
    # )
    
    # Delete related items first (cascade delete)
    db.query(AuctionItem).filter(AuctionItem.auction_id == auction_id).delete()
    
    # Delete auction
    db.delete(auction)
    db.commit()
    
    return {
        "message": "Auction deleted successfully",
        "auction_id": auction_id,
        "deleted_by": audit_log.performed_by,
        "reason": reason
    }


# ============================================================================
# ARCHIVE AUCTION
# ============================================================================

@router.post("/auctions/{auction_id}/archive")
async def archive_auction(
    auction_id: int,
    reason: str = Body(..., embed=True),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user = Depends(RequireAdmin)
):
    """
    Archive auction (soft delete)
    Can be restored later
    """
    # Find auction
    auction = db.query(Auction).filter(Auction.id == auction_id).first()
    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")
    
    if auction.status == AuctionStatus.ARCHIVED:
        raise HTTPException(status_code=400, detail="Auction is already archived")
    
    # Store previous status for restore
    previous_status = auction.status
    
    # Create audit log
    audit_log = AuditLog(
        auction_id=auction_id,
        action="ARCHIVED",
        performed_by=current_user.id if hasattr(current_user, 'id') else current_user.get('id'),
        performed_by_name=current_user.name if hasattr(current_user, 'name') else f"User {current_user.get('id')}",
        changes={
            "status": {
                "old_value": previous_status,
                "new_value": AuctionStatus.ARCHIVED
            }
        },
        reason=reason,
        timestamp=datetime.now(),
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    db.add(audit_log)
    
    # Update auction status
    auction.status = AuctionStatus.ARCHIVED
    auction.updated_at = datetime.now()
    
    # TODO: Send notification
    # await send_notification(
    #      user_id=auction.created_by,
    #      type="AUCTION_ARCHIVED",
    #      message=f"Your auction '{auction.auction_title}' has been archived",
    #      reason=reason
    # )
    
    db.commit()
    
    return {
        "message": "Auction archived successfully",
        "auction_id": auction_id,
        "archived_by": audit_log.performed_by,
        "reason": reason
    }


# ============================================================================
# RESTORE ARCHIVED AUCTION
# ============================================================================

@router.post("/auctions/{auction_id}/restore")
async def restore_auction(
    auction_id: int,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user = Depends(RequireAdmin)
):
    """
    Restore archived auction to DRAFT status
    """
    # Find auction
    auction = db.query(Auction).filter(Auction.id == auction_id).first()
    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")
    
    if auction.status != AuctionStatus.ARCHIVED:
        raise HTTPException(status_code=400, detail="Only archived auctions can be restored")
    
    # Create audit log
    audit_log = AuditLog(
        auction_id=auction_id,
        action="RESTORED",
        performed_by=current_user.id if hasattr(current_user, 'id') else current_user.get('id'),
        performed_by_name=current_user.name if hasattr(current_user, 'name') else f"User {current_user.get('id')}",
        changes={
            "status": {
                "old_value": AuctionStatus.ARCHIVED,
                "new_value": AuctionStatus.DRAFT
            }
        },
        timestamp=datetime.now(),
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    db.add(audit_log)
    
    # Restore auction to DRAFT
    auction.status = AuctionStatus.DRAFT
    auction.updated_at = datetime.now()
    
    db.commit()
    
    return {
        "message": "Auction restored successfully",
        "auction_id": auction_id,
        "restored_by": audit_log.performed_by
    }


# ============================================================================
# GET AUDIT TRAIL
# ============================================================================

@router.get("/audit/{auction_id}")
async def get_audit_trail(
    auction_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(RequireAdmin)
):
    """
    Get complete audit trail for an auction
    """
    # Verify auction exists
    auction = db.query(Auction).filter(Auction.id == auction_id).first()
    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")
    
    # Get all audit logs for this auction
    audit_logs = db.query(AuditLog).filter(
        AuditLog.auction_id == auction_id
    ).order_by(AuditLog.timestamp.desc()).all()
    
    return audit_logs


# ============================================================================
# PENDING APPROVALS (FOR DASHBOARD)
# ============================================================================

@router.get("/pending-approval")
async def get_pending_approvals(
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user = Depends(RequireAdmin)
):
    """
    Get auctions pending approval
    """
    query = db.query(Auction).filter(
        Auction.approval_status == ApprovalStatus.PENDING
    ).order_by(Auction.created_at.desc())
    
    total = query.count()
    offset = (page - 1) * page_size
    auctions = query.offset(offset).limit(page_size).all()
    
    return {
        "items": auctions,
        "total": total,
        "page": page,
        "page_size": page_size
    }


# ============================================================================
# GET VERIFIED SELLERS (FOR ADMIN DROP DOWN)
# ============================================================================

@router.get("/verified-sellers")
async def get_verified_sellers(
    q: Optional[str] = Query(None, min_length=2, description="Search by name, company or email"),
    db: Session = Depends(get_db),
    current_user = Depends(RequireAdmin)
):
    """
    Get list of verified sellers for dropdown selection
    Returns id, name, company_name, email
    """
    try:
        # Base query for sellers
        query = db.query(User).filter(
            User.role == "seller",
            User.is_active == 1,
            # Ensure only verified users are returned
            User.email_verified == 1, 
            User.gst_verified == 1
        )
        
        # Apply search filter only if q is provided and has content
        if q and len(q) >= 2:
            search_term = f"%{q}%"
            query = query.filter(
                or_(
                    User.first_name.ilike(search_term),
                    User.last_name.ilike(search_term),
                    User.company_name.ilike(search_term),
                    User.email.ilike(search_term)
                )
            )
        elif q:
            # If a search term is provided but too short, return empty list to avoid 500
            return []
        
        # Limit results for performance
        sellers = query.limit(20).all()
        
        # Return simplified list
        return [
            {
                "id": seller.id,
                "full_name": f"{seller.first_name} {seller.last_name}",
                "company_name": seller.company_name,
                "email": seller.email,
                "city": seller.city,
                "gst_number": seller.gst_number
            }
            for seller in sellers
        ]
    except Exception as e:
        logger.error(f"Error in get_verified_sellers: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error fetching sellers")
