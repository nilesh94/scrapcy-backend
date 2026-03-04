"""
Participant and Payment Pydantic Schemas
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone
from decimal import Decimal
from app.e_auction.utils.enums import PaymentType, PaymentStatus, PaymentMethod


# ============================================================================
# PARTICIPANT (REGISTRATION) SCHEMAS
# ============================================================================

class AuctionRegistrationRequest(BaseModel):
    """Request to register for an auction"""
    agreed_to_terms: bool = Field(..., description="Must agree to terms and conditions")
    
    @field_validator('agreed_to_terms')
    @classmethod
    def terms_must_be_accepted(cls, v):
        if not v:
            raise ValueError('You must agree to terms and conditions')
        return v
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "agreed_to_terms": True
            }
        }
    )


class ParticipantResponse(BaseModel):
    """Participant registration response"""
    id: int
    auction_id: int
    user_id: int
    
    # Financial
    registration_fee_paid: Decimal
    emd_blocked_amount: Decimal
    payment_status: str
    payment_ref_id: Optional[str] = None
    
    # Status
    participation_status: str
    agreed_to_terms: bool
    
    # Verification
    kyc_verified: bool
    phone_verified: bool
    email_verified: bool
    
    # Audit
    registered_at: datetime
    
    # Computed
    is_approved: bool = False
    can_bid: bool = False
    
    # SaaS Standard: Server time in UTC
    server_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(from_attributes=True)


class ParticipantListResponse(BaseModel):
    """List of participants"""
    auction_id: int
    total_participants: int
    approved_participants: int
    participants: List[ParticipantResponse]
    
    # SaaS Standard: Server time in UTC
    server_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(from_attributes=True)


class RegistrationSuccessResponse(BaseModel):
    """Response after successful registration"""
    success: bool = True
    message: str
    participant_id: int
    auction_id: int
    
    # Payment details
    registration_fee_amount: Decimal
    emd_amount: Decimal
    total_amount_due: Decimal
    
    # Payment link
    payment_required: bool = True
    payment_order_id: Optional[str] = None
    payment_url: Optional[str] = None
    
    # SaaS Standard: Server time in UTC
    server_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Registration successful. Please complete payment.",
                "participant_id": 123,
                "auction_id": 456,
                "registration_fee_amount": 1000.00,
                "emd_amount": 50000.00,
                "total_amount_due": 51000.00,
                "payment_required": True,
                "payment_url": "https://razorpay.com/payment/..."
            }
        }
    )


# ============================================================================
# PAYMENT SCHEMAS
# ============================================================================

class PaymentInitiateRequest(BaseModel):
    """Request to initiate payment"""
    payment_type: PaymentType
    amount: Decimal = Field(..., gt=0)
    auction_id: Optional[int] = None
    auction_item_id: Optional[int] = None
    
    # Payment method preference
    payment_method: Optional[PaymentMethod] = None
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "payment_type": "EMD",
                "amount": 50000.00,
                "auction_id": 456,
                "payment_method": "UPI"
            }
        }
    )


class PaymentVerifyRequest(BaseModel):
    """Request to verify payment"""
    transaction_id: str = Field(..., description="Payment gateway transaction ID")
    payment_signature: Optional[str] = Field(None, description="Payment signature from gateway")
    order_id: Optional[str] = Field(None, description="Order ID from payment initiation")
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "transaction_id": "pay_123456789",
                "payment_signature": "signature_hash",
                "order_id": "order_123456"
            }
        }
    )


class PaymentInitiateResponse(BaseModel):
    """Response after initiating payment"""
    success: bool = True
    payment_id: int
    order_id: str
    amount: Decimal
    currency: str = "INR"
    
    # Payment gateway details
    gateway_order_id: str
    gateway_key: str
    payment_url: Optional[str] = None
    
    # Expiry
    expires_at: datetime
    
    # SaaS Standard: Server time in UTC
    server_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "success": True,
                "payment_id": 789,
                "order_id": "ORD123456",
                "amount": 51000.00,
                "currency": "INR",
                "gateway_order_id": "order_razorpay_123",
                "gateway_key": "rzp_test_key",
                "payment_url": "https://razorpay.com/...",
                "expires_at": "2025-02-15T12:00:00"
            }
        }
    )


class PaymentVerifyResponse(BaseModel):
    """Response after verifying payment"""
    success: bool = True
    message: str
    payment_id: int
    transaction_id: str
    payment_status: str
    amount: Decimal
    payment_method: Optional[str] = None
    processed_at: Optional[datetime] = None
    
    # SaaS Standard: Server time in UTC
    server_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Payment verified successfully",
                "payment_id": 789,
                "transaction_id": "pay_123456789",
                "payment_status": "SUCCESS",
                "amount": 51000.00,
                "payment_method": "UPI",
                "processed_at": "2025-02-15T10:30:00"
            }
        }
    )


class PaymentResponse(BaseModel):
    """Payment details response"""
    id: int
    user_id: int
    auction_id: Optional[int] = None
    auction_item_id: Optional[int] = None
    
    # Payment details
    payment_type: str
    amount: Decimal
    currency: str
    
    # Status
    payment_status: str
    payment_method: Optional[str] = None
    transaction_id: Optional[str] = None
    
    # Refund
    refund_amount: Optional[Decimal] = None
    refund_status: Optional[str] = None
    refund_completed_at: Optional[datetime] = None
    
    # Audit
    created_at: datetime
    processed_at: Optional[datetime] = None
    
    # Computed
    is_successful: bool = False
    is_pending: bool = False
    is_refunded: bool = False
    
    # SaaS Standard: Server time in UTC
    server_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(from_attributes=True)


class PaymentListResponse(BaseModel):
    """List of payments"""
    total: int
    page: int
    page_size: int
    total_pages: int
    payments: List[PaymentResponse]
    
    # SaaS Standard: Server time in UTC
    server_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(from_attributes=True)


class PaymentHistoryResponse(BaseModel):
    """User's payment history"""
    total_payments: int = 0
    total_amount_paid: Decimal = Decimal('0.00')
    total_refunded: Decimal = Decimal('0.00')
    
    pending_payments: int = 0
    successful_payments: int = 0
    failed_payments: int = 0
    
    payments: List[PaymentResponse]
    
    # SaaS Standard: Server time in UTC
    server_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(from_attributes=True)


