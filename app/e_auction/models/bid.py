"""
Bid SQLAlchemy Model
Represents individual bid transactions
"""
from sqlalchemy import Column, Integer, String, Float, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base


class Bid(Base):
    """Bid model - Individual bid transaction"""
    __tablename__ = "BIDS"
    __table_args__ = {'schema': 'SCRAPCY_APP'}
    
    # Primary Key
    id = Column("ID", Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign Keys
    auction_id = Column("AUCTION_ID", Integer, ForeignKey("SCRAPCY_APP.AUCTIONS.ID"), nullable=False)
    auction_item_id = Column("AUCTION_ITEM_ID", Integer, ForeignKey("SCRAPCY_APP.AUCTION_ITEMS.ID"), nullable=False)
    user_id = Column("USER_ID", Integer, nullable=False)
    
    # Bid Details
    bid_amount = Column("BID_AMOUNT", Float, nullable=False)
    bid_time = Column("BID_TIME", TIMESTAMP(6), server_default=func.current_timestamp())
    bid_type = Column("BID_TYPE", String(20), default="MANUAL")  # MANUAL, AUTO, PROXY
    
    # Status
    is_winning_bid = Column("IS_WINNING_BID", Integer, default=0)
    bid_status = Column("BID_STATUS", String(20), default="ACTIVE")  # ACTIVE, OUTBID, WON, LOST, CANCELLED
    
    # Tracking
    ip_address = Column("IP_ADDRESS", String(50))
    device_info = Column("DEVICE_INFO", String(500))
    session_id = Column("SESSION_ID", String(255))
    
    # Relationships
    auction = relationship("Auction", back_populates="bids")
    auction_item = relationship("AuctionItem", back_populates="bids")
    
    def __repr__(self):
        return f"<Bid(id={self.id}, amount={self.bid_amount}, user_id={self.user_id}, status='{self.bid_status}')>"
    
    @property
    def is_active(self) -> bool:
        """Check if bid is currently active"""
        return self.bid_status == "ACTIVE"
    
    @property
    def is_winning(self) -> bool:
        """Check if this is the winning bid"""
        return self.is_winning_bid == 1
    
    @property
    def is_manual_bid(self) -> bool:
        """Check if bid was placed manually"""
        return self.bid_type == "MANUAL"
    
    @property
    def is_auto_bid(self) -> bool:
        """Check if bid was placed by auto-bidding system"""
        return self.bid_type in ["AUTO", "PROXY"]
