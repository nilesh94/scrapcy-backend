"""
Commission Pydantic Schemas
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone
from decimal import Decimal
from app.e_auction.utils.enums import CommissionType, RuleType
# SaaS Standard: Import centralized UTC serializer
from app.e_auction.utils.serialization import datetime_to_utc_iso


# ============================================================================
# COMMISSION RULE SCHEMAS
# ============================================================================

class CommissionRuleCreateRequest(BaseModel):
    """Request to create commission rule"""
    rule_name: str = Field(..., min_length=3, max_length=255)
    rule_type: RuleType
    
    # Commission rates (0-5%)
    seller_commission_percent: Decimal = Field(0, ge=0, le=5)
    buyer_commission_percent: Decimal = Field(0, ge=0, le=5)
    
    # Conditional application
    applies_to_auction_type: Optional[str] = Field(None, max_length=50)
    applies_to_category: Optional[str] = Field(None, max_length=100)
    min_transaction_amount: Optional[Decimal] = Field(None, ge=0)
    max_transaction_amount: Optional[Decimal] = Field(None, ge=0)
    
    # Priority and status
    is_active: bool = True
    is_default: bool = False
    priority: int = Field(0, ge=0, le=100)
    
    # Effective period
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
    
    @field_validator('max_transaction_amount')
    @classmethod
    def max_greater_than_min(cls, v: Optional[Decimal], info) -> Optional[Decimal]:
        if v and 'min_transaction_amount' in info.data and info.data['min_transaction_amount']:
            if v <= info.data['min_transaction_amount']:
                raise ValueError('max_transaction_amount must be greater than min_transaction_amount')
        return v
    
    @field_validator('effective_until')
    @classmethod
    def until_after_from(cls, v: Optional[datetime], info) -> Optional[datetime]:
        if v and 'effective_from' in info.data and info.data['effective_from']:
            if v <= info.data['effective_from']:
                raise ValueError('effective_until must be after effective_from')
        return v
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "rule_name": "Standard Commission",
                "rule_type": "BOTH",
                "seller_commission_percent": 2.0,
                "buyer_commission_percent": 1.0,
                "is_default": True,
                "priority": 0
            }
        }
    )


class CommissionRuleUpdateRequest(BaseModel):
    """Request to update commission rule"""
    rule_name: Optional[str] = Field(None, min_length=3, max_length=255)
    
    seller_commission_percent: Optional[Decimal] = Field(None, ge=0, le=5)
    buyer_commission_percent: Optional[Decimal] = Field(None, ge=0, le=5)
    
    applies_to_auction_type: Optional[str] = None
    applies_to_category: Optional[str] = None
    min_transaction_amount: Optional[Decimal] = Field(None, ge=0)
    max_transaction_amount: Optional[Decimal] = Field(None, ge=0)
    
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, le=100)
    
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None


class CommissionRuleResponse(BaseModel):
    """Commission rule response"""
    id: int
    rule_name: str
    rule_type: str
    
    seller_commission_percent: Decimal
    buyer_commission_percent: Decimal
    
    applies_to_auction_type: Optional[str] = None
    applies_to_category: Optional[str] = None
    min_transaction_amount: Optional[Decimal] = None
    max_transaction_amount: Optional[Decimal] = None
    
    is_active: bool
    is_default: bool
    priority: int
    
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
    
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Computed
    is_currently_effective: bool = False
    
    # SaaS Standard: Server time in UTC
    server_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: datetime_to_utc_iso}
    )


class CommissionRuleListResponse(BaseModel):
    """List of commission rules"""
    total: int
    active_rules: int
    default_rule_id: Optional[int] = None
    rules: List[CommissionRuleResponse]
    
    # SaaS Standard: Server time in UTC
    server_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: datetime_to_utc_iso}
    )


# ============================================================================
# COMMISSION SCHEMAS
# ============================================================================

class CommissionResponse(BaseModel):
    """Commission charge response"""
    id: int
    auction_id: int
    auction_item_id: int
    settlement_id: Optional[int] = None
    
    # Commission details
    commission_type: str
    charged_to_user_id: int
    
    # Calculation
    base_amount: Decimal
    commission_rate: Decimal
    commission_amount: Decimal
    
    # Tax
    gst_rate: Decimal
    gst_amount: Optional[Decimal] = None
    total_commission_with_tax: Optional[Decimal] = None
    
    # Rule applied
    commission_rule_id: Optional[int] = None
    rule_name: Optional[str] = None
    
    # Status
    status: str
    collected_at: Optional[datetime] = None
    payment_id: Optional[int] = None
    
    # Audit
    created_at: datetime
    
    # Computed
    is_collected: bool = False
    is_pending: bool = False
    
    # SaaS Standard: Server time in UTC
    server_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: datetime_to_utc_iso}
    )


class CommissionListResponse(BaseModel):
    """List of commissions"""
    total: int
    page: int
    page_size: int
    total_pages: int
    commissions: List[CommissionResponse]
    
    # SaaS Standard: Server time in UTC
    server_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: datetime_to_utc_iso}
    )


class CommissionCalculationResponse(BaseModel):
    """Commission calculation preview"""
    base_amount: Decimal
    
    # Seller commission
    seller_commission_rate: Decimal
    seller_commission_amount: Decimal
    seller_gst_amount: Decimal
    seller_total: Decimal
    
    # Buyer commission
    buyer_commission_rate: Decimal
    buyer_commission_amount: Decimal
    buyer_gst_amount: Decimal
    buyer_total: Decimal
    
    # Platform total
    total_platform_commission: Decimal
    total_platform_gst: Decimal
    total_platform_revenue: Decimal
    
    # Net amounts
    seller_receives: Decimal
    buyer_pays: Decimal
    
    # Rule applied
    rule_applied: Optional[CommissionRuleResponse] = None
    
    # SaaS Standard: Server time in UTC
    server_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        json_encoders={datetime: datetime_to_utc_iso},
        json_schema_extra = {
            "example": {
                "base_amount": 100000.00,
                "seller_commission_rate": 2.0,
                "seller_commission_amount": 2000.00,
                "seller_gst_amount": 360.00,
                "seller_total": 2360.00,
                "buyer_commission_rate": 1.0,
                "buyer_commission_amount": 1000.00,
                "buyer_gst_amount": 180.00,
                "buyer_total": 1180.00,
                "total_platform_revenue": 3540.00,
                "seller_receives": 97640.00,
                "buyer_pays": 101180.00
            }
        }
    )


# ============================================================================
# COMMISSION STATISTICS
# ============================================================================

class CommissionStatsResponse(BaseModel):
    """Commission statistics"""
    total_commissions_earned: Decimal = Decimal('0.00')
    total_gst_collected: Decimal = Decimal('0.00')
    total_revenue: Decimal = Decimal('0.00')
    
    # By type
    seller_commissions: Decimal = Decimal('0.00')
    buyer_commissions: Decimal = Decimal('0.00')
    
    # Status breakdown
    pending_collection: Decimal = Decimal('0.00')
    collected: Decimal = Decimal('0.00')
    waived: Decimal = Decimal('0.00')
    
    # Transaction counts
    total_transactions: int = 0
    pending_count: int = 0
    collected_count: int = 0
    
    # SaaS Standard: Server time in UTC
    server_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: datetime_to_utc_iso}
    )


class CommissionByCategory(BaseModel):
    """Commission breakdown by category"""
    category: str
    total_transactions: int
    total_commission: Decimal
    avg_commission_rate: Decimal
    model_config = ConfigDict(from_attributes=True)


class CommissionAnalyticsResponse(BaseModel):
    """Comprehensive commission analytics"""
    period_start: datetime
    period_end: datetime
    
    overall_stats: CommissionStatsResponse
    by_category: List[CommissionByCategory]
    
    # Trends
    daily_revenue: List[dict]  # [{date: "2025-02-01", revenue: 15000.00}, ...]
    monthly_revenue: List[dict]
    
    # Top performers
    top_auctions_by_commission: List[dict]
    
    # SaaS Standard: Server time in UTC
    server_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: datetime_to_utc_iso}
    )


# ============================================================================
# COMMISSION ACTIONS
# ============================================================================

class WaiveCommissionRequest(BaseModel):
    """Request to waive commission"""
    commission_id: int
    reason: str = Field(..., min_length=10, max_length=500)
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "commission_id": 123,
                "reason": "First-time seller promotion - waiving commission"
            }
        }
    )


class CommissionActionResponse(BaseModel):
    """Response for commission actions"""
    success: bool = True
    message: str
    commission_id: int
    new_status: str
    
    # SaaS Standard: Server time in UTC
    server_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        json_encoders={datetime: datetime_to_utc_iso},
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Commission waived successfully",
                "commission_id": 123,
                "new_status": "WAIVED"
            }
        }
    )
