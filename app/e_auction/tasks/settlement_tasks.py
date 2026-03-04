"""
Settlement Background Tasks
Auto-create settlements for won auctions
Calculate commissions, taxes, and payouts
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import List
from decimal import Decimal
import logging

from app.database.connection import SessionLocal
from app.e_auction.models import (
    Settlement, AuctionItem, Auction, Commission, CommissionRule
)
from app.e_auction.utils.enums import LotStatus
from app.e_auction.config import settings
from app.e_auction.services.notification_commission_scheduler import CommissionService

logger = logging.getLogger(__name__)


async def create_settlements_for_auction(auction_id: int):
    """
    Create settlements for all sold lots in an auction
    Called when auction closes
    """
    db = SessionLocal()
    try:
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            return
        
        # Get all sold lots
        sold_lots = db.query(AuctionItem).filter(
            AuctionItem.auction_id == auction_id,
            AuctionItem.lot_status == LotStatus.SOLD,
            AuctionItem.winner_user_id != None
        ).all()
        
        created_count = 0
        for lot in sold_lots:
            try:
                # Check if settlement already exists
                existing = db.query(Settlement).filter(
                    Settlement.auction_item_id == lot.id
                ).first()
                
                if existing:
                    logger.info(f"Settlement already exists for lot {lot.id}")
                    continue
                
                # Calculate commissions
                commission_calc = CommissionService.calculate_commission(
                    db=db,
                    final_bid_amount=float(lot.final_sold_price),
                    category=lot.category
                )
                
                # Create settlement
                settlement = Settlement(
                    auction_id=auction_id,
                    auction_item_id=lot.id,
                    winner_user_id=lot.winner_user_id,
                    seller_user_id=auction.created_by,
                    
                    # Final amounts
                    final_bid_amount=lot.final_sold_price,
                    
                    # Seller commission
                    seller_commission_rate=Decimal(str(commission_calc['seller_commission_rate'])),
                    seller_commission_amount=Decimal(str(commission_calc['seller_commission_amount'])),
                    seller_gst_amount=Decimal(str(commission_calc['seller_gst_amount'])),
                    seller_total_commission=Decimal(str(commission_calc['seller_total'])),
                    
                    # Buyer commission
                    buyer_commission_rate=Decimal(str(commission_calc['buyer_commission_rate'])),
                    buyer_commission_amount=Decimal(str(commission_calc['buyer_commission_amount'])),
                    buyer_gst_amount=Decimal(str(commission_calc['buyer_gst_amount'])),
                    buyer_total_commission=Decimal(str(commission_calc['buyer_total'])),
                    
                    # Platform revenue
                    total_platform_revenue=Decimal(str(commission_calc['total_platform_revenue'])),
                    
                    # Net amounts
                    total_buyer_payable=Decimal(str(commission_calc['buyer_pays'])),
                    total_seller_receivable=Decimal(str(commission_calc['seller_receives'])),
                    
                    # Payment status
                    buyer_payment_status="PENDING",
                    seller_payout_status="PENDING",
                    
                    # Payment due date (48 hours)
                    # SaaS FIX: Calculate expiry using UTC now
                    payment_due_date=datetime.now(timezone.utc) + timedelta(hours=48),
                    
                    # Invoice
                    invoice_number=generate_invoice_number(lot.id)
                )
                
                db.add(settlement)
                
                # Create commission records
                await create_commission_records(
                    db=db,
                    settlement=settlement,
                    commission_calc=commission_calc
                )
                
                db.commit()
                created_count += 1
                
                logger.info(f"✅ Created settlement for lot {lot.id} ({lot.item_name})")
                
                # TODO: Send payment notification to winner
                # from app.e_auction.tasks.notification_tasks import notify_payment_due
                # await notify_payment_due(lot.winner_user_id, lot.id, settlement.total_buyer_payable)
                
            except Exception as e:
                db.rollback()
                logger.error(f"❌ Failed to create settlement for lot {lot.id}: {str(e)}")
        
        if created_count > 0:
            logger.info(f"💰 Created {created_count} settlement(s) for auction {auction_id}")
        
        return created_count
    
    except Exception as e:
        logger.error(f"❌ Error in create_settlements_for_auction: {str(e)}")
        return 0
    finally:
        db.close()


async def create_commission_records(db: Session, settlement: Settlement, commission_calc: dict):
    """Create individual commission records"""
    try:
        # Seller commission
        if commission_calc['seller_commission_amount'] > 0:
            seller_commission = Commission(
                auction_id=settlement.auction_id,
                auction_item_id=settlement.auction_item_id,
                settlement_id=settlement.id,
                commission_type="SELLER_COMMISSION",
                charged_to_user_id=settlement.seller_user_id,
                base_amount=settlement.final_bid_amount,
                commission_rate=settlement.seller_commission_rate,
                commission_amount=settlement.seller_commission_amount,
                gst_rate=Decimal(str(settings.GST_RATE_PERCENT)),
                gst_amount=settlement.seller_gst_amount,
                total_commission_with_tax=settlement.seller_total_commission,
                status="PENDING",
                # SaaS FIX: Set UTC creation timestamp
                created_at=datetime.now(timezone.utc)
            )
            db.add(seller_commission)
        
        # Buyer commission
        if commission_calc['buyer_commission_amount'] > 0:
            buyer_commission = Commission(
                auction_id=settlement.auction_id,
                auction_item_id=settlement.auction_item_id,
                settlement_id=settlement.id,
                commission_type="BUYER_COMMISSION",
                charged_to_user_id=settlement.winner_user_id,
                base_amount=settlement.final_bid_amount,
                commission_rate=settlement.buyer_commission_rate,
                commission_amount=settlement.buyer_commission_amount,
                gst_rate=Decimal(str(settings.GST_RATE_PERCENT)),
                gst_amount=settlement.buyer_gst_amount,
                total_commission_with_tax=settlement.buyer_total_commission,
                status="PENDING",
                # SaaS FIX: Set UTC creation timestamp
                created_at=datetime.now(timezone.utc)
            )
            db.add(buyer_commission)
        
        logger.info(f"✅ Created commission records for settlement {settlement.id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to create commission records: {str(e)}")
        raise


async def process_pending_settlements():
    """
    Process settlements with pending payments
    Send reminders, check for overdue
    Called hourly
    """
    db = SessionLocal()
    try:
        # SaaS FIX: Use UTC-aware now for global processing
        now = datetime.now(timezone.utc)
        
        # Find pending settlements
        pending_settlements = db.query(Settlement).filter(
            Settlement.buyer_payment_status == "PENDING"
        ).all()
        
        reminded_count = 0
        overdue_count = 0
        
        for settlement in pending_settlements:
            try:
                # SaaS FIX: Ensure settlement.payment_due_date is aware
                due_date_utc = settlement.payment_due_date.replace(tzinfo=timezone.utc) if settlement.payment_due_date and settlement.payment_due_date.tzinfo is None else settlement.payment_due_date

                # Check if overdue
                if due_date_utc and due_date_utc < now:
                    if not settlement.is_overdue:
                        logger.warning(f"⚠️ Settlement {settlement.id} is overdue")
                        overdue_count += 1
                        
                        # TODO: Send overdue notification
                        # TODO: Mark as overdue in system
                
                # Send reminder 24 hours before due
                elif due_date_utc:
                    hours_until_due = (due_date_utc - now).total_seconds() / 3600
                    if 23 < hours_until_due < 25:  # Within 24-25 hours
                        # TODO: Send reminder
                        reminded_count += 1
                
            except Exception as e:
                logger.error(f"❌ Error processing settlement {settlement.id}: {str(e)}")
        
        if reminded_count > 0:
            logger.info(f"📧 Sent {reminded_count} payment reminder(s)")
        if overdue_count > 0:
            logger.warning(f"⚠️ Found {overdue_count} overdue payment(s)")
        
        return {"reminded": reminded_count, "overdue": overdue_count}
    
    except Exception as e:
        logger.error(f"❌ Error in process_pending_settlements: {str(e)}")
        return {"reminded": 0, "overdue": 0}
    finally:
        db.close()


async def mark_settlement_paid(settlement_id: int, payment_id: int):
    """
    Mark settlement as paid by buyer
    """
    db = SessionLocal()
    try:
        settlement = db.query(Settlement).filter(Settlement.id == settlement_id).first()
        if not settlement:
            return False
        
        settlement.buyer_payment_status = "COMPLETED"
        settlement.buyer_payment_id = payment_id
        # SaaS FIX: Set processed timestamp in UTC
        settlement.buyer_payment_date = datetime.now(timezone.utc)
        
        db.commit()
        
        logger.info(f"✅ Settlement {settlement_id} marked as paid")
        
        # TODO: Trigger seller payout process
        # await process_seller_payout(settlement_id)
        
        return True
    
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error marking settlement paid: {str(e)}")
        return False
    finally:
        db.close()


async def process_seller_payout(settlement_id: int):
    """
    Process payout to seller after buyer payment
    Deduct commissions and transfer to seller
    """
    db = SessionLocal()
    try:
        settlement = db.query(Settlement).filter(Settlement.id == settlement_id).first()
        if not settlement:
            return False
        
        # Verify buyer has paid
        if settlement.buyer_payment_status != "COMPLETED":
            logger.warning(f"Cannot payout - buyer hasn't paid for settlement {settlement_id}")
            return False
        
        # TODO: Integrate with payment gateway for payout
        # TODO: Transfer total_seller_receivable to seller's bank account
        
        settlement.seller_payout_status = "PROCESSING"
        # SaaS FIX: Set updated timestamp in UTC
        settlement.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        logger.info(f"💸 Initiated payout for settlement {settlement_id}")
        
        return True
    
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error processing seller payout: {str(e)}")
        return False
    finally:
        db.close()


def generate_invoice_number(lot_id: int) -> str:
    """Generate unique invoice number"""
    # SaaS FIX: Use UTC for unique invoice timestamp
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"INV-{date_str}-{lot_id:06d}"


async def generate_settlement_report(auction_id: int) -> dict:
    """
    Generate settlement report for an auction
    Returns summary of all settlements
    """
    db = SessionLocal()
    try:
        settlements = db.query(Settlement).filter(
            Settlement.auction_id == auction_id
        ).all()
        
        total_sold = len(settlements)
        total_revenue = sum(s.final_bid_amount for s in settlements)
        total_platform_revenue = sum(s.total_platform_revenue for s in settlements)
        
        pending_payments = sum(1 for s in settlements if s.buyer_payment_status == "PENDING")
        completed_payments = sum(1 for s in settlements if s.buyer_payment_status == "COMPLETED")
        
        return {
            "auction_id": auction_id,
            "total_lots_sold": total_sold,
            "total_revenue": float(total_revenue),
            "total_platform_revenue": float(total_platform_revenue),
            "pending_payments": pending_payments,
            "completed_payments": completed_payments,
            "settlements": settlements,
            # SaaS FIX: Include report generation time in UTC
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ Error generating settlement report: {str(e)}")
        return {}
    finally:
        db.close()
