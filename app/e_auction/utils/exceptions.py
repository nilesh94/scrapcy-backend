"""
Custom Exceptions for E-Auction Module
All business logic exceptions with proper HTTP status codes
"""
from fastapi import HTTPException, status


class EAuctionException(HTTPException):
    """Base exception for all e-auction errors"""
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)


# ============================================================================
# AUCTION EXCEPTIONS
# ============================================================================

class AuctionNotFoundException(EAuctionException):
    """Auction not found"""
    def __init__(self, auction_id: int):
        super().__init__(
            detail=f"Auction with ID {auction_id} not found",
            status_code=status.HTTP_404_NOT_FOUND
        )


class AuctionNotEditableException(EAuctionException):
    """Auction cannot be edited in current status"""
    def __init__(self, auction_status: str):
        super().__init__(
            detail=f"Cannot edit auction in status: {auction_status}",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class AuctionAlreadyStartedException(EAuctionException):
    """Auction has already started"""
    def __init__(self):
        super().__init__(
            detail="Cannot modify auction that has already started",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class AuctionNotLiveException(EAuctionException):
    """Auction is not currently live"""
    def __init__(self):
        super().__init__(
            detail="Auction is not currently live for bidding",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class AuctionNotApprovedException(EAuctionException):
    """Auction not approved for publishing"""
    def __init__(self):
        super().__init__(
            detail="Auction must be L1 and L2 approved before publishing",
            status_code=status.HTTP_403_FORBIDDEN
        )


# ============================================================================
# LOT/ITEM EXCEPTIONS
# ============================================================================

class LotNotFoundException(EAuctionException):
    """Lot/Item not found"""
    def __init__(self, lot_id: int):
        super().__init__(
            detail=f"Lot with ID {lot_id} not found",
            status_code=status.HTTP_404_NOT_FOUND
        )


class LotNotAvailableForBiddingException(EAuctionException):
    """Lot not available for bidding"""
    def __init__(self, lot_status: str):
        super().__init__(
            detail=f"Lot is not available for bidding. Current status: {lot_status}",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class LotAlreadySoldException(EAuctionException):
    """Lot already sold"""
    def __init__(self):
        super().__init__(
            detail="This lot has already been sold",
            status_code=status.HTTP_400_BAD_REQUEST
        )


# ============================================================================
# BID EXCEPTIONS
# ============================================================================

class BidAmountTooLowException(EAuctionException):
    """Bid amount is too low"""
    def __init__(self, min_amount: float, currency: str = "INR"):
        super().__init__(
            detail=f"Bid amount must be at least {currency} {min_amount:,.2f}",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class BidIncrementTooSmallException(EAuctionException):
    """Bid increment is too small"""
    def __init__(self, min_increment: float, currency: str = "INR"):
        super().__init__(
            detail=f"Bid must be at least {currency} {min_increment:,.2f} higher than current bid",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class UserNotRegisteredForAuctionException(EAuctionException):
    """User not registered for auction"""
    def __init__(self):
        super().__init__(
            detail="You must register and pay EMD before bidding",
            status_code=status.HTTP_403_FORBIDDEN
        )


class SellerCannotBidException(EAuctionException):
    """Seller cannot bid on their own auction"""
    def __init__(self):
        super().__init__(
            detail="Sellers cannot bid on their own auctions",
            status_code=status.HTTP_403_FORBIDDEN
        )


class BidRateLimitExceededException(EAuctionException):
    """Bid rate limit exceeded"""
    def __init__(self, retry_after: int):
        super().__init__(
            detail=f"Too many bids. Please try again in {retry_after} seconds",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )


class AuctionClosedException(EAuctionException):
    """Auction/Lot has closed"""
    def __init__(self):
        super().__init__(
            detail="Cannot place bid. Auction has closed",
            status_code=status.HTTP_400_BAD_REQUEST
        )


# ============================================================================
# PAYMENT EXCEPTIONS
# ============================================================================

class PaymentFailedException(EAuctionException):
    """Payment failed"""
    def __init__(self, reason: str = "Payment processing failed"):
        super().__init__(
            detail=reason,
            status_code=status.HTTP_402_PAYMENT_REQUIRED
        )


class InsufficientEMDException(EAuctionException):
    """Insufficient EMD amount"""
    def __init__(self, required: float, paid: float, currency: str = "INR"):
        super().__init__(
            detail=f"Insufficient EMD. Required: {currency} {required:,.2f}, Paid: {currency} {paid:,.2f}",
            status_code=status.HTTP_402_PAYMENT_REQUIRED
        )


class PaymentAlreadyProcessedException(EAuctionException):
    """Payment already processed"""
    def __init__(self):
        super().__init__(
            detail="Payment has already been processed for this transaction",
            status_code=status.HTTP_400_BAD_REQUEST
        )


# ============================================================================
# PARTICIPANT EXCEPTIONS
# ============================================================================

class AlreadyRegisteredException(EAuctionException):
    """User already registered for auction"""
    def __init__(self):
        super().__init__(
            detail="You are already registered for this auction",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class RegistrationNotApprovedException(EAuctionException):
    """Registration not approved"""
    def __init__(self):
        super().__init__(
            detail="Your registration has not been approved yet",
            status_code=status.HTTP_403_FORBIDDEN
        )


class UserBannedException(EAuctionException):
    """User is banned from auction"""
    def __init__(self):
        super().__init__(
            detail="You have been banned from participating in this auction",
            status_code=status.HTTP_403_FORBIDDEN
        )


# ============================================================================
# AUTHORIZATION EXCEPTIONS
# ============================================================================

class UnauthorizedException(EAuctionException):
    """User not authorized"""
    def __init__(self, detail: str = "Not authorized to perform this action"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class ForbiddenException(EAuctionException):
    """Action forbidden"""
    def __init__(self, detail: str = "You do not have permission to perform this action"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN
        )


class InsufficientPermissionsException(EAuctionException):
    """Insufficient permissions"""
    def __init__(self, required_role: str):
        super().__init__(
            detail=f"This action requires {required_role} role",
            status_code=status.HTTP_403_FORBIDDEN
        )


# ============================================================================
# VALIDATION EXCEPTIONS
# ============================================================================

class InvalidDateRangeException(EAuctionException):
    """Invalid date range"""
    def __init__(self, detail: str = "End date must be after start date"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class InvalidQuantityException(EAuctionException):
    """Invalid quantity"""
    def __init__(self, detail: str = "Quantity must be greater than zero"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class InvalidPriceException(EAuctionException):
    """Invalid price"""
    def __init__(self, detail: str = "Price must be greater than zero"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class ReservePriceExceedsStartingBidException(EAuctionException):
    """Reserve price exceeds starting bid"""
    def __init__(self):
        super().__init__(
            detail="Reserve price must be less than or equal to starting bid",
            status_code=status.HTTP_400_BAD_REQUEST
        )


# ============================================================================
# FILE UPLOAD EXCEPTIONS
# ============================================================================

class FileTooLargeException(EAuctionException):
    """File size exceeds limit"""
    def __init__(self, max_size_mb: int):
        super().__init__(
            detail=f"File size exceeds maximum limit of {max_size_mb}MB",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        )


class InvalidFileTypeException(EAuctionException):
    """Invalid file type"""
    def __init__(self, allowed_types: list):
        super().__init__(
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class FileUploadFailedException(EAuctionException):
    """File upload failed"""
    def __init__(self, reason: str = "File upload failed"):
        super().__init__(
            detail=reason,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# BUSINESS LOGIC EXCEPTIONS
# ============================================================================

class KYCNotVerifiedException(EAuctionException):
    """KYC not verified"""
    def __init__(self):
        super().__init__(
            detail="KYC verification required before participating in auctions",
            status_code=status.HTTP_403_FORBIDDEN
        )


class AutoBidConflictException(EAuctionException):
    """Auto-bid already exists"""
    def __init__(self):
        super().__init__(
            detail="You already have an active auto-bid for this lot",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class WatchlistLimitExceededException(EAuctionException):
    """Watchlist limit exceeded"""
    def __init__(self, max_items: int):
        super().__init__(
            detail=f"Watchlist limit of {max_items} items exceeded",
            status_code=status.HTTP_400_BAD_REQUEST
        )


# ============================================================================
# SYSTEM EXCEPTIONS
# ============================================================================

class DatabaseException(EAuctionException):
    """Database error"""
    def __init__(self, detail: str = "Database operation failed"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class ExternalServiceException(EAuctionException):
    """External service error"""
    def __init__(self, service_name: str, detail: str = "External service unavailable"):
        super().__init__(
            detail=f"{service_name}: {detail}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


class CacheException(EAuctionException):
    """Cache operation error"""
    def __init__(self, detail: str = "Cache operation failed"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
