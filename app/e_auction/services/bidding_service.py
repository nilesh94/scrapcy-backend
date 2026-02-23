"""
Bidding Service
Business logic for bidding operations
Optimized for performance - handles high-volume bidding
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime
from decimal import Decimal

from app.e_auction.models import Bid, AuctionItem, Auction, AuctionParticipant, AutoBid
from app.e_auction.schemas.bid import *
from app.e_auction.utils.exceptions import *
from app.e_auction.utils.enums import BidStatus, BidType, LotStatus, AutoBidStatus
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
        - Bid amount is valid
        - User is not the seller
        """
        # Get lot with PESSIMISTIC LOCK to handle simultaneous last-minute bids
        lot = db.query(AuctionItem).with_for_update().filter(AuctionItem.id == auction_item_id).first()
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
        
        # Validate bid amount against freshest data inside the lock
        min_bid = (lot.highest_bid_amount or lot.starting_bid_amount) + (lot.min_increment_amount or 0)
        if bid_amount < min_bid:
            raise BidAmountTooLowException(min_bid, auction.currency)
        
        # Create bid
        bid = Bid(
            auction_id=lot.auction_id,
            auction_item_id=auction_item_id,
            user_id=user_id,
            bid_amount=bid_amount,
            bid_type=BidType.MANUAL,
            bid_status=BidStatus.ACTIVE,
            ip_address=ip_address,
            device_info=device_info
        )
        
        db.add(bid)
        
        # Update previous winning bid
        if lot.highest_bid_amount:
            previous_bid = db.query(Bid).filter(
                and_(
                    Bid.auction_item_id == auction_item_id,
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
        
        db.commit()
        db.refresh(bid)
        
        # TODO: Trigger auto-bid for other users
        # TODO: Send notifications to outbid users
        # TODO: Check if extension needed
        
        return bid
    
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
