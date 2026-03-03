"""
Bidding Service
Business logic for bidding operations
Optimized for performance - handles high-volume bidding
"""
from typing import List, Optional
from sqlalchemy.orm import Session, noload
from sqlalchemy import and_, func
from datetime import datetime, timedelta
from decimal import Decimal
from fastapi import HTTPException

from app.e_auction.models import Bid, AuctionItem, Auction, AuctionParticipant, AutoBid
from app.e_auction.schemas.bid import *
from app.e_auction.utils.exceptions import *
from app.e_auction.utils.enums import BidStatus, BidType, LotStatus, AutoBidStatus, AuctionType
from app.e_auction.config import settings


class BiddingService:
    """Bidding service - handles all bid operations"""
    
    @staticmethod
    def place_bid(
        db: Session,
        auction_item_id: int,
        user_id: int,
        bid_amount: Decimal,
        ip_address: str,
        device_info: Optional[str] = None
    ) -> Bid:
        """
        Place a bid on a lot
        
        Validates:
        - User is registered for auction
        - Lot is live
        - Bid amount is valid (based on engine type)
        - User is not the seller
        """
        # Get lot with PESSIMISTIC LOCK. noload prevents ORA-02014 by removing joined-image subquery.
        lot = db.query(AuctionItem).options(noload(AuctionItem.images)).with_for_update().filter(AuctionItem.id == auction_item_id).first()
        if not lot:
            raise LotNotFoundException(auction_item_id)
        
        if not lot.is_live:
            raise LotNotAvailableForBiddingException(lot.lot_status)
        
        # Get auction
        auction = db.query(Auction).filter(Auction.id == lot.auction_id).first()
        
        # Check user is not seller
        if auction.created_by == user_id:
            raise SellerCannotBidException()
        
        # Check user is registered
        participant = db.query(AuctionParticipant).filter(
            and_(
                AuctionParticipant.auction_id == lot.auction_id,
                AuctionParticipant.user_id == user_id,
                AuctionParticipant.payment_status == "SUCCESS"
            )
        ).first()
        
        if not participant:
            raise UserNotRegisteredForAuctionException()

        # DISPATCHER: Route to specific engine logic based on Auction Type
        if lot.lot_auction_type == AuctionType.FORWARD:
            return BiddingService._execute_forward_bid(db, lot, auction, user_id, bid_amount, ip_address, device_info)
        
        elif lot.lot_auction_type == AuctionType.REVERSE:
            return BiddingService._execute_reverse_bid(db, lot, auction, user_id, bid_amount, ip_address, device_info)
            
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported auction type engine: {lot.lot_auction_type}")

    @staticmethod
    def _execute_forward_bid(db: Session, lot: AuctionItem, auction: Auction, user_id: int, bid_amount: Decimal, ip: str, device: Optional[str]) -> Bid:
        # Validation for Forward Auction: Price must go UP
        min_bid = (lot.highest_bid_amount or lot.starting_bid_amount) + (lot.min_increment_amount or 0)
        if bid_amount < min_bid:
            raise BidAmountTooLowException(min_bid, auction.currency)
        
        return BiddingService._commit_bid_and_update_lot(db, lot, user_id, bid_amount, ip, device)

    @staticmethod
    def _execute_reverse_bid(db: Session, lot: AuctionItem, auction: Auction, user_id: int, bid_amount: Decimal, ip: str, device: Optional[str]) -> Bid:
        # Validation for Reverse Auction: Price must go DOWN
        current_lowest = lot.highest_bid_amount or lot.starting_bid_amount
        max_allowed = current_lowest - (lot.min_increment_amount or 0)
        
        if bid_amount > max_allowed:
            raise HTTPException(status_code=400, detail=f"Bid too high for reverse auction. Max allowed: {max_allowed}")
        
        return BiddingService._commit_bid_and_update_lot(db, lot, user_id, bid_amount, ip, device)

    @staticmethod
    def _commit_bid_and_update_lot(db: Session, lot: AuctionItem, user_id: int, bid_amount: Decimal, ip: str, device: Optional[str]) -> Bid:
        # Create bid
        bid = Bid(
            auction_id=lot.auction_id,
            auction_item_id=lot.id,
            user_id=user_id,
            bid_amount=bid_amount,
            bid_type=BidType.MANUAL,
            bid_status=BidStatus.ACTIVE,
            ip_address=ip,
            device_info=device
        )
        
        db.add(bid)
        
        # Update previous winning bid
        if lot.highest_bid_amount:
            previous_bid = db.query(Bid).filter(
                and_(
                    Bid.auction_item_id == lot.id,
                    Bid.is_winning_bid == 1
                )
            ).first()
            if previous_bid:
                previous_bid.is_winning_bid = 0
                previous_bid.bid_status = BidStatus.OUTBID
        
        # Mark this as winning
        bid.is_winning_bid = 1
        
        # Update lot metadata inside the transaction
        lot.highest_bid_amount = bid_amount
        lot.winner_user_id = user_id
        lot.total_bids_count = (lot.total_bids_count or 0) + 1
        lot.last_bid_time = datetime.now() # ALIGNMENT: Track local time

        # Handle Auto-Extension and capture minutes for WebSocket broadcast
        extended_minutes = BiddingService._handle_auto_extension(lot)
        bid.is_extended = extended_minutes > 0
        bid.extension_minutes = extended_minutes 

        db.commit()
        db.refresh(bid)
        
        # NOTE: Real-time broadcast should be triggered from the caller/route
        return bid

    @staticmethod
    def _handle_auto_extension(lot: AuctionItem) -> int:
        """
        Industrial Precision Anti-Sniping Logic.
        Uses exact DB configuration. Returns 0 if not configured/enabled.
        """
        auction = lot.auction 
        
        # Check if extension is explicitly enabled in DB
        enable_ext = auction.ENABLE_EXTENSION if hasattr(auction, 'ENABLE_EXTENSION') else auction.enable_extension
        if not enable_ext:
            return 0

        # Pull exact configurations from DB
        window_mins = auction.EXTENSION_TRIGGER_WINDOW_MINUTES or 0
        ext_mins = auction.EXTENSION_DURATION_MINUTES or 0
        min_bids = auction.EXTENSION_MIN_TOTAL_BIDS or 1

        # Only proceed if we have a valid duration configured
        if ext_mins > 0 and lot.lot_end_time and (lot.total_bids_count or 0) >= min_bids:
            now = datetime.now()
            time_left = lot.lot_end_time - now
            
            # If bid is within the configured sniping window
            if time_left <= timedelta(minutes=window_mins) and time_left > timedelta(0):
                lot.lot_end_time = lot.lot_end_time + timedelta(minutes=ext_mins)
                lot.extension_count = (lot.extension_count or 0) + 1
                return ext_mins
        
        return 0
    
    @staticmethod
    def create_auto_bid(
        db: Session,
        auction_item_id: int,
        user_id: int,
        max_bid_amount: Decimal
    ) -> AutoBid:
        """Create auto-bid (proxy bidding)"""
        # Get lot
        lot = db.query(AuctionItem).filter(AuctionItem.id == auction_item_id).first()
        if not lot:
            raise LotNotFoundException(auction_item_id)
        
        # Check no existing active auto-bid
        existing = db.query(AutoBid).filter(
            and_(
                AutoBid.auction_item_id == auction_item_id,
                AutoBid.user_id == user_id,
                AutoBid.status == AutoBidStatus.ACTIVE
            )
        ).first()
        
        if existing:
            raise AutoBidConflictException()
        
        # Create auto-bid
        auto_bid = AutoBid(
            auction_item_id=auction_item_id,
            user_id=user_id,
            max_bid_amount=max_bid_amount,
            status=AutoBidStatus.ACTIVE
        )
        
        db.add(auto_bid)
        db.commit()
        db.refresh(auto_bid)
        
        # TODO: Immediately try to bid if current price < max
        
        return auto_bid
    
    @staticmethod
    def get_bid_history(
        db: Session,
        auction_item_id: int,
        page: int = 1,
        page_size: int = 50
    ) -> List[Bid]:
        """Get bid history for a lot"""
        skip = (page - 1) * page_size
        
        bids = db.query(Bid).filter(
            Bid.auction_item_id == auction_item_id
        ).order_by(Bid.bid_time.desc()).offset(skip).limit(page_size).all()
        
        return bids
    
    @staticmethod
    def get_my_bids(
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 20
    ) -> MyBidsResponse:
        """Get user's bids"""
        skip = (page - 1) * page_size
        
        bids = db.query(Bid).filter(
            Bid.user_id == user_id
        ).order_by(Bid.bid_time.desc()).offset(skip).limit(page_size).all()
        
        # Calculate stats
        total_bids = db.query(func.count(Bid.id)).filter(Bid.user_id == user_id).scalar()
        active_bids = db.query(func.count(Bid.id)).filter(
            and_(Bid.user_id == user_id, Bid.bid_status == BidStatus.ACTIVE)
        ).scalar()
        winning_bids = db.query(func.count(Bid.id)).filter(
            and_(Bid.user_id == user_id, Bid.is_winning_bid == 1)
        ).scalar()
        
        total_amount = db.query(func.sum(Bid.bid_amount)).filter(
            Bid.user_id == user_id
        ).scalar() or Decimal('0.00')
        
        return MyBidsResponse(
            total_bids=total_bids,
            active_bids=active_bids,
            winning_bids=winning_bids,
            lost_bids=0,  # Calculate from closed lots
            total_amount_bid=total_amount,
            # UPDATED: model_validate for Pydantic V2
            bids=[BidDetailResponse.model_validate(b) for b in bids]
        )
