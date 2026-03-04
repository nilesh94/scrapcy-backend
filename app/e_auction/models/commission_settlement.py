"""
Commission and Settlement Models
"""
from sqlalchemy import Column, Integer, String, Float, TIMESTAMP, CLOB, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base
from datetime import datetime, timezone


# ============================================================================
# COMMISSION_RULE MODEL
# ============================================================================

class CommissionRule(Base):
    """CommissionRule model - Commission configuration"""
    __tablename__ = "COMMISSION_RULES"
    __table_args__ = {'schema': 'SCRAPCY_APP'}
    
    id = Column("ID", Integer, primary_key=True, autoincrement=True)
    
    # Rule Configuration
    rule_name = Column("RULE_NAME", String(255), nullable=False)
    rule_type = Column("RULE_TYPE", String(50), nullable=False)
    
    # Commission Rates
    seller_commission_percent = Column("SELLER_COMMISSION_PERCENT", Float, default=0)
    buyer_commission_percent = Column("BUYER_COMMISSION_PERCENT", Float, default=0)
    
    # Conditional Application
    applies_to_auction_type = Column("APPLIES_TO_AUCTION_TYPE", String(50))
    applies_to_category = Column("APPLIES_TO_CATEGORY", String(100))
    min_transaction_amount = Column("MIN_TRANSACTION_AMOUNT", Float)
    max_transaction_amount = Column("MAX_TRANSACTION_AMOUNT", Float)
    
    # Status
    is_active = Column("IS_ACTIVE", Integer, default=1)
    is_default = Column("IS_DEFAULT", Integer, default=0)
    priority = Column("PRIORITY", Integer, default=0)
    
    # Effective Period
    effective_from = Column("EFFECTIVE_FROM", TIMESTAMP(6))
    effective_until = Column("EFFECTIVE_UNTIL", TIMESTAMP(6))
    
    # Audit
    created_by = Column("CREATED_BY", Integer, nullable=False)
    created_at = Column("CREATED_AT", TIMESTAMP(6), server_default=func.current_timestamp())
    updated_at = Column("UPDATED_AT", TIMESTAMP(6), onupdate=func.current_timestamp())
    
    def __repr__(self):
        return f"<CommissionRule(id={self.id}, name='{self.rule_name}', seller={self.seller_commission_percent}%, buyer={self.buyer_commission_percent}%)>"
    
    @property
    def is_currently_effective(self) -> bool:
        """Check if rule is currently effective"""
        # SaaS FIX: Use UTC Standard for boolean logic
        now = datetime.now(timezone.utc)
        
        start = self.effective_from.replace(tzinfo=timezone.utc) if self.effective_from and self.effective_from.tzinfo is None else self.effective_from
        end = self.effective_until.replace(tzinfo=timezone.utc) if self.effective_until and self.effective_until.tzinfo is None else self.effective_until

        if start and start > now:
            return False
        if end and end < now:
            return False
        return self.is_active == 1


# ============================================================================
# COMMISSION MODEL
# ============================================================================

class Commission(Base):
    """Commission model - Individual commission charges"""
    __tablename__ = "COMMISSIONS"
    __table_args__ = {'schema': 'SCRAPCY_APP'}
    
    id = Column("ID", Integer, primary_key=True, autoincrement=True)
    auction_id = Column("AUCTION_ID", Integer, nullable=False)
    auction_item_id = Column("AUCTION_ITEM_ID", Integer, nullable=False)
    settlement_id = Column("SETTLEMENT_ID", Integer, ForeignKey("SCRAPCY_APP.SETTLEMENTS.ID"))
    
    # Commission Details
    commission_type = Column("COMMISSION_TYPE", String(50), nullable=False)  # SELLER, BUYER, PLATFORM_FEE
    charged_to_user_id = Column("CHARGED_TO_USER_ID", Integer, nullable=False)
    
    # Calculation
    base_amount = Column("BASE_AMOUNT", Float, nullable=False)
    commission_rate = Column("COMMISSION_RATE", Float, nullable=False)
    commission_amount = Column("COMMISSION_AMOUNT", Float, nullable=False)
    
    # Tax
    gst_rate = Column("GST_RATE", Float, default=18)
    gst_amount = Column("GST_AMOUNT", Float)
    total_commission_with_tax = Column("TOTAL_COMMISSION_WITH_TAX", Float)
    
    # Rule Applied
    commission_rule_id = Column("COMMISSION_RULE_ID", Integer)
    rule_name = Column("RULE_NAME", String(255))
    
    # Status
    status = Column("STATUS", String(50), default="PENDING")
    collected_at = Column("COLLECTED_AT", TIMESTAMP(6))
    payment_id = Column("PAYMENT_ID", Integer)
    
    # Audit
    created_at = Column("CREATED_AT", TIMESTAMP(6), server_default=func.current_timestamp())
    
    # Relationships
    settlement = relationship("Settlement", back_populates="commissions")
    
    def __repr__(self):
        return f"<Commission(id={self.id}, type='{self.commission_type}', amount={self.commission_amount}, status='{self.status}')>"
    
    @property
    def is_collected(self) -> bool:
        return self.status == "COLLECTED"
    
    @property
    def is_pending(self) -> bool:
        return self.status == "PENDING"


