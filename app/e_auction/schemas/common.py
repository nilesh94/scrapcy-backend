"""
Common Pydantic Schemas
Base models and shared schemas used across the application
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Any, Dict
from datetime import datetime
from decimal import Decimal


# ============================================================================
# BASE RESPONSE MODELS
# ============================================================================

class ResponseBase(BaseModel):
    """Base response model"""
    success: bool = True
    message: Optional[str] = None
    
    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""
    total: int
    page: int
    page_size: int
    total_pages: int
    data: List[dict]
    
    class Config:
        from_attributes = True


# ============================================================================
# PAGINATION
# ============================================================================

class PaginationParams(BaseModel):
    """Pagination query parameters"""
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
    
    @property
    def skip(self) -> int:
        """Calculate offset"""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Get limit"""
        return self.page_size


# ============================================================================
# FILTERS
# ============================================================================

class DateRangeFilter(BaseModel):
    """Date range filter"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    @validator('end_date')
    def end_date_must_be_after_start(cls, v, values):
        if v and values.get('start_date') and v < values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v


class PriceRangeFilter(BaseModel):
    """Price range filter"""
    min_price: Optional[Decimal] = Field(None, ge=0)
    max_price: Optional[Decimal] = Field(None, ge=0)
    
    @validator('max_price')
    def max_price_must_be_greater(cls, v, values):
        if v and values.get('min_price') and v < values['min_price']:
            raise ValueError('max_price must be greater than min_price')
        return v


# ============================================================================
# COMMON FIELDS
# ============================================================================

class LocationBase(BaseModel):
    """Location information"""
    city: Optional[str] = None
    state: Optional[str] = None
    address: Optional[str] = None
    pincode: Optional[str] = None


class ContactInfo(BaseModel):
    """Contact information"""
    contact_person: Optional[str] = None
    # UPDATED: Changed regex to pattern for Pydantic V2
    contact_number: Optional[str] = Field(None, pattern=r'^\+?[0-9]{10,15}$')
    contact_email: Optional[str] = None


class AuditInfo(BaseModel):
    """Audit trail information"""
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[int] = None
    
    class Config:
        from_attributes = True


# ============================================================================
# STATUS ENUMS (for response schemas)
# ============================================================================

class StatusResponse(BaseModel):
    """Generic status response"""
    status: str
    status_label: Optional[str] = None
    can_edit: bool = False
    can_delete: bool = False
    can_approve: bool = False
    
    class Config:
        from_attributes = True


# ============================================================================
# FILE UPLOAD
# ============================================================================

class FileUploadResponse(BaseModel):
    """File upload response"""
    file_id: Optional[int] = None
    file_name: str
    file_url: str
    file_size: int
    mime_type: str
    uploaded_at: datetime
    
    class Config:
        from_attributes = True


class ImageInfo(BaseModel):
    """Image information"""
    image_id: Optional[int] = None
    image_url: str
    thumbnail_url: Optional[str] = None
    is_primary: bool = False
    display_order: int = 0


# ============================================================================
# ERROR RESPONSE
# ============================================================================

class ErrorDetail(BaseModel):
    """Detailed error information"""
    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response"""
    success: bool = False
    error: str
    details: Optional[List[ErrorDetail]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


# ============================================================================
# APPROVAL WORKFLOW
# ============================================================================

class ApprovalInfo(BaseModel):
    """Approval information"""
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    remarks: Optional[str] = None
    
    class Config:
        from_attributes = True


class ApprovalRequest(BaseModel):
    """Approval action request"""
    remarks: Optional[str] = Field(None, max_length=500)
    approve: bool = True  # True for approve, False for reject


# ============================================================================
# STATISTICS
# ============================================================================

class StatisticsBase(BaseModel):
    """Base statistics"""
    total_count: int = 0
    active_count: int = 0
    completed_count: int = 0


# ============================================================================
# NOTIFICATION PREFERENCES
# ============================================================================

class NotificationPreferences(BaseModel):
    """User notification preferences"""
    email: bool = True
    sms: bool = True
    push: bool = True
    in_app: bool = True


# ============================================================================
# MONEY/CURRENCY
# ============================================================================

class MoneyAmount(BaseModel):
    """Money amount with currency"""
    amount: Decimal = Field(..., ge=0)
    currency: str = Field("INR", max_length=3)
    
    @property
    def formatted(self) -> str:
        """Format as currency string"""
        return f"{self.currency} {self.amount:,.2f}"


# ============================================================================
# COMMON VALIDATORS
# ============================================================================

def validate_positive_amount(v: Optional[Decimal]) -> Optional[Decimal]:
    """Validate amount is positive"""
    if v is not None and v <= 0:
        raise ValueError("Amount must be greater than zero")
    return v


def validate_percentage(v: Optional[Decimal]) -> Optional[Decimal]:
    """Validate percentage is between 0 and 100"""
    if v is not None and (v < 0 or v > 100):
        raise ValueError("Percentage must be between 0 and 100")
    return v


def validate_phone_number(v: Optional[str]) -> Optional[str]:
    """Validate phone number format"""
    if v:
        import re
        if not re.match(r'^\+?[0-9]{10,15}$', v):
            raise ValueError("Invalid phone number format")
    return v