class RefundRequest(BaseModel):
    """Request for refund"""
    payment_id: int
    reason: str = Field(..., min_length=10, max_length=500)
    refund_amount: Optional[Decimal] = Field(None, gt=0, description="Partial refund amount (optional)")
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "payment_id": 789,
                "reason": "Auction cancelled by seller",
                "refund_amount": 50000.00
            }
        }
    )


class RefundResponse(BaseModel):
    """Refund processing response"""
    success: bool = True
    message: str
    payment_id: int
    refund_amount: Decimal
    refund_transaction_id: Optional[str] = None
    refund_status: str
    
    # SaaS Standard: Server time in UTC
    server_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Refund initiated successfully",
                "payment_id": 789,
                "refund_amount": 50000.00,
                "refund_status": "PROCESSING"
            }
        }
    )


# ============================================================================
# PAYMENT STATISTICS
# ============================================================================

class PaymentStatsResponse(BaseModel):
    """Payment statistics"""
    total_revenue: Decimal = Decimal('0.00')
    total_refunds: Decimal = Decimal('0.00')
    net_revenue: Decimal = Decimal('0.00')
    
    # By type
    registration_fees: Decimal = Decimal('0.00')
    emd_collected: Decimal = Decimal('0.00')
    final_payments: Decimal = Decimal('0.00')
    commission_collected: Decimal = Decimal('0.00')
    
    # Transaction counts
    total_transactions: int = 0
    successful_transactions: int = 0
    pending_transactions: int = 0
    failed_transactions: int = 0
    refunded_transactions: int = 0
    
    # SaaS Standard: Server time in UTC
    server_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# WEBHOOK SCHEMAS (for payment gateway callbacks)
# ============================================================================

class PaymentWebhookRequest(BaseModel):
    """Payment gateway webhook payload"""
    event: str  # payment.success, payment.failed, refund.processed
    entity: str = "payment"
    payload: dict
    
    # Razorpay specific
    account_id: Optional[str] = None
    created_at: Optional[int] = None


class PaymentWebhookResponse(BaseModel):
    """Response to payment gateway webhook"""
    status: str = "ok"
    message: str = "Webhook processed successfully"
