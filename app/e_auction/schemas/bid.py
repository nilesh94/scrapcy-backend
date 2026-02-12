"""
Bid Pydantic Schemas
Request and Response models for Bidding endpoints
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.e_auction.utils.enums import BidStatus, BidType, AutoBidStatus


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class PlaceBidRequest(BaseModel):
    """Request to place a bid"""
    bid_amount: Decimal = Field(..., gt=0, description="Bid amount")
    
    @validator('bid_amount')
    def validate_bid_amount(cls, v):
        if v <= 0:
            raise ValueError('Bid amount must be greater than zero')
        # Additional validation (increment, minimum) done in service layer
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "bid_amount": 26000.00
            }
        }


class AutoBidCreateRequest(BaseModel):
    """Request to create auto-bid (proxy bidding)"""
    max_bid_amount: Decimal = Field(..., gt=0, description="Maximum bid amount (ceiling)")
    
    @validator('max_bid_amount')
    def validate_max_bid(cls, v):
        if v <= 0:
            raise ValueError('Maximum bid amount must be greater than zero')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "max_bid_amount": 50000.00
            }
        }


class AutoBidUpdateRequest(BaseModel):
    """Request to update auto-bid"""
    max_bid_amount: Decimal = Field(..., gt=0, description="New maximum bid amount")
    
    class Config:
        json_schema_extra = {
            "example": {
                "max_bid_amount": 75000.00
            }
        }


class BidFilterParams(BaseModel):
    """Filter parameters for bid history"""
    auction_id: Optional[int] = None
    auction_item_id: Optional[int] = None
    user_id: Optional[int] = None
    bid_status: Optional[BidStatus] = None
    bid_type: Optional[BidType] = None
    
    # Date range
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    
    # Only winning bids
    winning_only: bool = Field(False, description="Show only winning bids")
    
    # My bids only
    my_bids_only: bool = Field(False, description="Show only my bids")


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class BidResponse(BaseModel):
    """Single bid response"""
    id: int
    auction_id: int
    auction_item_id: int
    user_id: int
    
    bid_amount: Decimal
    bid_time: datetime
    bid_type: str
    
    is_winning_bid: bool
    bid_status: str
    
    ip_address: Optional[str] = None
    device_info: Optional[str] = None
    
    class Config:
        from_attributes = True


class BidDetailResponse(BaseModel):
    """Detailed bid with item info"""
    id: int
    auction_id: int
    auction_item_id: int
    user_id: int
    
    # Bid details
    bid_amount: Decimal
    bid_time: datetime
    bid_type: str
    is_winning_bid: bool
    bid_status: str
    
    # Item info (joined)
    item_name: Optional[str] = None
    lot_number: Optional[str] = None
    current_highest_bid: Optional[Decimal] = None
    
    # Status flags
    is_active: bool = False
    is_outbid: bool = False
    
    class Config:
        from_attributes = True


class BidHistoryResponse(BaseModel):
    """Bid history for a lot"""
    auction_item_id: int
    item_name: str
    total_bids: int
    unique_bidders: int
    highest_bid: Optional[Decimal] = None
    bids: List[BidResponse]


class BidListResponse(BaseModel):
    """List of bids with pagination"""
    total: int
    page: int
    page_size: int
    total_pages: int
    bids: List[BidDetailResponse]


class MyBidsResponse(BaseModel):
    """User's bid summary"""
    total_bids: int = 0
    active_bids: int = 0
    winning_bids: int = 0
    lost_bids: int = 0
    total_amount_bid: Decimal = Decimal('0.00')
    bids: List[BidDetailResponse]


class BidSuccessResponse(BaseModel):
    """Response after placing a bid"""
    success: bool = True
    message: str
    bid_id: int
    bid_amount: Decimal
    is_winning: bool
    previous_highest_bid: Optional[Decimal] = None
    
    # Next bid info
    min_next_bid: Decimal
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Bid placed successfully",
                "bid_id": 789,
                "bid_amount": 26500.00,
                "is_winning": True,
                "previous_highest_bid": 26000.00,
                "min_next_bid": 27000.00
            }
        }


