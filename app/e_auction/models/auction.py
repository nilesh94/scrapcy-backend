"""
Auction SQLAlchemy Model
Represents the main auction event
"""
from sqlalchemy import Column, Integer, String, Float, TIMESTAMP, CLOB, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base


class Auction(Base):
    """Auction model - Main auction event"""
    __tablename__ = "AUCTIONS"
    __table_args__ = {'schema': 'SCRAPCY_APP'}
    
    # Primary Key
    id = Column("ID", Integer, primary_key=True, index=True, autoincrement=True)

    # seller_id: The actual owner (Company/Seller) of the auction
    seller_id = Column("SELLER_ID", Integer, nullable=False, index=True)
    
    # Creator
    created_by = Column("CREATED_BY", Integer, nullable=False)
    # Admin approval level (mirrors existing L1/L2 pattern)
    created_by_role = Column("CREATED_BY_ROLE", String(30))
    # Creator role snapshot and submission timestamp
    submitted_at = Column("SUBMITTED_AT", TIMESTAMP(6))
    
    # Auction Details
    auction_title = Column("AUCTION_TITLE", String(255), nullable=False)
    auction_type = Column("AUCTION_TYPE", String(50))  # FORWARD, REVERSE, DUTCH
    category = Column("CATEGORY", String(100))
    region = Column("REGION", String(100))
    
    # Status & Workflow
    status = Column("STATUS", String(50), default="DRAFT")
    approval_status = Column("APPROVAL_STATUS", String(50), default="PENDING")
    
    # L1 Approval
    publish_l1_approved_by = Column("PUBLISH_L1_APPROVED_BY", Integer)
    publish_l1_approved_at = Column("PUBLISH_L1_APPROVED_AT", TIMESTAMP(6))
    publish_l1_remarks = Column("PUBLISH_L1_REMARKS", String(500))
    
    # L2 Approval
    publish_l2_approved_by = Column("PUBLISH_L2_APPROVED_BY", Integer)
    publish_l2_approved_at = Column("PUBLISH_L2_APPROVED_AT", TIMESTAMP(6))
    publish_l2_remarks = Column("PUBLISH_L2_REMARKS", String(500))
    
    # Admin approval level (mirrors existing L1/L2 pattern)
    publish_admin_approved_by = Column("PUBLISH_ADMIN_APPROVED_BY", Integer)
    publish_admin_approved_at = Column("PUBLISH_ADMIN_APPROVED_AT", TIMESTAMP(6))
    publish_admin_remarks = Column("PUBLISH_ADMIN_REMARKS", String(500))
    
    # Scheduling
    scheduled_start_time = Column("SCHEDULED_START_TIME", TIMESTAMP(6))
    scheduled_end_time = Column("SCHEDULED_END_TIME", TIMESTAMP(6))
    actual_start_time = Column("ACTUAL_START_TIME", TIMESTAMP(6))
    actual_end_time = Column("ACTUAL_END_TIME", TIMESTAMP(6))
    published_at = Column("PUBLISHED_AT", TIMESTAMP(6))
    
    # Financial Requirements
    currency = Column("CURRENCY", String(10), default="INR")
    emd_amount = Column("EMD_AMOUNT", Float)
    registration_fee = Column("REGISTRATION_FEE", Float)
    
    # Extension Settings
    enable_extension = Column("ENABLE_EXTENSION", Integer, default=0)
    extension_trigger_window_minutes = Column("EXTENSION_TRIGGER_WINDOW_MINUTES", Integer, default=5)
    extension_duration_minutes = Column("EXTENSION_DURATION_MINUTES", Integer, default=5)
    extension_min_total_bids = Column("EXTENSION_MIN_TOTAL_BIDS", Integer, default=1)
    global_extension_minutes = Column("GLOBAL_EXTENSION_MINUTES", Integer, default=0)
    
    # Inspection Details
    inspection_start_date = Column("INSPECTION_START_DATE", TIMESTAMP(6))
    inspection_end_date = Column("INSPECTION_END_DATE", TIMESTAMP(6))
    inspection_location = Column("INSPECTION_LOCATION", String(500))
    inspection_contact_person = Column("INSPECTION_CONTACT_PERSON", String(255))
    inspection_contact_number = Column("INSPECTION_CONTACT_NUMBER", String(20))
    
    # Documents
    terms_and_conditions = Column("TERMS_AND_CONDITIONS", CLOB)
    auction_doc_url = Column("AUCTION_DOC_URL", String(500))
    
    # Analytics
    view_count = Column("VIEW_COUNT", Integer, default=0)
    is_featured = Column("IS_FEATURED", Integer, default=0)
    total_lots = Column("TOTAL_LOTS", Integer, default=0)
    
    # Cancellation
    cancelled_at = Column("CANCELLED_AT", TIMESTAMP(6))
    cancellation_reason = Column("CANCELLATION_REASON", String(500))
    
    # Audit
    created_at = Column("CREATED_AT", TIMESTAMP(6), server_default=func.current_timestamp())
    updated_at = Column("UPDATED_AT", TIMESTAMP(6), onupdate=func.current_timestamp())
    
    # Relationships
    items = relationship("AuctionItem", back_populates="auction", cascade="all, delete-orphan")
    participants = relationship("AuctionParticipant", back_populates="auction", cascade="all, delete-orphan")
    bids = relationship("Bid", back_populates="auction")
    payments = relationship("Payment", back_populates="auction")
    settlements = relationship("Settlement", back_populates="auction")
    # ABSOLUTELY REQUIRED FIX: Added the matching audit_logs relationship
    audit_logs = relationship("AuditLog", back_populates="auction", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Auction(id={self.id}, title='{self.auction_title}', status='{self.status}')>"
    
    @property
    def is_live(self) -> bool:
        """Check if auction is currently live"""
        return self.status == "LIVE"
    
    @property
    def is_approved(self) -> bool:
        """Check if auction is fully approved (L1 and L2)"""
        return self.approval_status == "L2_APPROVED"
    
    @property
    def can_be_edited(self) -> bool:
        """Check if auction can be edited"""
        return self.status in ["DRAFT", "PENDING_APPROVAL"]
    
    @property
    def requires_emd(self) -> bool:
        """Check if EMD is required"""
        return self.emd_amount is not None and self.emd_amount > 0
    
    @property
    def requires_registration_fee(self) -> bool:
        """Check if registration fee is required"""
        return self.registration_fee is not None and self.registration_fee > 0
