"""
Auction Pydantic Schemas
Request and Response models for Auction endpoints
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict # Updated imports
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.e_auction.schemas.common import (
    AuditInfo, 
    ApprovalInfo, 
    DateRangeFilter, 
    PaginationParams,
    validate_positive_amount
)
from app.e_auction.utils.enums import AuctionStatus, ApprovalStatus, AuctionType
# Import Lot schemas to allow nesting
from app.e_auction.schemas.auction_item import LotCreateRequest, LotDetailResponse


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class AuctionCreateRequest(BaseModel):
    """Request to create a new auction"""
    auction_title: str = Field(..., min_length=5, max_length=255, description="Auction title")
    auction_type: Optional[AuctionType] = Field(AuctionType.FORWARD, description="Auction type")
    category: Optional[str] = Field(None, max_length=100)
    region: Optional[str] = Field(None, max_length=100)
    
    # --- Seller ID (For Admin creation) ---
    seller_id: Optional[int] = Field(None, description="ID of the Seller/Company. Required if Admin is creating.")
    
    # Scheduling
    scheduled_start_time: datetime = Field(..., description="When auction starts")
    scheduled_end_time: datetime = Field(..., description="When auction ends")
    
    # Financial Requirements
    currency: str = Field("INR", max_length=10)
    emd_amount: Optional[Decimal] = Field(None, ge=0, description="EMD amount required")
    registration_fee: Optional[Decimal] = Field(None, ge=0, description="Registration fee")
    
    # Extension Settings
    enable_extension: bool = Field(False, description="Enable auto-extension")
    extension_trigger_window_minutes: Optional[int] = Field(5, ge=1, le=30)
    extension_duration_minutes: Optional[int] = Field(5, ge=1, le=30)
    extension_min_total_bids: Optional[int] = Field(1, ge=1)
    
    # Inspection Details
    inspection_start_date: Optional[datetime] = None
    inspection_end_date: Optional[datetime] = None
    inspection_location: Optional[str] = Field(None, max_length=500)
    inspection_contact_person: Optional[str] = Field(None, max_length=255)
    
    # CHANGED: 'regex' -> 'pattern' for Pydantic V2 compatibility
    inspection_contact_number: Optional[str] = Field(None, pattern=r'^\+?[0-9]{10,15}$')
    
    # Documents
    terms_and_conditions: Optional[str] = None
    auction_doc_url: Optional[str] = Field(None, max_length=500)

    # Allow creating lots in the same request
    lots: Optional[List[LotCreateRequest]] = Field(default=[], description="List of lots to create immediately")
    
    # UPDATED: Using field_validator for V2
    @field_validator('scheduled_end_time')
    @classmethod
    def end_time_after_start(cls, v: datetime, info) -> datetime:
        if 'scheduled_start_time' in info.data and v <= info.data['scheduled_start_time']:
            raise ValueError('scheduled_end_time must be after scheduled_start_time')
        return v
    
    @field_validator('inspection_end_date')
    @classmethod
    def inspection_end_after_start(cls, v: datetime, info) -> datetime:
        if v and 'inspection_start_date' in info.data and info.data['inspection_start_date']:
            if v <= info.data['inspection_start_date']:
                raise ValueError('inspection_end_date must be after inspection_start_date')
        return v
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "auction_title": "Industrial Scrap Metal Auction - January 2025",
                "seller_id": 101,
                "auction_type": "FORWARD",
                "category": "Ferrous Metals",
                "region": "Maharashtra",
                "scheduled_start_time": "2025-02-15T10:00:00",
                "scheduled_end_time": "2025-02-15T16:00:00",
                "currency": "INR",
                "emd_amount": 50000.00,
                "registration_fee": 1000.00,
                "enable_extension": True,
                "inspection_location": "Warehouse A, MIDC Taloja",
                "inspection_contact_person": "John Doe",
                "inspection_contact_number": "+919876543210",
                "lots": [
                    {
                        "item_name": "Test Lot 1",
                        "quantity": 100,
                        "unit": "KG",
                        "starting_bid_amount": 5000
                    }
                ]
            }
        }
    )


class AuctionUpdateRequest(BaseModel):
    """Request to update an existing auction"""
    auction_title: Optional[str] = Field(None, min_length=5, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    region: Optional[str] = Field(None, max_length=100)
    
    scheduled_start_time: Optional[datetime] = None
    scheduled_end_time: Optional[datetime] = None
    
    emd_amount: Optional[Decimal] = Field(None, ge=0)
    registration_fee: Optional[Decimal] = Field(None, ge=0)
    
    enable_extension: Optional[bool] = None
    extension_trigger_window_minutes: Optional[int] = Field(None, ge=1, le=30)
    extension_duration_minutes: Optional[int] = Field(None, ge=1, le=30)
    
    inspection_start_date: Optional[datetime] = None
    inspection_end_date: Optional[datetime] = None
    inspection_location: Optional[str] = Field(None, max_length=500)
    inspection_contact_person: Optional[str] = Field(None, max_length=255)
    
    inspection_contact_number: Optional[str] = Field(None, pattern=r'^\+?[0-9]{10,15}$')
    
    terms_and_conditions: Optional[str] = None
    auction_doc_url: Optional[str] = Field(None, max_length=500)
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "auction_title": "Updated Auction Title",
                "emd_amount": 75000.00
            }
        }
    )


class AuctionApprovalRequest(BaseModel):
    """Request for L1/L2 approval"""
    approve: bool = Field(..., description="True to approve, False to reject")
    remarks: Optional[str] = Field(None, max_length=500, description="Approval/Rejection remarks")
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "approve": True,
                "remarks": "All documents verified. Approved for publishing."
            }
        }
    )


class AuctionFilterParams(BaseModel):
    """Filter parameters for auction list"""
    status: Optional[AuctionStatus] = None
    approval_status: Optional[ApprovalStatus] = None
    auction_type: Optional[AuctionType] = None
    category: Optional[str] = None
    region: Optional[str] = None
    
    # Date filters
    start_date_from: Optional[datetime] = None
    start_date_to: Optional[datetime] = None
    
    # Search
    search: Optional[str] = Field(None, description="Search in title")
    
    # Creator filter
    created_by_me: Optional[bool] = Field(False, description="Show only my auctions")
    
    # Featured
    is_featured: Optional[bool] = None
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "status": "LIVE",
                "category": "Ferrous Metals",
                "region": "Maharashtra"
            }
        }
    )


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class AuctionBasicResponse(BaseModel):
    """Basic auction information"""
    id: int
    auction_title: str
    auction_type: Optional[str] = None
    
    seller_id: int
    
    status: str
    approval_status: str
    
    scheduled_start_time: Optional[datetime] = None
    scheduled_end_time: Optional[datetime] = None
    
    currency: str
    emd_amount: Optional[Decimal] = None
    registration_fee: Optional[Decimal] = None
    
    total_lots: int = 0
    view_count: int = 0
    is_featured: bool = False
    
    created_at: datetime
    emd_paid: bool = False
    
    model_config = ConfigDict(from_attributes=True)


class AuctionDetailResponse(BaseModel):
    """Detailed auction information"""
    id: int
    auction_title: str
    auction_type: Optional[str] = None
    category: Optional[str] = None
    region: Optional[str] = None
    
    seller_id: int
    
    # Status
    status: str
    approval_status: str
    
    # Scheduling
    scheduled_start_time: Optional[datetime] = None
    scheduled_end_time: Optional[datetime] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    published_at: Optional[datetime] = None
    
    # Financial
    currency: str
    emd_amount: Optional[Decimal] = None
    registration_fee: Optional[Decimal] = None
    
    # Extension Settings
    enable_extension: bool
    extension_trigger_window_minutes: Optional[int] = None
    extension_duration_minutes: Optional[int] = None
    extension_min_total_bids: Optional[int] = None
    
    # Inspection
    inspection_start_date: Optional[datetime] = None
    inspection_end_date: Optional[datetime] = None
    inspection_location: Optional[str] = None
    inspection_contact_person: Optional[str] = None
    inspection_contact_number: Optional[str] = None
    
    # Documents
    terms_and_conditions: Optional[str] = None
    auction_doc_url: Optional[str] = None
    
    # Approval Info
    l1_approved_by: Optional[int] = None
    l1_approved_at: Optional[datetime] = None
    l1_remarks: Optional[str] = None
    l2_approved_by: Optional[int] = None
    l2_approved_at: Optional[datetime] = None
    l2_remarks: Optional[str] = None
    
    # Stats
    total_lots: int = 0
    view_count: int = 0
    is_featured: bool = False
    
    # Creator
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Cancellation
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    
    # Computed fields
    is_live: bool = False
    is_approved: bool = False
    can_be_edited: bool = False
    requires_emd: bool = False
    requires_registration_fee: bool = False

    # Return created items in response
    items: Optional[List[LotDetailResponse]] = []
    
    model_config = ConfigDict(from_attributes=True)


class AuctionListResponse(BaseModel):
    """List of auctions with pagination"""
    total: int
    page: int
    page_size: int
    total_pages: int
    auctions: List[AuctionBasicResponse]
    model_config = ConfigDict(from_attributes=True)


class AuctionStatsResponse(BaseModel):
    """Auction statistics"""
    total_auctions: int = 0
    draft_auctions: int = 0
    pending_approval: int = 0
    scheduled_auctions: int = 0
    live_auctions: int = 0
    closed_auctions: int = 0
    cancelled_auctions: int = 0
    
    total_lots: int = 0
    total_participants: int = 0
    total_bids: int = 0
    model_config = ConfigDict(from_attributes=True)


class AuctionActionResponse(BaseModel):
    """Response for auction actions (approve, publish, cancel)"""
    success: bool = True
    message: str
    auction_id: int
    new_status: Optional[str] = None
    new_approval_status: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Auction approved successfully",
                "auction_id": 123,
                "new_approval_status": "L1_APPROVED"
            }
        }
    )


# ============================================================================
# UTILITY SCHEMAS
# ============================================================================

class AuctionStatusChange(BaseModel):
    """Request to change auction status"""
    new_status: AuctionStatus
    reason: Optional[str] = Field(None, max_length=500)


class CancelAuctionRequest(BaseModel):
    """Request to cancel auction"""
    cancellation_reason: str = Field(..., min_length=10, max_length=500)
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "cancellation_reason": "Unable to proceed due to seller request"
            }
        }
    )
