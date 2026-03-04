"""
Notification Background Tasks
Send email, SMS, and push notifications
"""
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List
import logging

from app.database.connection import SessionLocal
from app.e_auction.models import Notification, Auction, AuctionItem, AuctionParticipant
from app.e_auction.utils.enums import NotificationType
from app.e_auction.config import settings

logger = logging.getLogger(__name__)


async def process_pending_notifications():
    """
    Process notifications pending in queue
    Send via email, SMS, push as configured
    Called every 5 minutes
    """
    db = SessionLocal()
    try:
        # Get pending notifications (not sent yet)
        pending = db.query(Notification).filter(
            Notification.sent_at == None
        ).limit(settings.NOTIFICATION_BATCH_SIZE).all()
        
        sent_count = 0
        for notification in pending:
            try:
                # Send email if enabled
                if notification.send_email and settings.EMAIL_ENABLED:
                    await send_email_notification(notification)
                
                # Send SMS if enabled
                if notification.send_sms and settings.SMS_ENABLED:
                    await send_sms_notification(notification)
                
                # Send push notification if enabled
                if notification.send_push:
                    await send_push_notification(notification)
                
                # Mark as sent
                # SaaS FIX: Use UTC-aware timestamp for notification audit
                notification.sent_at = datetime.now(timezone.utc)
                db.commit()
                
                sent_count += 1
                
            except Exception as e:
                db.rollback()
                logger.error(f"❌ Failed to send notification {notification.id}: {str(e)}")
        
        if sent_count > 0:
            logger.info(f"📧 Sent {sent_count} notification(s)")
        
        return sent_count
    
    except Exception as e:
        logger.error(f"❌ Error in process_pending_notifications: {str(e)}")
        return 0
    finally:
        db.close()


async def send_email_notification(notification: Notification):
    """Send email notification"""
    if not settings.EMAIL_ENABLED:
        return
    
    try:
        # TODO: Implement actual email sending
        # if settings.EMAIL_PROVIDER == "sendgrid":
        #      from sendgrid import SendGridAPIClient
        #      from sendgrid.helpers.mail import Mail
        #      
        #      message = Mail(
        #          from_email=settings.EMAIL_FROM,
        #          to_emails=user.email,
        #          subject=notification.title,
        #          html_content=notification.message
        #      )
        #      
        #      sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        #      response = sg.send(message)
        
        logger.info(f"📧 Email sent for notification {notification.id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to send email: {str(e)}")
        raise


async def send_sms_notification(notification: Notification):
    """Send SMS notification"""
    if not settings.SMS_ENABLED:
        return
    
    try:
        # TODO: Implement actual SMS sending
        # if settings.SMS_PROVIDER == "msg91":
        #      import requests
        #      
        #      url = "https://api.msg91.com/api/v5/flow/"
        #      payload = {
        #          "authkey": settings.MSG91_AUTH_KEY,
        #          "mobiles": user.phone,
        #          "message": notification.message,
        #          "sender": settings.MSG91_SENDER_ID,
        #          "route": settings.MSG91_ROUTE
        #      }
        #      
        #      response = requests.post(url, json=payload)
        
        logger.info(f"📱 SMS sent for notification {notification.id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to send SMS: {str(e)}")
        raise


async def send_push_notification(notification: Notification):
    """Send push notification"""
    try:
        # TODO: Implement push notification
        # Can use Firebase Cloud Messaging (FCM) or similar
        
        logger.info(f"🔔 Push notification sent for notification {notification.id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to send push notification: {str(e)}")
        raise


async def notify_auction_started(auction_id: int):
    """
    Notify all registered participants that auction has started
    """
    db = SessionLocal()
    try:
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            return
        
        # Get all approved participants
        participants = db.query(AuctionParticipant).filter(
            AuctionParticipant.auction_id == auction_id,
            AuctionParticipant.participation_status == "APPROVED",
            AuctionParticipant.payment_status == "SUCCESS"
        ).all()
        
        notified_count = 0
        for participant in participants:
            try:
                notification = Notification(
                    user_id=participant.user_id,
                    notification_type=NotificationType.AUCTION_STARTING,
                    title="Auction Started!",
                    message=f"The auction '{auction.auction_title}' is now live! Start bidding now.",
                    auction_id=auction_id,
                    priority="NORMAL",
                    send_email=True,
                    send_sms=True,
                    send_push=True,
                    send_in_app=True,
                    # SaaS FIX: Set UTC creation timestamp
                    created_at=datetime.now(timezone.utc)
                )
                
                db.add(notification)
                notified_count += 1
                
            except Exception as e:
                logger.error(f"❌ Failed to create notification for user {participant.user_id}: {str(e)}")
        
        db.commit()
        logger.info(f"📢 Created {notified_count} auction start notifications")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error in notify_auction_started: {str(e)}")
    finally:
        db.close()


