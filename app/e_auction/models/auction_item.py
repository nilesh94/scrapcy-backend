"""
AuctionItem (Lot) SQLAlchemy Model
Represents individual lots within an auction
"""
from sqlalchemy import Column, Integer, String, Float, TIMESTAMP, CLOB, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base
from app.e_auction.models.auction_item_images import AuctionItemImage
from datetime import datetime


class AuctionItem(Base):
    """AuctionItem model - Individual lot/item in auction"""
    __tablename__ = "AUCTION_ITEMS"
    __table_args__ = {'schema': 'SCRAPCY_APP'}
    
    # Primary Key
    id = Column("ID", Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign Keys
    auction_id = Column("AUCTION_ID", Integer, ForeignKey("SCRAPCY_APP.AUCTIONS.ID"), nullable=False)
    origin_listing_id = Column("ORIGIN_LISTING_ID", Integer)
    
    # Item Details
    item_name = Column("ITEM_NAME", String(255), nullable=False)
    item_type = Column("ITEM_TYPE", String(100))
    lot_number = Column("LOT_NUMBER", String(50))
    
    # Scrap Material Details
    scrap_type = Column("SCRAP_TYPE", String(100))
    category = Column("CATEGORY", String(100))
    material = Column("MATERIAL", String(100))
    grade = Column("GRADE", String(100))
    form = Column("FORM", String(100))
    
    # Quantity
    quantity = Column("QUANTITY", Float, nullable=False)
    unit = Column("UNIT", String(50), nullable=False)
    is_partial_qty_allowed = Column("IS_PARTIAL_QTY_ALLOWED", Integer, default=0)
    estimated_weight = Column("ESTIMATED_WEIGHT", Float)
    weight_unit = Column("WEIGHT_UNIT", String(20))
    
    # Location
    location_city = Column("LOCATION_CITY", String(100))
    location_state = Column("LOCATION_STATE", String(100))
    location_address = Column("LOCATION_ADDRESS", String(500))
    pickup_conditions = Column("PICKUP_CONDITIONS", String(1000))
    
    # Media
    image_urls = Column("IMAGE_URLS", CLOB)  # JSON array
    test_report_url = Column("TEST_REPORT_URL", String(500))
    attributes_json = Column("ATTRIBUTES_JSON", CLOB)  # Additional attributes
    
    # Bidding Configuration
    starting_bid_amount = Column("STARTING_BID_AMOUNT", Float, nullable=False)
    reserve_price = Column("RESERVE_PRICE", Float)
    min_increment_amount = Column("MIN_INCREMENT_AMOUNT", Float)
    buy_now_price = Column("BUY_NOW_PRICE", Float)
    
    # Lot Scheduling
    lot_start_time = Column("LOT_START_TIME", TIMESTAMP(6))
    lot_end_time = Column("LOT_END_TIME", TIMESTAMP(6))
    
    # Lot Status
    lot_status = Column("LOT_STATUS", String(50), default="PENDING")
    lot_auction_type = Column("LOT_AUCTION_TYPE", String(50))
    
    # Current Bidding State
    highest_bid_amount = Column("HIGHEST_BID_AMOUNT", Float)
    winner_user_id = Column("WINNER_USER_ID", Integer)
    
    # Performance Counters (Denormalized)
    total_bids_count = Column("TOTAL_BIDS_COUNT", Integer, default=0)
    unique_bidders_count = Column("UNIQUE_BIDDERS_COUNT", Integer, default=0)
    last_bid_time = Column("LAST_BID_TIME", TIMESTAMP(6))
    extension_count = Column("EXTENSION_COUNT", Integer, default=0)
    view_count = Column("VIEW_COUNT", Integer, default=0)
    
    # Settlement Details
    final_sold_price = Column("FINAL_SOLD_PRICE", Float)
    commission_rate = Column("COMMISSION_RATE", Float)
    commission_amount = Column("COMMISSION_AMOUNT", Float)
    tax_amount = Column("TAX_AMOUNT", Float)
    total_payable_amount = Column("TOTAL_PAYABLE_AMOUNT", Float)
    settlement_status = Column("SETTLEMENT_STATUS", String(50))
    
    # Approval Workflow
    l1_approved_by = Column("L1_APPROVED_BY", Integer)
    l1_approved_at = Column("L1_APPROVED_AT", TIMESTAMP(6))
    l1_remarks = Column("L1_REMARKS", String(500))
    l2_approved_by = Column("L2_APPROVED_BY", Integer)
    l2_approved_at = Column("L2_APPROVED_AT", TIMESTAMP(6))
    l2_remarks = Column("L2_REMARKS", String(500))
    rejection_reason = Column("REJECTION_REASON", String(500))
    
    # Additional
    condition_rating = Column("CONDITION_RATING", Integer)  # 1-5 stars
    is_featured = Column("IS_FEATURED", Integer, default=0)
    seller_notes = Column("SELLER_NOTES", String(2000))
    
    # Auction Type Specific
    decrement_amount = Column("DECREMENT_AMOUNT", Float)  # For Dutch auction
    
    # Audit
    created_at = Column("CREATED_AT", TIMESTAMP(6), server_default=func.current_timestamp())

    # --- Link images table to this Lot ---
    images = relationship("AuctionItemImage", back_populates="item", cascade="all, delete-orphan", lazy="joined")
    
    # Relationships
    auction = relationship("Auction", back_populates="items")
    bids = relationship("Bid", back_populates="auction_item", cascade="all, delete-orphan")
    watchlist_entries = relationship("Watchlist", back_populates="auction_item", cascade="all, delete-orphan")
    auto_bids = relationship("AutoBid", back_populates="auction_item", cascade="all, delete-orphan")
    settlement = relationship("Settlement", back_populates="auction_item", uselist=False)
    
    def __repr__(self):
        return f"<AuctionItem(id={self.id}, name='{self.item_name}', status='{self.lot_status}')>"
    
    @property
    def is_live(self) -> bool:
        """Check if lot is currently live for bidding"""
        return self.lot_status == "LIVE"
    
    @property
    def is_sold(self) -> bool:
        """Check if lot has been sold"""
        return self.lot_status == "SOLD"
    
    @property
    def has_bids(self) -> bool:
        """Check if lot has received any bids"""
        return self.total_bids_count > 0
    
    @property
    def current_price(self) -> float:
        """Get current price (highest bid or starting bid)"""
        return self.highest_bid_amount or self.starting_bid_amount
    
    @property
    def min_next_bid(self) -> float:
        """Calculate minimum next bid amount based on current highest bid"""
        current = self.highest_bid_amount or self.starting_bid_amount
        # Use DB increment; if null, fallback to 0 to allow any bid above current
        increment = self.min_increment_amount or 0
        return current + increment
    
    @property
    def has_reserve_price(self) -> bool:
        """Check if lot has a reserve price"""
        return self.reserve_price is not None and self.reserve_price > 0
    
    @property
    def reserve_met(self) -> bool:
        """Check if reserve price has been met"""
        if not self.has_reserve_price:
            return True
        return self.highest_bid_amount is not None and self.highest_bid_amount >= self.reserve_price
    
    @property
    def can_accept_bids(self) -> bool:
        """Check if lot can accept new bids"""
        # Use datetime.now() instead of func.current_timestamp() to return a valid boolean for Pydantic
        return self.lot_status == "LIVE" and (self.lot_end_time > datetime.now() if self.lot_end_time else False)