# ============================================================================
# SETTLEMENT MODEL
# ============================================================================

class Settlement(Base):
    """Settlement model - Post-auction financial settlement"""
    __tablename__ = "SETTLEMENTS"
    __table_args__ = {'schema': 'SCRAPCY_APP'}
    
    id = Column("ID", Integer, primary_key=True, autoincrement=True)
    auction_id = Column("AUCTION_ID", Integer, ForeignKey("SCRAPCY_APP.AUCTIONS.ID"), nullable=False)
    auction_item_id = Column("AUCTION_ITEM_ID", Integer, ForeignKey("SCRAPCY_APP.AUCTION_ITEMS.ID"), nullable=False)
    winner_user_id = Column("WINNER_USER_ID", Integer, nullable=False)
    seller_user_id = Column("SELLER_USER_ID", Integer, nullable=False)
    
    # Financial Details
    final_bid_amount = Column("FINAL_BID_AMOUNT", Float, nullable=False)
    commission_rate = Column("COMMISSION_RATE", Float)
    commission_amount = Column("COMMISSION_AMOUNT", Float)
    gst_rate = Column("GST_RATE", Float)
    gst_amount = Column("GST_AMOUNT", Float)
    tds_amount = Column("TDS_AMOUNT", Float)
    other_charges = Column("OTHER_CHARGES", Float, default=0)
    
    # Commissions Breakdown
    seller_commission_amount = Column("SELLER_COMMISSION_AMOUNT", Float, default=0)
    seller_commission_gst = Column("SELLER_COMMISSION_GST", Float, default=0)
    buyer_commission_amount = Column("BUYER_COMMISSION_AMOUNT", Float, default=0)
    buyer_commission_gst = Column("BUYER_COMMISSION_GST", Float, default=0)
    total_platform_commission = Column("TOTAL_PLATFORM_COMMISSION", Float, default=0)
    total_platform_gst = Column("TOTAL_PLATFORM_GST", Float, default=0)
    total_platform_revenue = Column("TOTAL_PLATFORM_REVENUE", Float, default=0)
    
    # Payables
    total_buyer_payable = Column("TOTAL_BUYER_PAYABLE", Float, nullable=False)
    total_seller_receivable = Column("TOTAL_SELLER_RECEIVABLE", Float, nullable=False)
    
    # Payment Status
    buyer_payment_status = Column("BUYER_PAYMENT_STATUS", String(50), default="PENDING")
    seller_payout_status = Column("SELLER_PAYOUT_STATUS", String(50), default="PENDING")
    
    # References
    buyer_payment_id = Column("BUYER_PAYMENT_ID", Integer)
    seller_payout_id = Column("SELLER_PAYOUT_ID", Integer)
    
    # Deadlines
    payment_due_date = Column("PAYMENT_DUE_DATE", TIMESTAMP(6))
    payment_completed_at = Column("PAYMENT_COMPLETED_AT", TIMESTAMP(6))
    payout_completed_at = Column("PAYOUT_COMPLETED_AT", TIMESTAMP(6))
    
    # Invoice
    invoice_number = Column("INVOICE_NUMBER", String(100), unique=True)
    invoice_generated_at = Column("INVOICE_GENERATED_AT", TIMESTAMP(6))
    invoice_url = Column("INVOICE_URL", String(500))
    
    # Audit
    created_at = Column("CREATED_AT", TIMESTAMP(6), server_default=func.current_timestamp())
    updated_at = Column("UPDATED_AT", TIMESTAMP(6), onupdate=func.current_timestamp())
    settled_at = Column("SETTLED_AT", TIMESTAMP(6))
    
    # Relationships
    auction = relationship("Auction", back_populates="settlements")
    auction_item = relationship("AuctionItem", back_populates="settlement")
    commissions = relationship("Commission", back_populates="settlement")
    
    def __repr__(self):
        return f"<Settlement(id={self.id}, item_id={self.auction_item_id}, amount={self.final_bid_amount})>"
    
    @property
    def is_buyer_payment_complete(self) -> bool:
        return self.buyer_payment_status == "COMPLETED"
    
    @property
    def is_seller_payout_complete(self) -> bool:
        return self.seller_payout_status == "COMPLETED"
    
    @property
    def is_fully_settled(self) -> bool:
        return self.is_buyer_payment_complete and self.is_seller_payout_complete
    
    @property
    def is_overdue(self) -> bool:
        """Check if payment is overdue based on UTC standard"""
        if not self.payment_due_date:
            return False
        # SaaS FIX: Standardize comparison to UTC aware objects
        now = datetime.now(timezone.utc)
        due_date = self.payment_due_date.replace(tzinfo=timezone.utc) if self.payment_due_date.tzinfo is None else self.payment_due_date
        return due_date < now and not self.is_buyer_payment_complete
