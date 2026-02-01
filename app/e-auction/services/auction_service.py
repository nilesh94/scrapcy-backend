"""
Auction Service
Complete business logic for auction management
All config from ENV - no hardcoded values
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from app.e_auction.models import Auction, AuctionItem, AuctionParticipant
from app.e_auction.schemas.auction import *
from app.e_auction.utils.exceptions import *
from app.e_auction.utils.enums import AuctionStatus, ApprovalStatus
from app.e_auction.config import settings


class AuctionService:
    """Auction management service - all operations for auctions"""
    
    @staticmethod
    def create_auction(
        db: Session,
        auction_data: AuctionCreateRequest,
        created_by_user_id: int
    ) -> Auction:
        """Create new auction"""
        # Validate dates
        if auction_data.scheduled_end_time <= auction_data.scheduled_start_time:
            raise InvalidDateRangeException("End time must be after start time")
        
        auction = Auction(
            created_by=created_by_user_id,
            auction_title=auction_data.auction_title,
            auction_type=auction_data.auction_type,
            category=auction_data.category,
            region=auction_data.region,
            status=AuctionStatus.DRAFT,
            approval_status=ApprovalStatus.PENDING,
            scheduled_start_time=auction_data.scheduled_start_time,
            scheduled_end_time=auction_data.scheduled_end_time,
            currency=auction_data.currency,
            emd_amount=auction_data.emd_amount,
            registration_fee=auction_data.registration_fee,
            enable_extension=auction_data.enable_extension,
            extension_trigger_window_minutes=auction_data.extension_trigger_window_minutes,
            extension_duration_minutes=auction_data.extension_duration_minutes,
            inspection_start_date=auction_data.inspection_start_date,
            inspection_end_date=auction_data.inspection_end_date,
            inspection_location=auction_data.inspection_location,
            inspection_contact_person=auction_data.inspection_contact_person,
            inspection_contact_number=auction_data.inspection_contact_number,
            terms_and_conditions=auction_data.terms_and_conditions,
            auction_doc_url=auction_data.auction_doc_url,
        )
        
        db.add(auction)
        db.commit()
        db.refresh(auction)
        return auction
    
    @staticmethod
    def get_by_id(db: Session, auction_id: int) -> Auction:
        """Get auction by ID"""
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise AuctionNotFoundException(auction_id)
        
        # Increment view count
        auction.view_count = (auction.view_count or 0) + 1
        db.commit()
        return auction
    
    @staticmethod
    def update_auction(
        db: Session,
        auction_id: int,
        auction_data: AuctionUpdateRequest,
        user_id: int
    ) -> Auction:
        """Update auction"""
        auction = AuctionService.get_by_id(db, auction_id)
        
        if auction.created_by != user_id:
            raise ForbiddenException("Only creator can edit")
        
        if not auction.can_be_edited:
            raise AuctionNotEditableException(auction.status)
        
        # Update fields
        update_data = auction_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(auction, field, value)
        
        auction.updated_at = datetime.now()
        db.commit()
        db.refresh(auction)
        return auction
    
    @staticmethod
    def list_auctions(
        db: Session,
        filters: AuctionFilterParams,
        page: int,
        page_size: int,
        user_id: Optional[int] = None
    ) -> AuctionListResponse:
        """List auctions with filters"""
        query = db.query(Auction)
        
        if filters.status:
            query = query.filter(Auction.status == filters.status)
        if filters.category:
            query = query.filter(Auction.category == filters.category)
        if filters.search:
            query = query.filter(Auction.auction_title.ilike(f"%{filters.search}%"))
        if filters.created_by_me and user_id:
            query = query.filter(Auction.created_by == user_id)
        
        total = query.count()
        skip = (page - 1) * page_size
        auctions = query.order_by(Auction.created_at.desc()).offset(skip).limit(page_size).all()
        
        return AuctionListResponse(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
            auctions=[AuctionBasicResponse.from_orm(a) for a in auctions]
        )
    
    @staticmethod
    def submit_for_approval(db: Session, auction_id: int, user_id: int) -> Auction:
        """Submit for approval"""
        auction = AuctionService.get_by_id(db, auction_id)
        
        if auction.created_by != user_id:
            raise ForbiddenException()
        
        # Check has lots
        lot_count = db.query(func.count(AuctionItem.id)).filter(
            AuctionItem.auction_id == auction_id
        ).scalar()
        if lot_count == 0:
            raise InvalidDateRangeException("Must have at least one lot")
        
        auction.status = AuctionStatus.PENDING_APPROVAL
        db.commit()
        db.refresh(auction)
        return auction
    
    @staticmethod
    def approve_l1(
        db: Session,
        auction_id: int,
        approver_id: int,
        remarks: Optional[str],
        approve: bool
    ) -> Auction:
        """L1 approval"""
        auction = AuctionService.get_by_id(db, auction_id)
        
        if approve:
            auction.approval_status = ApprovalStatus.L1_APPROVED
            auction.publish_l1_approved_by = approver_id
            auction.publish_l1_approved_at = datetime.now()
            auction.publish_l1_remarks = remarks
        else:
            auction.status = AuctionStatus.DRAFT
            auction.approval_status = ApprovalStatus.REJECTED
            auction.publish_l1_remarks = remarks
        
        db.commit()
        db.refresh(auction)
        return auction
    
    @staticmethod
    def approve_l2(
        db: Session,
        auction_id: int,
        approver_id: int,
        remarks: Optional[str],
        approve: bool
    ) -> Auction:
        """L2 approval"""
        auction = AuctionService.get_by_id(db, auction_id)
        
        if auction.approval_status != ApprovalStatus.L1_APPROVED:
            raise AuctionNotEditableException("Must be L1 approved first")
        
        if approve:
            auction.approval_status = ApprovalStatus.L2_APPROVED
            auction.status = AuctionStatus.SCHEDULED
            auction.publish_l2_approved_by = approver_id
            auction.publish_l2_approved_at = datetime.now()
            auction.publish_l2_remarks = remarks
        else:
            auction.status = AuctionStatus.DRAFT
            auction.approval_status = ApprovalStatus.REJECTED
            auction.publish_l2_remarks = remarks
        
        db.commit()
        db.refresh(auction)
        return auction
    
    @staticmethod
    def publish_auction(db: Session, auction_id: int) -> Auction:
        """Publish auction (make LIVE)"""
        auction = AuctionService.get_by_id(db, auction_id)
        
        if not auction.is_approved:
            raise AuctionNotApprovedException()
        
        auction.status = AuctionStatus.LIVE
        auction.actual_start_time = datetime.now()
        auction.published_at = datetime.now()
        
        db.commit()
        db.refresh(auction)
        return auction
    
    @staticmethod
    def close_auction(db: Session, auction_id: int) -> Auction:
        """Close auction"""
        auction = AuctionService.get_by_id(db, auction_id)
        
        auction.status = AuctionStatus.CLOSED
        auction.actual_end_time = datetime.now()
        
        db.commit()
        db.refresh(auction)
        return auction
