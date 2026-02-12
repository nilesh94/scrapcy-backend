"""
E-Auction Schemas Package
Export all Pydantic request/response schemas
"""

# Common schemas
from .common import (
    ResponseBase,
    PaginatedResponse,
    PaginationParams,
    DateRangeFilter,
    PriceRangeFilter,
    LocationBase,
    ContactInfo,
    AuditInfo,
    StatusResponse,
    FileUploadResponse,
    ImageInfo,
    ErrorDetail,
    ErrorResponse,
    ApprovalInfo,
    ApprovalRequest,
    StatisticsBase,
    NotificationPreferences,
    MoneyAmount,
)

# Auction schemas
from .auction import (
    AuctionCreateRequest,
    AuctionUpdateRequest,
    AuctionApprovalRequest,
    AuctionFilterParams,
    AuctionBasicResponse,
    AuctionDetailResponse,
    AuctionListResponse,
    AuctionStatsResponse,
    AuctionActionResponse,
    AuctionStatusChange,
    CancelAuctionRequest,
)

# Auction Item (Lot) schemas
from .auction_item import (
    LotCreateRequest,
    LotUpdateRequest,
    LotApprovalRequest,
    LotImageUploadRequest,
    LotFilterParams,
    LotBasicResponse,
    LotDetailResponse,
    LotListResponse,
    LotStatsResponse,
    LotActionResponse,
)

# Bid schemas
from .bid import (
    PlaceBidRequest,
    AutoBidCreateRequest,
    AutoBidUpdateRequest,
    BidFilterParams,
    BidResponse,
    BidDetailResponse,
    BidHistoryResponse,
    BidListResponse,
    MyBidsResponse,
    BidSuccessResponse,
    BidRejectedResponse,
    AutoBidResponse,
    AutoBidListResponse,
    AutoBidSuccessResponse,
    CancelAutoBidRequest,
    BidStatsResponse,
    LotBidSummary,
    BidUpdateMessage,
)

# Participant and Payment schemas
from .participant_payment import (
    AuctionRegistrationRequest,
    ParticipantResponse,
    ParticipantListResponse,
    RegistrationSuccessResponse,
    PaymentInitiateRequest,
    PaymentVerifyRequest,
    PaymentInitiateResponse,
    PaymentVerifyResponse,
    PaymentResponse,
    PaymentListResponse,
    PaymentHistoryResponse,
    RefundRequest,
    RefundResponse,
    PaymentStatsResponse,
    PaymentWebhookRequest,
    PaymentWebhookResponse,
)

# Commission schemas
from .commission import (
    CommissionRuleCreateRequest,
    CommissionRuleUpdateRequest,
    CommissionRuleResponse,
    CommissionRuleListResponse,
    CommissionResponse,
    CommissionListResponse,
    CommissionCalculationResponse,
    CommissionStatsResponse,
    CommissionByCategory,
    CommissionAnalyticsResponse,
    WaiveCommissionRequest,
    CommissionActionResponse,
)

__all__ = [
    # Common
    "ResponseBase",
    "PaginatedResponse",
    "PaginationParams",
    "DateRangeFilter",
    "PriceRangeFilter",
    "LocationBase",
    "ContactInfo",
    "AuditInfo",
    "StatusResponse",
    "FileUploadResponse",
    "ImageInfo",
    "ErrorDetail",
    "ErrorResponse",
    "ApprovalInfo",
    "ApprovalRequest",
    "StatisticsBase",
    "NotificationPreferences",
    "MoneyAmount",
    
    # Auction
    "AuctionCreateRequest",
    "AuctionUpdateRequest",
    "AuctionApprovalRequest",
    "AuctionFilterParams",
    "AuctionBasicResponse",
    "AuctionDetailResponse",
    "AuctionListResponse",
    "AuctionStatsResponse",
    "AuctionActionResponse",
    "AuctionStatusChange",
    "CancelAuctionRequest",
    
    # Auction Item
    "LotCreateRequest",
    "LotUpdateRequest",
    "LotApprovalRequest",
    "LotImageUploadRequest",
    "LotFilterParams",
    "LotBasicResponse",
    "LotDetailResponse",
    "LotListResponse",
    "LotStatsResponse",
    "LotActionResponse",
    
    # Bid
    "PlaceBidRequest",
    "AutoBidCreateRequest",
    "AutoBidUpdateRequest",
    "BidFilterParams",
    "BidResponse",
    "BidDetailResponse",
    "BidHistoryResponse",
    "BidListResponse",
    "MyBidsResponse",
    "BidSuccessResponse",
    "BidRejectedResponse",
    "AutoBidResponse",
    "AutoBidListResponse",
    "AutoBidSuccessResponse",
    "CancelAutoBidRequest",
    "BidStatsResponse",
    "LotBidSummary",
    "BidUpdateMessage",
    
    # Participant & Payment
    "AuctionRegistrationRequest",
    "ParticipantResponse",
    "ParticipantListResponse",
    "RegistrationSuccessResponse",
    "PaymentInitiateRequest",
    "PaymentVerifyRequest",
    "PaymentInitiateResponse",
    "PaymentVerifyResponse",
    "PaymentResponse",
    "PaymentListResponse",
    "PaymentHistoryResponse",
    "RefundRequest",
    "RefundResponse",
    "PaymentStatsResponse",
    "PaymentWebhookRequest",
    "PaymentWebhookResponse",
    
    # Commission
    "CommissionRuleCreateRequest",
    "CommissionRuleUpdateRequest",
    "CommissionRuleResponse",
    "CommissionRuleListResponse",
    "CommissionResponse",
    "CommissionListResponse",
    "CommissionCalculationResponse",
    "CommissionStatsResponse",
    "CommissionByCategory",
    "CommissionAnalyticsResponse",
    "WaiveCommissionRequest",
    "CommissionActionResponse",
]
