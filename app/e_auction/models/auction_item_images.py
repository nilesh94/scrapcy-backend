from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, SmallInteger
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.connection import Base

class AuctionItemImage(Base):
    """
    Model for storing metadata of images associated with auction lots.
    Table: scrapcy_app.auction_item_images
    """
    __tablename__ = "auction_item_images"
    __table_args__ = {"schema": "scrapcy_app"}

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("SCRAPCY_APP.AUCTION_ITEMS.ID", ondelete="CASCADE"), nullable=False)
    image_url = Column(String(1000), nullable=False)
    file_name = Column(String(255), nullable=False)
    drive_file_id = Column(String(255), unique=True)
    file_size = Column(Integer)
    is_primary = Column(SmallInteger, default=0) # 1 for thumbnail, 0 for gallery
    display_order = Column(Integer, default=0)   # For manual sorting in UI
    created_at = Column(DateTime, server_default=func.now())

    # --- Define the relationship back to the Lot ---
    # This allows SQLAlchemy to associate these images with the AuctionItem model
    item = relationship("AuctionItem", back_populates="images")
