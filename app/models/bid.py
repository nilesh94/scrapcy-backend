"""
Bidding Models: Bids and Bid Events
Mapped to SCRAPCY_APP schema
"""
from sqlalchemy import Column, Integer, String, Float, TIMESTAMP, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base

class Bid(Base):
    """Bid model - Main record for every bid placed"""
    __tablename__ = "BIDS"
    __table_args__ = {'schema': 'SCRAPCY_APP', 'extend_existing': True}
    
    id = Column("ID", Integer, primary_key=True, autoincrement=True)
    auction_id = Column("AUCTION_ID", Integer, ForeignKey("SCRAPCY_APP.AUCTIONS.ID"), nullable=False)
    auction_item_id = Column("AUCTION_ITEM_ID", Integer, ForeignKey("SCRAPCY_APP.AUCTION_ITEMS.ID"), nullable=False)
    user_id = Column("USER_ID", Integer, nullable=False)
    bid_amount = Column("BID_AMOUNT", Float, nullable=False)
    # SaaS Standard: Using timezone-aware DateTime for global bid synchronization
    bid_time = Column("BID_TIME", DateTime(timezone=True), server_default=func.current_timestamp())
    bid_type = Column("BID_TYPE", String(20))  # MANUAL, AUTO
    is_winning_bid = Column("IS_WINNING_BID", Integer, default=0)
    bid_status = Column("BID_STATUS", String(20)) # ACTIVE, OUTBID, CANCELLED
    ip_address = Column("IP_ADDRESS", String(50))
    device_info = Column("DEVICE_INFO", String(500))
    session_id = Column("SESSION_ID", String(255))

    # Relationships
    auction = relationship("Auction", back_populates="bids")
    auction_item = relationship("AuctionItem", back_populates="bids")

class BidEvent(Base):
    """BidEvent model - Audit log for real-time bidding events"""
    __tablename__ = "BID_EVENTS"
    __table_args__ = {'schema': 'SCRAPCY_APP', 'extend_existing': True}
    
    id = Column("ID", Integer, primary_key=True, autoincrement=True)
    bid_id = Column("BID_ID", Integer, nullable=False)
    auction_item_id = Column("AUCTION_ITEM_ID", Integer, nullable=False)
    user_id = Column("USER_ID", Integer, nullable=False)
    event_type = Column("EVENT_TYPE", String(50), nullable=False) # BID_PLACED, OUTBID, EXTENSION
    bid_amount = Column("BID_AMOUNT", Float, nullable=False)
    previous_highest_bid = Column("PREVIOUS_HIGHEST_BID", Float)
    response_time_ms = Column("RESPONSE_TIME_MS", Integer)
    # SaaS Standard: Ensure audit events are timestamped with global accuracy
    server_timestamp = Column("SERVER_TIMESTAMP", DateTime(timezone=True), server_default=func.current_timestamp())
    is_auto_bid = Column("IS_AUTO_BID", Integer, default=0)
    auto_bid_id = Column("AUTO_BID_ID", Integer)
    ip_address = Column("IP_ADDRESS", String(50))
    device_type = Column("DEVICE_TYPE", String(50))
