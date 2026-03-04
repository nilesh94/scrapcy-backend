import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.e_auction.models.auction import Auction
from app.e_auction.models.approval import AuctionApprovalLog
from app.e_auction.utils.enums import AuctionStatus, ApprovalStatus
from app.e_auction.websockets.bid_handler import broadcast_auction_started, broadcast_auction_ended

logger = logging.getLogger(__name__)

async def auction_status_monitor():
    """
    High-precision monitor for automated status transitions.
    """
    while True:
        db = SessionLocal()
        try:
            # SaaS Standard: Current time in aware UTC for cross-regional synchronization
            now = datetime.now(timezone.utc)

            # --- 1. GO LIVE LOGIC (SCHEDULED -> LIVE) ---
            ready_to_live = db.query(Auction).filter(
                Auction.status == AuctionStatus.SCHEDULED,
                Auction.approval_status == ApprovalStatus.PUBLISHED,
                Auction.scheduled_start_time <= now
            ).all()

            for auction in ready_to_live:
                from_status = auction.status
                auction.status = AuctionStatus.LIVE #
                auction.actual_start_time = now #
                auction.updated_at = now #

                # Immutable Audit Log Entry
                db.add(AuctionApprovalLog(
                    auction_id=auction.id,
                    action_by=0, # System User
                    action_by_role="SYSTEM",
                    action="GO_LIVE",
                    from_status=from_status,
                    to_status=AuctionStatus.LIVE,
                    comments="Auto: scheduled_start_time reached"
                ))
                logger.info(f"🚀 Auction {auction.id} is now LIVE.")
                await broadcast_auction_started(auction.id)

            # --- 2. CLOSE LOGIC (LIVE -> CLOSED) ---
            ready_to_close = db.query(Auction).filter(
                Auction.status == AuctionStatus.LIVE,
                Auction.approval_status == ApprovalStatus.PUBLISHED,
                Auction.scheduled_end_time <= now
            ).all()

            for auction in ready_to_close:
                from_status = auction.status
                auction.status = AuctionStatus.CLOSED #
                auction.actual_end_time = now #
                auction.updated_at = now #

                # Immutable Audit Log Entry
                db.add(AuctionApprovalLog(
                    auction_id=auction.id,
                    action_by=0,
                    action_by_role="SYSTEM",
                    action="CLOSE",
                    from_status=from_status,
                    to_status=AuctionStatus.CLOSED,
                    comments="Auto: scheduled_end_time reached"
                ))
                logger.info(f"🏁 Auction {auction.id} is now CLOSED.")
                await broadcast_auction_ended(auction.id)

            db.commit()
        except Exception as e:
            logger.error(f"❌ Status Monitor Error: {e}")
            db.rollback()
        finally:
            db.close()
        
        await asyncio.sleep(30) # Poll interval
