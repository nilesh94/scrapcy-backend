"""
Notification Service
Send notifications via multiple channels
Configured via ENV
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.e_auction.models import Notification
from app.e_auction.utils.enums import NotificationType, NotificationPriority
from app.e_auction.config import settings


class NotificationService:
    """Notification service - multi-channel notifications"""
    
    @staticmethod
    def create_notification(
        db: Session,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        auction_id: Optional[int] = None,
        auction_item_id: Optional[int] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        send_email: bool = False,
        send_sms: bool = False
    ) -> Notification:
        """Create and optionally send notification"""
        
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            auction_id=auction_id,
            auction_item_id=auction_item_id,
            priority=priority,
            send_email=send_email and settings.EMAIL_ENABLED,
            send_sms=send_sms and settings.SMS_ENABLED,
            send_push=True,
            send_in_app=True,
            # SaaS FIX: Use UTC for creation timestamp
            created_at=datetime.now(timezone.utc)
        )
        
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        # TODO: Async send via queue
        # if send_email: send_email_task.delay(notification.id)
        # if send_sms: send_sms_task.delay(notification.id)
        
        return notification
    
    @staticmethod
    def mark_as_read(db: Session, notification_id: int, user_id: int) -> bool:
        """Mark notification as read"""
        notification = db.query(Notification).filter(
            and_(
                Notification.id == notification_id,
                Notification.user_id == user_id
            )
        ).first()
        
        if notification:
            notification.is_read = 1
            # SaaS FIX: Use UTC for read timestamp
            notification.read_at = datetime.now(timezone.utc)
            db.commit()
            return True
        return False
    
    @staticmethod
    def get_user_notifications(
        db: Session,
        user_id: int,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 20
    ) -> List[Notification]:
        """Get user notifications"""
        query = db.query(Notification).filter(Notification.user_id == user_id)
        
        if unread_only:
            query = query.filter(Notification.is_read == 0)
        
        skip = (page - 1) * page_size
        return query.order_by(Notification.created_at.desc()).offset(skip).limit(page_size).all()


class CommissionService:
    """Commission calculation and management"""
    
    @staticmethod
    def calculate_commission(
        db: Session,
        final_bid_amount: float,
        category: Optional[str] = None
    ) -> dict:
        """
        Calculate commission based on rules
        Returns: dict with seller_commission, buyer_commission, gst, totals
        """
        from app.e_auction.models import CommissionRule
        from sqlalchemy import and_
        
        # SaaS FIX: Use UTC for rule effectivity check
        now = datetime.now(timezone.utc)
        
        # Get applicable rule (highest priority first)
        rule = db.query(CommissionRule).filter(
            and_(
                CommissionRule.is_active == 1,
                CommissionRule.effective_from <= now,
                (CommissionRule.effective_until == None) | (CommissionRule.effective_until >= now)
            )
        ).order_by(CommissionRule.priority.desc()).first()
        
        # Use default if no rule found
        seller_rate = rule.seller_commission_percent if rule else settings.DEFAULT_SELLER_COMMISSION_PERCENT
        buyer_rate = rule.buyer_commission_percent if rule else settings.DEFAULT_BUYER_COMMISSION_PERCENT
        gst_rate = settings.GST_RATE_PERCENT
        
        # Calculate
        seller_commission = (final_bid_amount * seller_rate) / 100
        seller_gst = (seller_commission * gst_rate) / 100
        seller_total = seller_commission + seller_gst
        
        buyer_commission = (final_bid_amount * buyer_rate) / 100
        buyer_gst = (buyer_commission * gst_rate) / 100
        buyer_total = buyer_commission + buyer_gst
        
        platform_revenue = seller_total + buyer_total
        seller_receives = final_bid_amount - seller_total
        buyer_pays = final_bid_amount + buyer_total
        
        return {
            'base_amount': final_bid_amount,
            'seller_commission_rate': seller_rate,
            'seller_commission_amount': seller_commission,
            'seller_gst_amount': seller_gst,
            'seller_total': seller_total,
            'buyer_commission_rate': buyer_rate,
            'buyer_commission_amount': buyer_commission,
            'buyer_gst_amount': buyer_gst,
            'buyer_total': buyer_total,
            'total_platform_revenue': platform_revenue,
            'seller_receives': seller_receives,
            'buyer_pays': buyer_pays,
            'rule_applied': rule
        }


class SchedulerService:
    """Background job scheduler for auction operations"""
    
    @staticmethod
    def check_auctions_to_publish(db: Session) -> List[int]:
        """
        Find auctions ready to be published
        Called by scheduler every minute
        """
        from app.e_auction.models import Auction
        from app.e_auction.utils.enums import AuctionStatus, ApprovalStatus
        
        # SaaS FIX: Use UTC for start time comparison
        now = datetime.now(timezone.utc)
        
        auctions = db.query(Auction).filter(
            and_(
                Auction.status == AuctionStatus.SCHEDULED,
                Auction.approval_status == ApprovalStatus.L2_APPROVED,
                Auction.scheduled_start_time <= now,
                Auction.actual_start_time == None
            )
        ).all()
        
        published_ids = []
        for auction in auctions:
            try:
                auction.status = AuctionStatus.LIVE
                auction.actual_start_time = now
                auction.published_at = now
                db.commit()
                published_ids.append(auction.id)
            except:
                db.rollback()
        
        return published_ids
    
    @staticmethod
    def check_auctions_to_close(db: Session) -> List[int]:
        """
        Find auctions that should be closed
        Called by scheduler every 30 seconds
        """
        from app.e_auction.models import Auction
        from app.e_auction.utils.enums import AuctionStatus
        
        # SaaS FIX: Use UTC for end time comparison
        now = datetime.now(timezone.utc)
        
        auctions = db.query(Auction).filter(
            and_(
                Auction.status == AuctionStatus.LIVE,
                Auction.scheduled_end_time <= now,
                Auction.actual_end_time == None
            )
        ).all()
        
        closed_ids = []
        for auction in auctions:
            try:
                auction.status = AuctionStatus.CLOSED
                auction.actual_end_time = now
                db.commit()
                closed_ids.append(auction.id)
                
                # TODO: Create settlements for all sold lots
                
            except:
                db.rollback()
        
        return closed_ids
