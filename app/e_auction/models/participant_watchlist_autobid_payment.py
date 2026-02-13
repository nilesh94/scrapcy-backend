"""
Additional Models: Participant, Watchlist, AutoBid, Payment
Mapped to SCRAPCY_APP schema
"""
from sqlalchemy import Column, Integer, String, Float, TIMESTAMP, CLOB, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base


# ============================================================================
# AUCTION_PARTICIPANT MODEL
# ============================================================================

class AuctionParticipant(Base):
    """AuctionParticipant model - User registration for auction"""
    __tablename__ = "AUCTION_PARTICIPANTS"
    __table_args__ = {'schema': 'SCRAPCY_APP'}
    
    id = Column("ID", Integer, primary_key=True, autoincrement=True)
    auction_id = Column("AUCTION_ID", Integer, ForeignKey("SCRAPCY_APP.AUCTIONS.ID"), nullable=False)
    user_id = Column("USER_ID", Integer, nullable=False)
    
    # Financial
    registration_fee_paid = Column("REGISTRATION_FEE_PAID", Float, default=0)
    emd_blocked_amount = Column("EMD_BLOCKED_AMOUNT", Float, default=0)
    payment_status = Column("PAYMENT_STATUS", String(50), default="PENDING")
    payment_ref_id = Column("PAYMENT_REF_ID", String(255))
    
    # Status
    participation_status = Column("PARTICIPATION_STATUS", String(50), default="APPROVED")
    agreed_to_terms = Column("AGREED_TO_TERMS", Integer, default=0)
    
    # Verification
    kyc_verified = Column("KYC_VERIFIED", Integer, default=0)
    phone_verified = Column("PHONE_VERIFIED", Integer, default=0)
    email_verified = Column("EMAIL_VERIFIED", Integer, default=0)
    
    # Audit
    ip_address = Column("IP_ADDRESS", String(50))
    registered_at = Column("REGISTERED_AT", TIMESTAMP(6), server_default=func.current_timestamp())
    
    # Relationships
    auction = relationship("Auction", back_populates="participants")
    
    def __repr__(self):
        return f"<AuctionParticipant(auction_id={self.auction_id}, user_id={self.user_id}, status='{self.participation_status}')>"
    
    @property
    def is_approved(self) -> bool:
        return self.participation_status == "APPROVED" and self.payment_status == "SUCCESS"
    
    @property
    def can_bid(self) -> bool:
        return self.is_approved and self.agreed_to_terms == 1


# ============================================================================
# WATCHLIST MODEL
# ============================================================================

class Watchlist(Base):
    """Watchlist model - User's watched items"""
    __tablename__ = "WATCHLIST"
    __table_args__ = {'schema': 'SCRAPCY_APP'}
    
    id = Column("ID", Integer, primary_key=True, autoincrement=True)
    user_id = Column("USER_ID", Integer, nullable=False)
    auction_item_id = Column("AUCTION_ITEM_ID", Integer, ForeignKey("SCRAPCY_APP.AUCTION_ITEMS.ID"), nullable=False)
    created_at = Column("CREATED_AT", TIMESTAMP(6), server_default=func.current_timestamp())
    
    # Relationships
    auction_item = relationship("AuctionItem", back_populates="watchlist_entries")
    
    def __repr__(self):
        return f"<Watchlist(user_id={self.user_id}, item_id={self.auction_item_id})>"


# ============================================================================
# AUTO_BID MODEL
# ============================================================================

