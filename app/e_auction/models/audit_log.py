"""
Audit Log Model
File: app/e_auction/models/audit_log.py
"""
from sqlalchemy import Column, Integer, String, CLOB, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone

from app.database.connection import Base


class AuditLog(Base):
    """
    Audit trail for all auction-related actions
    Tracks who did what, when, why, and how
    """
    __tablename__ = "AUCTION_AUDIT_LOGS"
    __table_args__ = {'schema': 'SCRAPCY_APP'}
    
    # Primary key
    id = Column("ID", Integer, primary_key=True, index=True)
    
    # Which auction
    auction_id = Column("AUCTION_ID", Integer, ForeignKey("SCRAPCY_APP.AUCTIONS.ID", ondelete="CASCADE"), nullable=False, index=True)
    
    # What action
    action = Column("ACTION", String(50), nullable=False, index=True)
    # Examples: CREATED, UPDATED, DELETED, ARCHIVED, RESTORED,
    #            SUBMITTED, APPROVED_L1, APPROVED_L2, REJECTED,
    #            PUBLISHED, CLOSED, CANCELLED
    
    action_type = Column("ACTION_TYPE", String(50))  # Optional: UPDATE_FIELD, APPROVAL, STATUS_CHANGE
    
    # Who performed the action

    performed_by = Column("PERFORMED_BY", Integer, ForeignKey("USERS.ID"), nullable=False, index=True)
    performed_by_name = Column("PERFORMED_BY_NAME", String(255))  # Cache name for faster display
    
    # When
    # SaaS FIX: Use timezone-aware UTC default for immutable audit tracking
    timestamp = Column("TIMESTAMP", TIMESTAMP(6), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    
    # What changed (JSON format)
    changes = Column("CHANGES", CLOB)
    # Format: {"field_name": {"old_value": "x", "new_value": "y"}}
    # Example: {"status": {"old_value": "DRAFT", "new_value": "LIVE"}}
    
    # Why (required for DELETE, ARCHIVE, REJECT)
    reason = Column("REASON", CLOB)
    
    # Additional remarks
    remarks = Column("REMARKS", CLOB)
    
    # Metadata for security/compliance
    ip_address = Column("IP_ADDRESS", String(50))
    user_agent = Column("USER_AGENT", CLOB)
    
    # Relationships
    # Note: Ensure the "Auction" and "User" models are also imported or 
    # discovered by SQLAlchemy to avoid relationship mapping errors.
    auction = relationship("Auction", back_populates="audit_logs")
    
    user = relationship("User")
    
    def __repr__(self):
        return f"<AuditLog {self.action} on Auction {self.auction_id} by User {self.performed_by}>"
