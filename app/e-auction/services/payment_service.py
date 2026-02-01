"""
Payment Service
Handles all payment operations
Supports: Razorpay (configured via ENV)
"""
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import hmac

from app.e_auction.models import Payment, AuctionParticipant
from app.e_auction.schemas.participant_payment import *
from app.e_auction.utils.exceptions import *
from app.e_auction.utils.enums import PaymentType, PaymentStatus
from app.e_auction.config import settings


class PaymentService:
    """Payment processing service"""
    
    @staticmethod
    def initiate_payment(
        db: Session,
        user_id: int,
        payment_type: PaymentType,
        amount: Decimal,
        auction_id: Optional[int] = None,
        auction_item_id: Optional[int] = None
    ) -> PaymentInitiateResponse:
        """
        Initiate payment
        Creates payment record and generates payment gateway link
        """
        # Generate unique order ID
        order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{user_id}"
        
        # Create payment record
        payment = Payment(
            user_id=user_id,
            auction_id=auction_id,
            auction_item_id=auction_item_id,
            payment_type=payment_type,
            amount=amount,
            currency=settings.PAYMENT_CURRENCY,
            payment_status=PaymentStatus.PENDING,
            transaction_id=order_id
        )
        
        db.add(payment)
        db.commit()
        db.refresh(payment)
        
        # Generate payment gateway details
        # If Razorpay is enabled, create order
        gateway_order_id = order_id
        gateway_key = ""
        payment_url = None
        
        if settings.RAZORPAY_ENABLED:
            try:
                # Import razorpay only if enabled (optional dependency)
                import razorpay
                
                client = razorpay.Client(
                    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
                )
                
                # Create Razorpay order
                razorpay_order = client.order.create({
                    'amount': int(amount * 100),  # Convert to paise
                    'currency': settings.PAYMENT_CURRENCY,
                    'receipt': order_id,
                    'notes': {
                        'user_id': user_id,
                        'payment_type': payment_type.value
                    }
                })
                
                gateway_order_id = razorpay_order['id']
                gateway_key = settings.RAZORPAY_KEY_ID
                
                # Update payment with gateway order ID
                payment.transaction_id = gateway_order_id
                db.commit()
                
            except ImportError:
                # Razorpay not installed - use mock
                pass
            except Exception as e:
                raise PaymentFailedException(f"Payment gateway error: {str(e)}")
        
        expires_at = datetime.now() + timedelta(minutes=settings.PAYMENT_TIMEOUT_MINUTES)
        
        return PaymentInitiateResponse(
            success=True,
            payment_id=payment.id,
            order_id=order_id,
            amount=amount,
            currency=settings.PAYMENT_CURRENCY,
            gateway_order_id=gateway_order_id,
            gateway_key=gateway_key,
            payment_url=payment_url,
            expires_at=expires_at
        )
    
    @staticmethod
    def verify_payment(
        db: Session,
        payment_id: int,
        transaction_id: str,
        payment_signature: Optional[str] = None
    ) -> PaymentVerifyResponse:
        """
        Verify payment from gateway
        """
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise PaymentFailedException("Payment not found")
        
        if payment.payment_status == PaymentStatus.SUCCESS:
            raise PaymentAlreadyProcessedException()
        
        # Verify signature if Razorpay
        if settings.RAZORPAY_ENABLED and payment_signature:
            try:
                # Verify Razorpay signature
                expected_signature = hmac.new(
                    settings.RAZORPAY_KEY_SECRET.encode(),
                    f"{payment.transaction_id}|{transaction_id}".encode(),
                    hashlib.sha256
                ).hexdigest()
                
                if payment_signature != expected_signature:
                    raise PaymentFailedException("Invalid payment signature")
                
            except Exception as e:
                payment.payment_status = PaymentStatus.FAILED
                db.commit()
                raise PaymentFailedException(f"Payment verification failed: {str(e)}")
        
        # Mark as successful
        payment.payment_status = PaymentStatus.SUCCESS
        payment.processed_at = datetime.now()
        
        db.commit()
        db.refresh(payment)
        
        # Update participant status if EMD/registration fee
        if payment.payment_type in [PaymentType.EMD, PaymentType.REGISTRATION_FEE]:
            participant = db.query(AuctionParticipant).filter(
                and_(
                    AuctionParticipant.user_id == payment.user_id,
                    AuctionParticipant.auction_id == payment.auction_id
                )
            ).first()
            
            if participant:
                participant.payment_status = "SUCCESS"
                if payment.payment_type == PaymentType.EMD:
                    participant.emd_blocked_amount = payment.amount
                elif payment.payment_type == PaymentType.REGISTRATION_FEE:
                    participant.registration_fee_paid = payment.amount
                db.commit()
        
        return PaymentVerifyResponse(
            success=True,
            message="Payment verified successfully",
            payment_id=payment.id,
            transaction_id=transaction_id,
            payment_status=PaymentStatus.SUCCESS.value,
            amount=payment.amount,
            processed_at=payment.processed_at
        )
    
    @staticmethod
    def initiate_refund(
        db: Session,
        payment_id: int,
        reason: str,
        refund_amount: Optional[Decimal] = None
    ) -> RefundResponse:
        """
        Initiate refund for a payment
        """
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise PaymentFailedException("Payment not found")
        
        if payment.payment_status != PaymentStatus.SUCCESS:
            raise PaymentFailedException("Only successful payments can be refunded")
        
        if payment.refund_status == "PROCESSED":
            raise PaymentAlreadyProcessedException()
        
        # Determine refund amount
        refund_amt = refund_amount or payment.amount
        
        # Create refund (placeholder - actual gateway integration needed)
        refund_txn_id = f"RFN{datetime.now().strftime('%Y%m%d%H%M%S')}{payment.id}"
        
        payment.refund_amount = refund_amt
        payment.refund_status = "PROCESSING"
        payment.refund_transaction_id = refund_txn_id
        payment.refund_initiated_at = datetime.now()
        payment.refund_reason = reason
        
        db.commit()
        
        return RefundResponse(
            success=True,
            message="Refund initiated",
            payment_id=payment.id,
            refund_amount=refund_amt,
            refund_transaction_id=refund_txn_id,
            refund_status="PROCESSING"
        )
    
    @staticmethod
    def get_payment_history(
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 20
    ) -> PaymentHistoryResponse:
        """Get user's payment history"""
        skip = (page - 1) * page_size
        
        payments = db.query(Payment).filter(
            Payment.user_id == user_id
        ).order_by(Payment.created_at.desc()).offset(skip).limit(page_size).all()
        
        # Stats
        total_paid = db.query(func.sum(Payment.amount)).filter(
            and_(Payment.user_id == user_id, Payment.payment_status == PaymentStatus.SUCCESS)
        ).scalar() or Decimal('0.00')
        
        total_refunded = db.query(func.sum(Payment.refund_amount)).filter(
            and_(Payment.user_id == user_id, Payment.refund_status == "PROCESSED")
        ).scalar() or Decimal('0.00')
        
        return PaymentHistoryResponse(
            total_payments=len(payments),
            total_amount_paid=total_paid,
            total_refunded=total_refunded,
            payments=[PaymentResponse.from_orm(p) for p in payments]
        )
