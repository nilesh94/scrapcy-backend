"""
Payment & Participant Routes
Registration and payment endpoints
All endpoints have RBAC placeholders (commented for testing)
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.e_auction.services import PaymentService
from app.e_auction.schemas.participant_payment import *
from app.e_auction.routes.auth_dependencies import get_current_user_id, RequireAuth

# Payment router
payment_router = APIRouter(prefix="/api/v1/e-auction/payments", tags=["Payments"])

# Participant router
participant_router = APIRouter(prefix="/api/v1/e-auction/participants", tags=["Participants"])


# ============================================================================
# PARTICIPANT / REGISTRATION ENDPOINTS
# ============================================================================

@participant_router.post("/auctions/{auction_id}/register", response_model=RegistrationSuccessResponse)
async def register_for_auction(
    auction_id: int,
    registration_data: AuctionRegistrationRequest,
    # ==== RBAC: Authenticated buyer ====
    current_user: dict = Depends(RequireAuth),
    db: Session = Depends(get_db)
):
    """
    Register for auction
    
    RBAC: Requires authentication
    Creates participant record and initiates payment
    """
    from app.e_auction.models import Auction, AuctionParticipant
    from app.e_auction.utils.enums import PaymentType
    from sqlalchemy import and_
    from decimal import Decimal
    
    # Get ID from model attribute or dict key
    user_id = getattr(current_user, "id", None) or current_user.get("id")
    
    # Get auction
    auction = db.query(Auction).filter(Auction.id == auction_id).first()
    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")
    
    # Check if already registered
    existing = db.query(AuctionParticipant).filter(
        and_(
            AuctionParticipant.auction_id == auction_id,
            AuctionParticipant.user_id == user_id
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Already registered for this auction")
    
    # Create participant
    participant = AuctionParticipant(
        auction_id=auction_id,
        user_id=user_id,
        agreed_to_terms=registration_data.agreed_to_terms,
        participation_status="APPROVED"  # Auto-approved for now
    )
    
    db.add(participant)
    db.commit()
    db.refresh(participant)
    
    # Calculate total payment
    reg_fee = auction.registration_fee or Decimal('0.00')
    emd = auction.emd_amount or Decimal('0.00')
    total_due = reg_fee + emd
    
    # Initiate payment if required
    payment_response = None
    if total_due > 0:
        payment_response = PaymentService.initiate_payment(
            db=db,
            user_id=user_id,
            payment_type=PaymentType.EMD,  # Combined payment
            amount=total_due,
            auction_id=auction_id
        )
    
    return RegistrationSuccessResponse(
        success=True,
        message="Registration successful. Please complete payment.",
        participant_id=participant.id,
        auction_id=auction_id,
        registration_fee_amount=reg_fee,
        emd_amount=emd,
        total_amount_due=total_due,
        payment_required=total_due > 0,
        payment_order_id=payment_response.payment_id if payment_response else None, # Changed order_id to payment_id based on schema
        payment_url=payment_response.payment_url if payment_response else None
    )


@participant_router.get("/auctions/{auction_id}/participants", response_model=ParticipantListResponse)
async def get_auction_participants(
    auction_id: int,
    # ==== RBAC: Only auction creator or admin ====
    current_user: dict = Depends(RequireAuth),
    db: Session = Depends(get_db)
):
    """
    Get list of participants for an auction
    
    RBAC: Only auction creator or ADMIN
    """
    from app.e_auction.models import AuctionParticipant
    
    participants = db.query(AuctionParticipant).filter(
        AuctionParticipant.auction_id == auction_id
    ).all()
    
    total = len(participants)
    approved = sum(1 for p in participants if p.participation_status == "APPROVED" and p.payment_status == "SUCCESS")
    
    # UPDATED: model_validate for Pydantic V2
    return ParticipantListResponse(
        auction_id=auction_id,
        total_participants=total,
        approved_participants=approved,
        participants=[ParticipantResponse.model_validate(p) for p in participants]
    )


# ============================================================================
# PAYMENT ENDPOINTS
# ============================================================================

@payment_router.post("/initiate", response_model=PaymentInitiateResponse)
async def initiate_payment(
    payment_request: PaymentInitiateRequest,
    # ==== RBAC: Authenticated user ====
    current_user: dict = Depends(RequireAuth),
    db: Session = Depends(get_db)
):
    """
    Initiate payment
    
    RBAC: Requires authentication
    """
    # Get ID from model attribute or dict key
    user_id = getattr(current_user, "id", None) or current_user.get("id")

    return PaymentService.initiate_payment(
        db=db,
        user_id=user_id,
        payment_type=payment_request.payment_type,
        amount=payment_request.amount,
        auction_id=payment_request.auction_id,
        auction_item_id=payment_request.auction_item_id
    )


@payment_router.post("/verify", response_model=PaymentVerifyResponse)
async def verify_payment(
    verify_request: PaymentVerifyRequest,
    # ==== RBAC: Authenticated user ====
    current_user: dict = Depends(RequireAuth),
    db: Session = Depends(get_db)
):
    """
    Verify payment after gateway callback
    
    RBAC: Requires authentication
    """
    from app.e_auction.models import Payment
    
    # Get payment by transaction ID
    payment = db.query(Payment).filter(
        Payment.transaction_id == verify_request.order_id
    ).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return PaymentService.verify_payment(
        db=db,
        payment_id=payment.id,
        transaction_id=verify_request.transaction_id,
        payment_signature=verify_request.payment_signature
    )


@payment_router.get("/history", response_model=PaymentHistoryResponse)
async def get_payment_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    # ==== RBAC: Authenticated user ====
    current_user: dict = Depends(RequireAuth),
    db: Session = Depends(get_db)
):
    """
    Get payment history
    
    RBAC: Requires authentication
    """
    # Get ID from model attribute or dict key
    user_id = getattr(current_user, "id", None) or current_user.get("id")

    return PaymentService.get_payment_history(
        db=db,
        user_id=user_id,
        page=page,
        page_size=page_size
    )


@payment_router.post("/refund", response_model=RefundResponse)
async def request_refund(
    refund_request: RefundRequest,
    # ==== RBAC: Authenticated user or admin ====
    current_user: dict = Depends(RequireAuth),
    db: Session = Depends(get_db)
):
    """
    Request refund
    
    RBAC: Payment owner or ADMIN
    """
    from app.e_auction.models import Payment
    
    # Get ID from model attribute or dict key
    user_id = getattr(current_user, "id", None) or current_user.get("id")

    payment = db.query(Payment).filter(Payment.id == refund_request.payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Verify ownership
    if payment.user_id != user_id:
         raise HTTPException(status_code=403, detail="Not authorized")
    
    return PaymentService.initiate_refund(
        db=db,
        payment_id=refund_request.payment_id,
        reason=refund_request.reason,
        refund_amount=refund_request.refund_amount
    )


@payment_router.post("/webhook/razorpay")
async def razorpay_webhook(
    webhook_data: PaymentWebhookRequest,
    db: Session = Depends(get_db)
):
    """
    Razorpay webhook handler
    
    No RBAC - called by payment gateway
    Should verify webhook signature in production
    """
    # TODO: Verify webhook signature
    # TODO: Process webhook events
    
    return PaymentWebhookResponse(
        status="ok",
        message="Webhook received"
    )
