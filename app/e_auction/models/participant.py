"""
Auction Participant SQLAlchemy Model
Tracks user registration and eligibility for specific auctions
"""
from sqlalchemy import Column, Integer, String, Float, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base

class AuctionParticipant(Base):
    """AuctionParticipant model - Maps to SCRAPCY_APP.AUCTION_PARTICIPANTS"""
    __tablename__ = "AUCTION_PARTICIPANTS"
    __table_args__ = {'schema': 'SCRAPCY_APP'}

    # Primary Key
    id = Column("ID", Integer, primary_key=True, index=True, autoincrement=True)

    # Foreign Keys
    auction_id = Column("AUCTION_ID", Integer, ForeignKey("SCRAPCY_APP.AUCTIONS.ID"), nullable=False)
    user_id = Column("USER_ID", Integer, nullable=False, index=True)

    # Financials
    registration_fee_paid = Column("REGISTRATION_FEE_PAID", Float)
    emd_blocked_amount = Column("EMD_BLOCKED_AMOUNT", Float)
    
    # Statuses
    payment_status = Column("PAYMENT_STATUS", String(50)) # e.g., 'SUCCESS', 'PENDING'
    payment_ref_id = Column("PAYMENT_REF_ID", String(255))
    participation_status = Column("PARTICIPATION_STATUS", String(50)) # e.g., 'APPROVED'

    # Verifications
    agreed_to_terms = Column("AGREED_TO_TERMS", Integer, default=0)
    kyc_verified = Column("KYC_VERIFIED", Integer, default=0)
    phone_verified = Column("PHONE_VERIFIED", Integer, default=0)
    email_verified = Column("EMAIL_VERIFIED", Integer, default=0)
    
    # Metadata
    ip_address = Column("IP_ADDRESS", String(50))
    registered_at = Column("REGISTERED_AT", TIMESTAMP(6), server_default=func.current_timestamp())

    # Relationships
    auction = relationship("Auction", back_populates="participants")

    def __repr__(self):
        return f"<AuctionParticipant(auction_id={self.auction_id}, user_id={self.user_id}, status='{self.participation_status}')>"