class BidRejectedResponse(BaseModel):
    """Response when bid is rejected"""
    success: bool = False
    error: str
    error_code: str
    current_highest_bid: Optional[Decimal] = None
    min_required_bid: Optional[Decimal] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "Bid amount too low",
                "error_code": "BID_TOO_LOW",
                "current_highest_bid": 26000.00,
                "min_required_bid": 26500.00
            }
        }


# ============================================================================
# AUTO-BID SCHEMAS
# ============================================================================

class AutoBidResponse(BaseModel):
    """Auto-bid configuration response"""
    id: int
    auction_item_id: int
    user_id: int
    
    max_bid_amount: Decimal
    current_pushed_bid: Optional[Decimal] = None
    
    status: str
    
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Computed
    is_active: bool = False
    has_budget_remaining: bool = False
    budget_remaining: Optional[Decimal] = None
    
    class Config:
        from_attributes = True


class AutoBidListResponse(BaseModel):
    """User's active auto-bids"""
    total: int
    active_count: int
    auto_bids: List[AutoBidResponse]


class AutoBidSuccessResponse(BaseModel):
    """Response after creating/updating auto-bid"""
    success: bool = True
    message: str
    auto_bid_id: int
    max_bid_amount: Decimal
    current_highest_bid: Optional[Decimal] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Auto-bid activated successfully",
                "auto_bid_id": 123,
                "max_bid_amount": 50000.00,
                "current_highest_bid": 26000.00
            }
        }


class CancelAutoBidRequest(BaseModel):
    """Request to cancel auto-bid"""
    reason: Optional[str] = Field(None, max_length=500)


# ============================================================================
# BID STATISTICS
# ============================================================================

class BidStatsResponse(BaseModel):
    """Bidding statistics"""
    total_bids_placed: int = 0
    total_amount_bid: Decimal = Decimal('0.00')
    active_bids: int = 0
    won_auctions: int = 0
    lost_auctions: int = 0
    
    # Auto-bid stats
    active_auto_bids: int = 0
    auto_bids_triggered: int = 0
    
    # Success rate
    win_rate: float = 0.0  # Percentage


class LotBidSummary(BaseModel):
    """Summary of bids for a specific lot"""
    auction_item_id: int
    item_name: str
    
    total_bids: int = 0
    unique_bidders: int = 0
    
    starting_bid: Decimal
    current_highest_bid: Optional[Decimal] = None
    reserve_price: Optional[Decimal] = None
    
    last_bid_time: Optional[datetime] = None
    
    # User's participation
    user_has_bid: bool = False
    user_highest_bid: Optional[Decimal] = None
    user_is_winning: bool = False
    user_has_auto_bid: bool = False
    
    class Config:
        from_attributes = True


# ============================================================================
# REAL-TIME BID UPDATES (WebSocket)
# ============================================================================

class BidUpdateMessage(BaseModel):
    """WebSocket message for real-time bid updates"""
    event_type: str = "BID_PLACED"  # BID_PLACED, BID_OUTBID, AUCTION_EXTENDED, AUCTION_CLOSING
    auction_item_id: int
    
    # Bid info
    bid_id: Optional[int] = None
    bid_amount: Optional[Decimal] = None
    bid_time: Optional[datetime] = None
    
    # Current state
    current_highest_bid: Decimal
    total_bids: int
    unique_bidders: int
    
    # Timing
    time_remaining_seconds: Optional[int] = None
    is_extended: bool = False
    extension_count: int = 0
    
    # Winner info (anonymized)
    winning_user_id: Optional[int] = None  # Only sent to the winner
    is_current_user_winning: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "BID_PLACED",
                "auction_item_id": 456,
                "bid_amount": 27000.00,
                "current_highest_bid": 27000.00,
                "total_bids": 15,
                "unique_bidders": 8,
                "time_remaining_seconds": 180,
                "is_current_user_winning": False
            }
        }
