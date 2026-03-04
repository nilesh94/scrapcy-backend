"""
Notification Model
"""
from sqlalchemy import Column, Integer, String, TIMESTAMP
from sqlalchemy.sql import func
from app.database.connection import Base
from datetime import datetime, timezone


class Notification(Base):
    """Notification model - User notifications"""
    __tablename__ = "NOTIFICATIONS"
    __table_args__ = {'schema': 'SCRAPCY_APP'}
    
    id = Column("ID", Integer, primary_key=True, autoincrement=True)
    user_id = Column("USER_ID", Integer, nullable=False)
    
    # Content
    notification_type = Column("NOTIFICATION_TYPE", String(50), nullable=False)
    title = Column("TITLE", String(255))
    message = Column("MESSAGE", String(1000), nullable=False)
    
    # Links
    auction_id = Column("AUCTION_ID", Integer)
    auction_item_id = Column("AUCTION_ITEM_ID", Integer)
    
    # Delivery Channels
    send_email = Column("SEND_EMAIL", Integer, default=0)
    send_sms = Column("SEND_SMS", Integer, default=0)
    send_push = Column("SEND_PUSH", Integer, default=1)
    send_in_app = Column("SEND_IN_APP", Integer, default=1)
    
    # Status
    is_read = Column("IS_READ", Integer, default=0)
    read_at = Column("READ_AT", TIMESTAMP(6))
    
    # Priority
    priority = Column("PRIORITY", String(20), default="NORMAL")  # LOW, NORMAL, HIGH, URGENT
    
    # Audit
    created_at = Column("CREATED_AT", TIMESTAMP(6), server_default=func.current_timestamp())
    sent_at = Column("SENT_AT", TIMESTAMP(6))
    
    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, type='{self.notification_type}', read={self.is_read})>"
    
    @property
    def is_unread(self) -> bool:
        return self.is_read == 0
    
    @property
    def is_urgent(self) -> bool:
        return self.priority == "URGENT"
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = 1
        # SaaS FIX: Use Python UTC now to ensure application-level consistency
        self.read_at = datetime.now(timezone.utc)
