"""
Custom Validators
Validation functions for business logic
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional


def validate_auction_dates(start_time: datetime, end_time: datetime) -> bool:
    """Validate auction date range"""
    if end_time <= start_time:
        return False
    
    # Auction must be at least 1 hour
    min_duration = (end_time - start_time).total_seconds()
    if min_duration < 3600:  # 1 hour
        return False
    
    # Start time must be in future
    # SaaS FIX: Use UTC-aware now for global future-date validation
    now = datetime.now(timezone.utc)
    
    # Ensure start_time is timezone-aware for comparison
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)

    if start_time <= now:
        return False
    
    return True


def validate_bid_amount(
    bid_amount: Decimal,
    current_highest: Optional[Decimal],
    starting_bid: Decimal,
    min_increment: Optional[Decimal] = None
) -> tuple[bool, str]:
    """
    Validate bid amount
    Returns (is_valid, error_message)
    """
    # Must be greater than starting bid
    if bid_amount < starting_bid:
        return False, f"Bid must be at least {starting_bid}"
    
    # If there's a current bid, must exceed it
    if current_highest:
        required_bid = current_highest
        
        # Add minimum increment if specified
        if min_increment:
            required_bid += min_increment
        else:
            # Default 1% increment
            required_bid += (current_highest * Decimal('0.01'))
        
        if bid_amount < required_bid:
            return False, f"Bid must be at least {required_bid}"
    
    return True, ""


def validate_commission_rate(rate: float) -> bool:
    """Validate commission rate (0-5%)"""
    return 0 <= rate <= 5


def validate_quantity(quantity: Decimal) -> bool:
    """Validate quantity is positive"""
    return quantity > 0


def validate_price(price: Decimal) -> bool:
    """Validate price is positive"""
    return price > 0


def validate_reserve_price(reserve: Decimal, starting_bid: Decimal) -> bool:
    """Validate reserve price"""
    # Reserve can't be higher than starting bid
    return reserve <= starting_bid


def validate_extension_settings(
    trigger_window: int,
    extension_duration: int,
    max_extensions: int
) -> bool:
    """Validate auction extension settings"""
    if trigger_window < 1 or trigger_window > 30:
        return False
    if extension_duration < 1 or extension_duration > 30:
        return False
    if max_extensions < 1 or max_extensions > 20:
        return False
    return True
