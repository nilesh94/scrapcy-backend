"""
Helper Functions
Common utility functions used across the e-auction module
"""
from typing import Optional, List
from datetime import datetime, timedelta
from decimal import Decimal
import re


def calculate_time_remaining(end_time: datetime) -> dict:
    """
    Calculate time remaining until end_time
    Returns dict with days, hours, minutes, seconds
    """
    if not end_time:
        return None
    
    now = datetime.now()
    if end_time <= now:
        return {"days": 0, "hours": 0, "minutes": 0, "seconds": 0, "total_seconds": 0}
    
    delta = end_time - now
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    return {
        "days": days,
        "hours": hours,
        "minutes": minutes,
        "seconds": seconds,
        "total_seconds": int(delta.total_seconds())
    }


def format_currency(amount: Decimal, currency: str = "INR") -> str:
    """Format amount as currency string"""
    return f"{currency} {amount:,.2f}"


def generate_invoice_number(settlement_id: int) -> str:
    """Generate unique invoice number"""
    date_str = datetime.now().strftime("%Y%m%d")
    return f"INV-{date_str}-{settlement_id:06d}"


def generate_order_id(user_id: int, auction_id: int) -> str:
    """Generate unique order ID for payments"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"ORD-{auction_id}-{user_id}-{timestamp}"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    # Remove special characters
    filename = re.sub(r'[^\w\s.-]', '', filename)
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    return filename


def parse_json_array(json_str: Optional[str]) -> List:
    """Safely parse JSON array string"""
    if not json_str:
        return []
    
    try:
        import json
        return json.loads(json_str)
    except:
        return []


def to_json_array(data: List) -> str:
    """Convert list to JSON string"""
    import json
    return json.dumps(data)


def calculate_gst(amount: Decimal, gst_rate: float = 18.0) -> Decimal:
    """Calculate GST amount"""
    return (amount * Decimal(str(gst_rate))) / Decimal('100')


def calculate_tds(amount: Decimal, tds_rate: float = 1.0) -> Decimal:
    """Calculate TDS amount"""
    return (amount * Decimal(str(tds_rate))) / Decimal('100')


def is_valid_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_valid_phone(phone: str) -> bool:
    """Validate phone number (India)"""
    pattern = r'^\+?[0-9]{10,15}$'
    return bool(re.match(pattern, phone))


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."