class AutoBid(Base):
    """AutoBid model - Proxy bidding configuration"""
    __tablename__ = "AUTO_BIDS"
    __table_args__ = {'schema': 'SCRAPCY_APP'}
    
    id = Column("ID", Integer, primary_key=True, autoincrement=True)
    auction_item_id = Column("AUCTION_ITEM_ID", Integer, ForeignKey("SCRAPCY_APP.AUCTION_ITEMS.ID"), nullable=False)
    user_id = Column("USER_ID", Integer, nullable=False)
    
    # Configuration
    max_bid_amount = Column("MAX_BID_AMOUNT", Float, nullable=False)
    current_pushed_bid = Column("CURRENT_PUSHED_BID", Float)
    
    # Status
    status = Column("STATUS", String(20), default="ACTIVE")  # ACTIVE, OUTBID, CANCELLED, EXHAUSTED
    
    # Audit
    created_at = Column("CREATED_AT", TIMESTAMP(6), server_default=func.current_timestamp())
    updated_at = Column("UPDATED_AT", TIMESTAMP(6), onupdate=func.current_timestamp())
    
    # Relationships
    auction_item = relationship("AuctionItem", back_populates="auto_bids")
    
    def __repr__(self):
        return f"<AutoBid(user_id={self.user_id}, item_id={self.auction_item_id}, max={self.max_bid_amount})>"
    
    @property
    def is_active(self) -> bool:
        return self.status == "ACTIVE"
    
    @property
    def has_budget_remaining(self) -> bool:
        if not self.current_pushed_bid:
            return True
        return self.current_pushed_bid < self.max_bid_amount


# ============================================================================
# PAYMENT MODEL
# ============================================================================

class Payment(Base):
    """Payment model - All payment transactions"""
    __tablename__ = "PAYMENTS"
    __table_args__ = {'schema': 'SCRAPCY_APP'}
    
    id = Column("ID", Integer, primary_key=True, autoincrement=True)
    user_id = Column("USER_ID", Integer, nullable=False)
    auction_id = Column("AUCTION_ID", Integer, ForeignKey("SCRAPCY_APP.AUCTIONS.ID"))
    auction_item_id = Column("AUCTION_ITEM_ID", Integer)
    
    # Payment Details
    payment_type = Column("PAYMENT_TYPE", String(50), nullable=False)
    amount = Column("AMOUNT", Float, nullable=False)
    currency = Column("CURRENCY", String(10), default="INR")
    
    # Status
    payment_status = Column("PAYMENT_STATUS", String(50), default="PENDING")
    payment_method = Column("PAYMENT_METHOD", String(50))
    transaction_id = Column("TRANSACTION_ID", String(255), unique=True)
    gateway_response = Column("GATEWAY_RESPONSE", CLOB)
    
    # Refund
    refund_transaction_id = Column("REFUND_TRANSACTION_ID", String(255))
    refund_amount = Column("REFUND_AMOUNT", Float)
    refund_status = Column("REFUND_STATUS", String(50))
    refund_initiated_at = Column("REFUND_INITIATED_AT", TIMESTAMP(6))
    refund_completed_at = Column("REFUND_COMPLETED_AT", TIMESTAMP(6))
    refund_reason = Column("REFUND_REASON", String(500))
    
    # Additional
    bank_account_id = Column("BANK_ACCOUNT_ID", Integer)
    fee_breakdown_json = Column("FEE_BREAKDOWN_JSON", CLOB)
    
    # Audit
    created_at = Column("CREATED_AT", TIMESTAMP(6), server_default=func.current_timestamp())
    processed_at = Column("PROCESSED_AT", TIMESTAMP(6))
    updated_at = Column("UPDATED_AT", TIMESTAMP(6), onupdate=func.current_timestamp())
    ip_address = Column("IP_ADDRESS", String(50))
    
    # Relationships
    auction = relationship("Auction", back_populates="payments")
    
    def __repr__(self):
        return f"<Payment(id={self.id}, type='{self.payment_type}', amount={self.amount}, status='{self.payment_status}')>"
    
    @property
    def is_successful(self) -> bool:
        return self.payment_status == "SUCCESS"
    
    @property
    def is_pending(self) -> bool:
        return self.payment_status == "PENDING"
    
    @property
    def is_refunded(self) -> bool:
        return self.refund_status == "PROCESSED"
