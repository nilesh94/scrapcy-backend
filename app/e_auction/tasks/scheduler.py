"""
Background Scheduler for Auction Tasks
Auto-publish, auto-close auctions, send notifications
Uses APScheduler - lightweight and efficient
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List
import logging

from app.database.connection import SessionLocal
from app.e_auction.models import Auction, AuctionItem
from app.e_auction.utils.enums import AuctionStatus, ApprovalStatus, LotStatus
from app.e_auction.services.notification_commission_scheduler import NotificationService
from app.e_auction.utils.enums import NotificationType
from app.e_auction.config import settings

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def check_and_publish_auctions():
    """
    Check for auctions that should be published (made LIVE)
    Runs every minute in production, every 60 seconds in local
    """
    db = SessionLocal()
    try:
        # SaaS FIX: Use UTC-aware now for publishing logic
        now = datetime.now(timezone.utc)
        
        # Find auctions ready to publish
        auctions = db.query(Auction).filter(
            Auction.status == AuctionStatus.SCHEDULED,
            Auction.approval_status == ApprovalStatus.L2_APPROVED,
            Auction.scheduled_start_time <= now,
            Auction.actual_start_time == None
        ).all()
        
        published_count = 0
        for auction in auctions:
            try:
                # Publish auction
                auction.status = AuctionStatus.LIVE
                auction.actual_start_time = now
                auction.published_at = now
                auction.updated_at = now
                
                db.commit()
                published_count += 1
                
                logger.info(f"✅ Published auction {auction.id}: {auction.auction_title}")
                
                # TODO: Send notifications to registered participants
                # NotificationService.create_notification(
                #      db=db,
                #      user_id=participant.user_id,
                #      notification_type=NotificationType.AUCTION_STARTING,
                #      title="Auction Started",
                #      message=f"Auction '{auction.auction_title}' is now live!",
                #      auction_id=auction.id
                # )
                
            except Exception as e:
                db.rollback()
                logger.error(f"❌ Failed to publish auction {auction.id}: {str(e)}")
        
        if published_count > 0:
            logger.info(f"📢 Published {published_count} auctions")
    
    except Exception as e:
        logger.error(f"❌ Error in check_and_publish_auctions: {str(e)}")
    finally:
        db.close()


async def check_and_close_auctions():
    """
    Check for auctions that should be closed
    Runs every 30 seconds in production, every 60 seconds in local
    """
    db = SessionLocal()
    try:
        # SaaS FIX: Use UTC-aware now for closing logic
        now = datetime.now(timezone.utc)
        
        # Find auctions ready to close
        auctions = db.query(Auction).filter(
            Auction.status == AuctionStatus.LIVE,
            Auction.scheduled_end_time <= now,
            Auction.actual_end_time == None
        ).all()
        
        closed_count = 0
        for auction in auctions:
            try:
                # Close auction
                auction.status = AuctionStatus.CLOSED
                auction.actual_end_time = now
                auction.updated_at = now
                
                # Close all lots in this auction
                lots = db.query(AuctionItem).filter(
                    AuctionItem.auction_id == auction.id,
                    AuctionItem.lot_status == LotStatus.LIVE
                ).all()
                
                for lot in lots:
                    if lot.highest_bid_amount:
                        lot.lot_status = LotStatus.SOLD
                        lot.final_sold_price = lot.highest_bid_amount
                    else:
                        lot.lot_status = LotStatus.UNSOLD
                
                db.commit()
                closed_count += 1
                
                logger.info(f"✅ Closed auction {auction.id}: {auction.auction_title}")
                
                # TODO: Create settlements for sold lots
                # TODO: Send notifications to winners
                
            except Exception as e:
                db.rollback()
                logger.error(f"❌ Failed to close auction {auction.id}: {str(e)}")
        
        if closed_count > 0:
            logger.info(f"🏁 Closed {closed_count} auctions")
    
    except Exception as e:
        logger.error(f"❌ Error in check_and_close_auctions: {str(e)}")
    finally:
        db.close()


async def check_auction_extensions():
    """
    Check if any lots need time extension
    Runs every 10 seconds
    """
    db = SessionLocal()
    try:
        # SaaS FIX: Use UTC-aware now for polling extension logic
        now = datetime.now(timezone.utc)
        
        # Find lots that might need extension
        lots = db.query(AuctionItem).join(Auction).filter(
            Auction.status == AuctionStatus.LIVE,
            Auction.enable_extension == 1,
            AuctionItem.lot_status == LotStatus.LIVE,
            AuctionItem.extension_count < Auction.MAX_AUCTION_EXTENSIONS
        ).all()
        
        extended_count = 0
        for lot in lots:
            try:
                # Check if bid was placed in trigger window
                if lot.last_bid_time:
                    auction = db.query(Auction).filter(Auction.id == lot.auction_id).first()
                    
                    # SaaS FIX: Ensure naive last_bid_time is treated as UTC
                    last_bid_utc = lot.last_bid_time.replace(tzinfo=timezone.utc) if lot.last_bid_time.tzinfo is None else lot.last_bid_time
                    time_since_last_bid = (now - last_bid_utc).total_seconds()
                    trigger_window = (auction.extension_trigger_window_minutes or 0) * 60
                    
                    # SaaS FIX: Ensure naive lot_end_time is treated as UTC
                    lot_end_utc = lot.lot_end_time.replace(tzinfo=timezone.utc) if lot.lot_end_time.tzinfo is None else lot.lot_end_time
                    time_until_end = (lot_end_utc - now).total_seconds()
                    
                    if time_until_end > 0 and time_until_end < trigger_window and time_since_last_bid < trigger_window:
                        # Extend the auction
                        from datetime import timedelta
                        lot.lot_end_time = lot_end_utc + timedelta(minutes=auction.extension_duration_minutes)
                        lot.extension_count = (lot.extension_count or 0) + 1
                        
                        db.commit()
                        extended_count += 1
                        
                        logger.info(f"⏰ Extended lot {lot.id} by {auction.extension_duration_minutes} minutes")
                        
                        # TODO: Send notification about extension
                
            except Exception as e:
                db.rollback()
                logger.error(f"❌ Failed to extend lot {lot.id}: {str(e)}")
        
        if extended_count > 0:
            logger.info(f"⏰ Extended {extended_count} lots")
    
    except Exception as e:
        logger.error(f"❌ Error in check_auction_extensions: {str(e)}")
    finally:
        db.close()


async def process_pending_notifications():
    """
    Process pending notifications (email, SMS)
    Runs every 5 minutes
    """
    db = SessionLocal()
    try:
        from app.e_auction.models import Notification
        
        # Get unsent notifications
        notifications = db.query(Notification).filter(
            Notification.sent_at == None
        ).limit(settings.NOTIFICATION_BATCH_SIZE).all()
        
        sent_count = 0
        for notification in notifications:
            try:
                # Send email if enabled
                if notification.send_email and settings.EMAIL_ENABLED:
                    # TODO: Send email
                    pass
                
                # Send SMS if enabled
                if notification.send_sms and settings.SMS_ENABLED:
                    # TODO: Send SMS
                    pass
                
                # Mark as sent
                # SaaS FIX: Use UTC-aware timestamp for notification audit
                notification.sent_at = datetime.now(timezone.utc)
                db.commit()
                sent_count += 1
                
            except Exception as e:
                db.rollback()
                logger.error(f"❌ Failed to send notification {notification.id}: {str(e)}")
        
        if sent_count > 0:
            logger.info(f"📧 Sent {sent_count} notifications")
    
    except Exception as e:
        logger.error(f"❌ Error in process_pending_notifications: {str(e)}")
    finally:
        db.close()


def start_scheduler():
    """Start the background scheduler"""
    global scheduler
    
    if not settings.SCHEDULER_ENABLED:
        logger.info("⏸️  Scheduler disabled in configuration")
        return
    
    scheduler = AsyncIOScheduler()
    
    # Add jobs
    interval = settings.scheduler_interval
    
    # Check auctions to publish (every minute in prod, 60s in local)
    scheduler.add_job(
        check_and_publish_auctions,
        trigger=IntervalTrigger(seconds=interval),
        id='check_publish_auctions',
        name='Check and publish auctions',
        replace_existing=True
    )
    
    # Check auctions to close (every 30s in prod, 60s in local)
    scheduler.add_job(
        check_and_close_auctions,
        trigger=IntervalTrigger(seconds=interval),
        id='check_close_auctions',
        name='Check and close auctions',
        replace_existing=True
    )
    
    # Check auction extensions (every 10s)
    if not settings.is_local():
        scheduler.add_job(
            check_auction_extensions,
            trigger=IntervalTrigger(seconds=10),
            id='check_extensions',
            name='Check auction extensions',
            replace_existing=True
        )
    
    # Process notifications (every 5 minutes)
    scheduler.add_job(
        process_pending_notifications,
        trigger=IntervalTrigger(minutes=5),
        id='process_notifications',
        name='Process pending notifications',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(f"✅ Scheduler started (interval: {interval}s)")


def stop_scheduler():
    """Stop the background scheduler"""
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("🛑 Scheduler stopped")
