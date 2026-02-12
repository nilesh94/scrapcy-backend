"""
Audit Log Model
Add this to: app/e_auction/models/audit_log.py
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database.base import Base


class AuditLog(Base):
    """
    Audit trail for all auction-related actions
    Tracks who did what, when, why, and how
    """
    __tablename__ = "auction_audit_logs"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Which auction
    auction_id = Column(Integer, ForeignKey("auctions.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # What action
    action = Column(String(50), nullable=False, index=True)
    # Examples: CREATED, UPDATED, DELETED, ARCHIVED, RESTORED,
    #           SUBMITTED, APPROVED_L1, APPROVED_L2, REJECTED,
    #           PUBLISHED, CLOSED, CANCELLED
    
    action_type = Column(String(50))  # Optional: UPDATE_FIELD, APPROVAL, STATUS_CHANGE
    
    # Who performed the action
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    performed_by_name = Column(String(255))  # Cache name for faster display
    
    # When
    timestamp = Column(DateTime, default=datetime.now, nullable=False, index=True)
    
    # What changed (JSON format)
    changes = Column(JSON)
    # Format: {"field_name": {"old_value": "x", "new_value": "y"}}
    # Example: {"status": {"old_value": "DRAFT", "new_value": "LIVE"}}
    
    # Why (required for DELETE, ARCHIVE, REJECT)
    reason = Column(Text)
    
    # Additional remarks
    remarks = Column(Text)
    
    # Metadata for security/compliance
    ip_address = Column(String(50))
    user_agent = Column(Text)
    
    # Relationships
    auction = relationship("Auction", backref="audit_logs")
    user = relationship("User")
    
    def __repr__(self):
        return f"<AuditLog {self.action} on Auction {self.auction_id} by User {self.performed_by}>"