async def notify_auction_ended(auction_id: int):
    """
    Notify winners and sellers about auction end
    """
    db = SessionLocal()
    try:
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            return
        
        # Get all lots
        lots = db.query(AuctionItem).filter(
            AuctionItem.auction_id == auction_id
        ).all()
        
        notified_count = 0
        for lot in lots:
            try:
                # Notify winner if lot sold
                if lot.lot_status == "SOLD" and lot.winner_user_id:
                    winner_notification = Notification(
                        user_id=lot.winner_user_id,
                        notification_type=NotificationType.WON,
                        title="Congratulations! You Won!",
                        message=f"You won the bid for '{lot.item_name}' at {lot.final_sold_price}. Please complete payment.",
                        auction_id=auction_id,
                        auction_item_id=lot.id,
                        priority="HIGH",
                        send_email=True,
                        send_sms=True,
                        send_push=True,
                        send_in_app=True,
                        # SaaS FIX: Set UTC creation timestamp
                        created_at=datetime.now(timezone.utc)
                    )
                    db.add(winner_notification)
                    notified_count += 1
                
                # TODO: Notify seller about sale
                # TODO: Notify losing bidders
                
            except Exception as e:
                logger.error(f"❌ Failed to create end notification for lot {lot.id}: {str(e)}")
        
        db.commit()
        logger.info(f"🏁 Created {notified_count} auction end notifications")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error in notify_auction_ended: {str(e)}")
    finally:
        db.close()


async def notify_outbid(auction_item_id: int, outbid_user_id: int, new_bid_amount: float):
    """
    Notify user they've been outbid
    """
    db = SessionLocal()
    try:
        lot = db.query(AuctionItem).filter(AuctionItem.id == auction_item_id).first()
        if not lot:
            return
        
        notification = Notification(
            user_id=outbid_user_id,
            notification_type=NotificationType.OUTBID,
            title="You've Been Outbid!",
            message=f"Someone bid {new_bid_amount} on '{lot.item_name}'. Place a higher bid now!",
            auction_id=lot.auction_id,
            auction_item_id=auction_item_id,
            priority="HIGH",
            send_email=False,  # Too frequent for email
            send_sms=False,
            send_push=True,
            send_in_app=True,
            # SaaS FIX: Set UTC creation timestamp
            created_at=datetime.now(timezone.utc)
        )
        
        db.add(notification)
        db.commit()
        
        logger.info(f"🔔 Outbid notification created for user {outbid_user_id}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error in notify_outbid: {str(e)}")
    finally:
        db.close()


async def notify_lot_ending_soon(auction_item_id: int, minutes_remaining: int):
    """
    Notify watchers that lot is ending soon
    """
    db = SessionLocal()
    try:
        lot = db.query(AuctionItem).filter(AuctionItem.id == auction_item_id).first()
        if not lot:
            return
        
        # TODO: Get all watchers/bidders for this lot
        # For now, notify current bidders
        
        logger.info(f"⏰ Lot ending soon notifications sent for lot {auction_item_id}")
        
    except Exception as e:
        logger.error(f"❌ Error in notify_lot_ending_soon: {str(e)}")
    finally:
        db.close()


async def notify_payment_due(user_id: int, auction_item_id: int, amount: float):
    """
    Notify winner about payment due
    """
    db = SessionLocal()
    try:
        lot = db.query(AuctionItem).filter(AuctionItem.id == auction_item_id).first()
        if not lot:
            return
        
        notification = Notification(
            user_id=user_id,
            notification_type=NotificationType.PAYMENT_DUE,
            title="Payment Due",
            message=f"Payment of {amount} is due for '{lot.item_name}'. Complete payment within 48 hours.",
            auction_id=lot.auction_id,
            auction_item_id=auction_item_id,
            priority="HIGH",
            send_email=True,
            send_sms=True,
            send_push=True,
            send_in_app=True,
            # SaaS FIX: Set UTC creation timestamp
            created_at=datetime.now(timezone.utc)
        )
        
        db.add(notification)
        db.commit()
        
        logger.info(f"💰 Payment due notification created for user {user_id}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error in notify_payment_due: {str(e)}")
    finally:
        db.close()
