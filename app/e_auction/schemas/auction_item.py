"""
Auction Item (Lot) Pydantic Schemas
Request and Response models for Lot endpoints
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.e_auction.schemas.common import validate_positive_amount
from app.e_auction.utils.enums import LotStatus, ScrapType, UnitType


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class LotCreateRequest(BaseModel):
    """Request to create a new lot"""
    # Basic Info
    item_name: str = Field(..., min_length=5, max_length=255)
    item_type: Optional[str] = Field(None, max_length=100)
    lot_number: Optional[str] = Field(None, max_length=50)
    
    # Scrap Material Details
    scrap_type: Optional[ScrapType] = None
    category: Optional[str] = Field(None, max_length=100)
    material: Optional[str] = Field(None, max_length=100)
    grade: Optional[str] = Field(None, max_length=100)
    form: Optional[str] = Field(None, max_length=100, description="Sheet, Wire, Ingot, etc.")
    
    # Quantity
    quantity: Decimal = Field(..., gt=0, description="Quantity available")
    unit: UnitType = Field(..., description="Unit of measurement")
    is_partial_qty_allowed: bool = Field(False, description="Allow partial quantity bids")
    estimated_weight: Optional[Decimal] = Field(None, gt=0)
    weight_unit: Optional[str] = Field(None, max_length=20)
    
    # Location
    location_city: Optional[str] = Field(None, max_length=100)
    location_state: Optional[str] = Field(None, max_length=100)
    location_address: Optional[str] = Field(None, max_length=500)
    pickup_conditions: Optional[str] = Field(None, max_length=1000)
    
    # Bidding Configuration
    starting_bid_amount: Decimal = Field(..., gt=0, description="Starting bid price")
    reserve_price: Optional[Decimal] = Field(None, gt=0, description="Minimum acceptable price")
    min_increment_amount: Optional[Decimal] = Field(None, gt=0, description="Minimum bid increment")
    buy_now_price: Optional[Decimal] = Field(None, gt=0, description="Instant buy price")
    
    # Lot Scheduling (optional, inherits from auction if not provided)
    lot_start_time: Optional[datetime] = None
    lot_end_time: Optional[datetime] = None
    
    # Additional
    condition_rating: Optional[int] = Field(None, ge=1, le=5, description="Condition rating 1-5 stars")
    seller_notes: Optional[str] = Field(None, max_length=2000)
    
    # Auction Type Specific
    decrement_amount: Optional[Decimal] = Field(None, gt=0, description="For Dutch auction")
    
    _validate_starting_bid = validator('starting_bid_amount', allow_reuse=True)(validate_positive_amount)
    
    @validator('reserve_price')
    def reserve_price_validation(cls, v, values):
        if v and 'starting_bid_amount' in values:
            if v < values['starting_bid_amount']:
                raise ValueError('reserve_price cannot be less than starting_bid_amount')
        return v
    
    @validator('buy_now_price')
    def buy_now_price_validation(cls, v, values):
        if v and 'starting_bid_amount' in values:
            if v <= values['starting_bid_amount']:
                raise ValueError('buy_now_price must be greater than starting_bid_amount')
        return v
    
    @validator('lot_end_time')
    def lot_end_after_start(cls, v, values):
        if v and 'lot_start_time' in values and values['lot_start_time']:
            if v <= values['lot_start_time']:
                raise ValueError('lot_end_time must be after lot_start_time')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "item_name": "MS Scrap - Turning Boring 500 MT",
                "scrap_type": "Ferrous",
                "category": "Metal",
                "material": "Mild Steel",
                "grade": "A",
                "form": "Scrap",
                "quantity": 500,
                "unit": "MT",
                "location_city": "Mumbai",
                "location_state": "Maharashtra",
                "starting_bid_amount": 25000.00,
                "reserve_price": 24000.00,
                "min_increment_amount": 500.00,
                "condition_rating": 4
            }
        }


class LotUpdateRequest(BaseModel):
    """Request to update an existing lot"""
    item_name: Optional[str] = Field(None, min_length=5, max_length=255)
    item_type: Optional[str] = Field(None, max_length=100)
    
    scrap_type: Optional[ScrapType] = None
    category: Optional[str] = Field(None, max_length=100)
    material: Optional[str] = Field(None, max_length=100)
    grade: Optional[str] = Field(None, max_length=100)
    form: Optional[str] = Field(None, max_length=100)
    
    quantity: Optional[Decimal] = Field(None, gt=0)
    unit: Optional[UnitType] = None
    is_partial_qty_allowed: Optional[bool] = None
    
    location_city: Optional[str] = Field(None, max_length=100)
    location_state: Optional[str] = Field(None, max_length=100)
    location_address: Optional[str] = Field(None, max_length=500)
    pickup_conditions: Optional[str] = Field(None, max_length=1000)
    
    starting_bid_amount: Optional[Decimal] = Field(None, gt=0)
    reserve_price: Optional[Decimal] = Field(None, gt=0)
    min_increment_amount: Optional[Decimal] = Field(None, gt=0)
    buy_now_price: Optional[Decimal] = Field(None, gt=0)
    
    condition_rating: Optional[int] = Field(None, ge=1, le=5)
    seller_notes: Optional[str] = Field(None, max_length=2000)


class LotApprovalRequest(BaseModel):
    """Request for lot L1/L2 approval"""
    approve: bool = Field(..., description="True to approve, False to reject")
    remarks: Optional[str] = Field(None, max_length=500)
    
    class Config:
        json_schema_extra = {
            "example": {
                "approve": True,
                "remarks": "Quality verified. Approved for auction."
            }
        }


class LotImageUploadRequest(BaseModel):
    """Request for lot image upload"""
    is_primary: bool = Field(False, description="Set as primary image")
    display_order: int = Field(0, ge=0, description="Display order in gallery")


class LotFilterParams(BaseModel):
    """Filter parameters for lot list"""
    auction_id: Optional[int] = None
    lot_status: Optional[LotStatus] = None
    category: Optional[str] = None
    material: Optional[str] = None
    scrap_type: Optional[ScrapType] = None
    
    # Location filters
    location_state: Optional[str] = None
    location_city: Optional[str] = None
    
    # Price range
    min_price: Optional[Decimal] = Field(None, ge=0)
    max_price: Optional[Decimal] = Field(None, ge=0)
    
    # Quantity range
    min_quantity: Optional[Decimal] = Field(None, ge=0)
    max_quantity: Optional[Decimal] = Field(None, ge=0)
    
    # Search
    search: Optional[str] = Field(None, description="Search in item name, material")
    
    # Featured
    is_featured: Optional[bool] = None
    
    # Has bids
    has_bids: Optional[bool] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "lot_status": "LIVE",
                "material": "Copper",
                "min_price": 10000,
                "max_price": 50000
            }
        }


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class LotImageResponse(BaseModel):
    """Response model for lot images"""
    id: int
    image_url: str
    file_name: str
    is_primary: int
    display_order: int

    class Config:
        from_attributes = True


class LotBasicResponse(BaseModel):
    """Basic lot information for list views"""
    id: int
    auction_id: int
    item_name: str
    lot_number: Optional[str] = None
    
    # Material
    category: Optional[str] = None
    material: Optional[str] = None
    scrap_type: Optional[str] = None
    
    # Quantity
    quantity: Decimal
    unit: str
    
    # Location
    location_city: Optional[str] = None
    location_state: Optional[str] = None
    
    # Bidding
    starting_bid_amount: Decimal
    highest_bid_amount: Optional[Decimal] = None
    reserve_price: Optional[Decimal] = None
    buy_now_price: Optional[Decimal] = None
    
    # Status
    lot_status: str
    
    # Stats
    total_bids_count: int = 0
    unique_bidders_count: int = 0
    view_count: int = 0
    
    # Timing
    lot_start_time: Optional[datetime] = None
    lot_end_time: Optional[datetime] = None
    
    # Primary image
    primary_image_url: Optional[str] = None
    
    # Computed
    current_price: Decimal
    is_live: bool = False
    
    class Config:
        from_attributes = True


class LotDetailResponse(BaseModel):
    """Detailed lot information"""
    id: int
    auction_id: int
    origin_listing_id: Optional[int] = None
    
    # Basic Info
    item_name: str
    item_type: Optional[str] = None
    lot_number: Optional[str] = None
    
    # Scrap Details
    scrap_type: Optional[str] = None
    category: Optional[str] = None
    material: Optional[str] = None
    grade: Optional[str] = None
    form: Optional[str] = None
    
    # Quantity
    quantity: Decimal
    unit: str
    is_partial_qty_allowed: bool
    estimated_weight: Optional[Decimal] = None
    weight_unit: Optional[str] = None
    
    # Location
    location_city: Optional[str] = None
    location_state: Optional[str] = None
    location_address: Optional[str] = None
    pickup_conditions: Optional[str] = None
    
    # Media (JSON arrays)
    image_urls: Optional[str] = None  # Will be parsed as JSON in service
    test_report_url: Optional[str] = None
    attributes_json: Optional[str] = None
    
    # Bidding Configuration
    starting_bid_amount: Decimal
    reserve_price: Optional[Decimal] = None
    min_increment_amount: Optional[Decimal] = None
    buy_now_price: Optional[Decimal] = None
    
    # Current State
    highest_bid_amount: Optional[Decimal] = None
    winner_user_id: Optional[int] = None
    
    # Stats
    total_bids_count: int = 0
    unique_bidders_count: int = 0
    last_bid_time: Optional[datetime] = None
    extension_count: int = 0
    view_count: int = 0
    
    # Status
    lot_status: str
    lot_auction_type: Optional[str] = None
    
    # Timing
    lot_start_time: Optional[datetime] = None
    lot_end_time: Optional[datetime] = None
    
    # Settlement
    final_sold_price: Optional[Decimal] = None
    settlement_status: Optional[str] = None
    
    # Approval
    l1_approved_by: Optional[int] = None
    l1_approved_at: Optional[datetime] = None
    l1_remarks: Optional[str] = None
    l2_approved_by: Optional[int] = None
    l2_approved_at: Optional[datetime] = None
    l2_remarks: Optional[str] = None
    rejection_reason: Optional[str] = None
    
    # Additional
    condition_rating: Optional[int] = None
    is_featured: bool = False
    seller_notes: Optional[str] = None

    # --- Include the images list in the response ---
    images: List[LotImageResponse] = []
    
    # Auction Type Specific
    decrement_amount: Optional[Decimal] = None
    
    # Audit
    created_at: datetime
    
    # Computed fields
    current_price: Decimal
    min_next_bid: Decimal
    is_live: bool = False
    is_sold: bool = False
    has_bids: bool = False
    has_reserve_price: bool = False
    reserve_met: bool = False
    can_accept_bids: bool = False
    
    class Config:
        from_attributes = True


class LotListResponse(BaseModel):
    """List of lots with pagination"""
    total: int
    page: int
    page_size: int
    total_pages: int
    lots: List[LotBasicResponse]


class LotStatsResponse(BaseModel):
    """Lot statistics"""
    total_lots: int = 0
    pending_lots: int = 0
    approved_lots: int = 0
    live_lots: int = 0
    sold_lots: int = 0
    unsold_lots: int = 0
    
    total_value: Decimal = Decimal('0.00')
    sold_value: Decimal = Decimal('0.00')
    
    total_bids: int = 0
    unique_bidders: int = 0


class LotActionResponse(BaseModel):
    """Response for lot actions"""
    success: bool = True
    message: str
    lot_id: int
    new_status: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Lot approved successfully",
                "lot_id": 456,
                "new_status": "APPROVED"
            }
        }
