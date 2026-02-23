import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.e_auction.models.auction import Auction
from app.e_auction.models.approval import AuctionApprovalLog
from app.e_auction.utils.enums import AuctionStatus, ApprovalAction, ApprovalStatus
from app.e_auction.websockets.bid_handler import broadcast_auction_started

logger = logging.getLogger(__name__)

async def auction_status_monitor():
    """
    High-precision monitor for automated status transitions.
    """
    while True:
        db = SessionLocal()
        try:
            # 1. Find auctions ready to go LIVE [cite: 236-240]
            ready_auctions = db.query(Auction).filter(
                Auction.status == AuctionStatus.SCHEDULED,
                Auction.approval_status == ApprovalStatus.PUBLISHED,
                Auction.scheduled_start_time <= datetime.utcnow()
            ).all()

            for auction in ready_auctions:
                from_status = auction.status
                
                # 2. Operational Update 
                auction.status = AuctionStatus.LIVE
                auction.actual_start_time = datetime.utcnow()
                auction.updated_at = datetime.utcnow()

                # 3. Immutable Audit Log [cite: 247-252]
                log_entry = AuctionApprovalLog(
                    auction_id=auction.id,
                    action_by=0, # 0 represents SYSTEM user
                    action_by_role="SYSTEM",
                    action="GO_LIVE",
                    from_status=from_status,
                    to_status=AuctionStatus.LIVE,
                    comments="Auto: scheduled_start_time reached"
                )
                db.add(log_entry)
                
                logger.info(f"🚀 Auction {auction.id} is now LIVE via System Worker.")
                
                # 4. Trigger Real-time UI refresh
                await broadcast_auction_started(auction.id)
            
            db.commit()
        except Exception as e:
            logger.error(f"❌ Status Monitor Error: {e}")
            db.rollback()
        finally:
            db.close()
        
        await asyncio.sleep(30) # Poll interval
