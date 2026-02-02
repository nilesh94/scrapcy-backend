"""
Auction Background Tasks
Auto-close, auto-publish, and extension handling
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List
import logging

from app.database.connection import SessionLocal
from app.e_auction.models import Auction, AuctionItem
from app.e_auction.utils.enums import AuctionStatus, ApprovalStatus, LotStatus
from app.e_auction.config import settings

logger = logging.getLogger(__name__)


async def publish_scheduled_auctions():
    """
    Find and publish auctions that are ready to go live
    Called by scheduler every minute
    """
    db = SessionLocal()
    try:
        now = datetime.now()
        
        # Find auctions ready to publish
        auctions_to_publish = db.query(Auction).filter(
            Auction.status == AuctionStatus.SCHEDULED,
            Auction.approval_status == ApprovalStatus.L2_APPROVED,
            Auction.scheduled_start_time <= now,
            Auction.actual_start_time == None
        ).all()
        
        published_count = 0
        for auction in auctions_to_publish:
            try:
                # Update auction status
                auction.status = AuctionStatus.LIVE
                auction.actual_start_time = now
                auction.published_at = now
                auction.updated_at = now
                
                # Update all lots to LIVE
                lots = db.query(AuctionItem).filter(
                    AuctionItem.auction_id == auction.id
                ).all()
                
                for lot in lots:
                    lot.lot_status = LotStatus.LIVE
                
                db.commit()
                published_count += 1
                
                logger.info(f"✅ Published auction {auction.id}: {auction.auction_title}")
                
                # TODO: Send notifications to registered participants
                # from app.e_auction.tasks.notification_tasks import notify_auction_started
                # await notify_auction_started(auction.id)
                
            except Exception as e:
                db.rollback()
                logger.error(f"❌ Failed to publish auction {auction.id}: {str(e)}")
        
        if published_count > 0:
            logger.info(f"📢 Successfully published {published_count} auction(s)")
        
        return published_count
    
    except Exception as e:
        logger.error(f"❌ Error in publish_scheduled_auctions: {str(e)}")
        return 0
    finally:
        db.close()


async def close_ended_auctions():
    """
    Find and close auctions that have ended
    Called by scheduler every 30 seconds
    """
    db = SessionLocal()
    try:
        now = datetime.now()
        
        # Find auctions to close
        auctions_to_close = db.query(Auction).filter(
            Auction.status == AuctionStatus.LIVE,
            Auction.scheduled_end_time <= now,
            Auction.actual_end_time == None
        ).all()
        
        closed_count = 0
        for auction in auctions_to_close:
            try:
                # Close auction
                auction.status = AuctionStatus.CLOSED
                auction.actual_end_time = now
                auction.updated_at = now
                
                # Close all lots
                lots = db.query(AuctionItem).filter(
                    AuctionItem.auction_id == auction.id,
                    AuctionItem.lot_status == LotStatus.LIVE
                ).all()
                
                for lot in lots:
                    # Mark as SOLD if has winner, else UNSOLD
                    if lot.highest_bid_amount and lot.winner_user_id:
                        lot.lot_status = LotStatus.SOLD
                        lot.final_sold_price = lot.highest_bid_amount
                    else:
                        lot.lot_status = LotStatus.UNSOLD
                
                db.commit()
                closed_count += 1
                
                logger.info(f"✅ Closed auction {auction.id}: {auction.auction_title}")
                
                # TODO: Trigger settlement creation
                # from app.e_auction.tasks.settlement_tasks import create_settlements_for_auction
                # await create_settlements_for_auction(auction.id)
                
                # TODO: Send notifications to winners and sellers
                # from app.e_auction.tasks.notification_tasks import notify_auction_ended
                # await notify_auction_ended(auction.id)
                
            except Exception as e:
                db.rollback()
                logger.error(f"❌ Failed to close auction {auction.id}: {str(e)}")
        
        if closed_count > 0:
            logger.info(f"🏁 Successfully closed {closed_count} auction(s)")
        
        return closed_count
    
    except Exception as e:
        logger.error(f"❌ Error in close_ended_auctions: {str(e)}")
        return 0
    finally:
        db.close()


async def process_auction_extensions():
    """
    Check if any lots need time extension due to late bids
    Called by scheduler every 10 seconds
    """
    db = SessionLocal()
    try:
        now = datetime.now()
        
        # Find lots that might need extension
        live_lots = db.query(AuctionItem).join(Auction).filter(
            Auction.status == AuctionStatus.LIVE,
            Auction.enable_extension == 1,
            AuctionItem.lot_status == LotStatus.LIVE,
            AuctionItem.extension_count < settings.MAX_AUCTION_EXTENSIONS
        ).all()
        
        extended_count = 0
        for lot in live_lots:
            try:
                # Check if bid was placed within trigger window
                if lot.last_bid_time:
                    auction = db.query(Auction).filter(Auction.id == lot.auction_id).first()
                    
                    # Calculate time until lot ends
                    time_until_end = (lot.lot_end_time - now).total_seconds()
                    
                    # Calculate trigger window in seconds
                    trigger_window = auction.extension_trigger_window_minutes * 60
                    
                    # If lot is within trigger window and has recent bid
                    if 0 < time_until_end < trigger_window:
                        time_since_last_bid = (now - lot.last_bid_time).total_seconds()
                        
                        # If bid was placed in trigger window, extend
                        if time_since_last_bid < trigger_window:
                            # Check minimum bids requirement
                            if lot.total_bids_count >= (auction.extension_min_total_bids or 1):
                                # Extend the lot
                                extension_minutes = auction.extension_duration_minutes
                                lot.lot_end_time = lot.lot_end_time + timedelta(minutes=extension_minutes)
                                lot.extension_count = (lot.extension_count or 0) + 1
                                
                                db.commit()
                                extended_count += 1
                                
                                logger.info(
                                    f"⏰ Extended lot {lot.id} ({lot.item_name}) "
                                    f"by {extension_minutes} minutes "
                                    f"(extension #{lot.extension_count})"
                                )
                                
                                # TODO: Send extension notification via WebSocket
                                # from app.e_auction.websockets.bid_handler import broadcast_extension
                                # await broadcast_extension(lot.id, extension_minutes)
                
            except Exception as e:
                db.rollback()
                logger.error(f"❌ Failed to extend lot {lot.id}: {str(e)}")
        
        if extended_count > 0:
            logger.info(f"⏰ Successfully extended {extended_count} lot(s)")
        
        return extended_count
    
    except Exception as e:
        logger.error(f"❌ Error in process_auction_extensions: {str(e)}")
        return 0
    finally:
        db.close()


async def send_closing_warnings():
    """
    Send warnings for lots closing soon (within 60 seconds)
    Called by scheduler every 30 seconds
    """
    db = SessionLocal()
    try:
        now = datetime.now()
        warning_window = now + timedelta(seconds=60)
        
        # Find lots closing soon
        closing_lots = db.query(AuctionItem).join(Auction).filter(
            Auction.status == AuctionStatus.LIVE,
            AuctionItem.lot_status == LotStatus.LIVE,
            AuctionItem.lot_end_time <= warning_window,
            AuctionItem.lot_end_time > now
        ).all()
        
        warned_count = 0
        for lot in closing_lots:
            try:
                # TODO: Send WebSocket notification
                # from app.e_auction.websockets.bid_handler import broadcast_closing_warning
                # await broadcast_closing_warning(lot.id)
                
                warned_count += 1
                logger.debug(f"⚠️ Sent closing warning for lot {lot.id}")
                
            except Exception as e:
                logger.error(f"❌ Failed to send warning for lot {lot.id}: {str(e)}")
        
        if warned_count > 0:
            logger.info(f"⚠️ Sent closing warnings for {warned_count} lot(s)")
        
        return warned_count
    
    except Exception as e:
        logger.error(f"❌ Error in send_closing_warnings: {str(e)}")
        return 0
    finally:
        db.close()


async def cleanup_expired_drafts():
    """
    Cleanup draft auctions older than 30 days
    Called daily
    """
    db = SessionLocal()
    try:
        cutoff_date = datetime.now() - timedelta(days=30)
        
        # Find old draft auctions
        old_drafts = db.query(Auction).filter(
            Auction.status == AuctionStatus.DRAFT,
            Auction.created_at < cutoff_date
        ).all()
        
        deleted_count = 0
        for auction in old_drafts:
            try:
                # Delete associated lots
                db.query(AuctionItem).filter(
                    AuctionItem.auction_id == auction.id
                ).delete()
                
                # Delete auction
                db.delete(auction)
                db.commit()
                
                deleted_count += 1
                logger.info(f"🗑️ Deleted old draft auction {auction.id}")
                
            except Exception as e:
                db.rollback()
                logger.error(f"❌ Failed to delete draft {auction.id}: {str(e)}")
        
        if deleted_count > 0:
            logger.info(f"🗑️ Cleaned up {deleted_count} old draft(s)")
        
        return deleted_count
    
    except Exception as e:
        logger.error(f"❌ Error in cleanup_expired_drafts: {str(e)}")
        return 0
    finally:
        db.close()
