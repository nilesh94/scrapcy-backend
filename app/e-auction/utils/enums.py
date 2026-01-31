"""
Enumerations for E-Auction Module
All status values and types used across the application
"""
from enum import Enum


class AuctionStatus(str, Enum):
    """Auction lifecycle statuses"""
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class ApprovalStatus(str, Enum):
    """Approval workflow statuses"""
    PENDING = "PENDING"
    L1_APPROVED = "L1_APPROVED"
    L2_APPROVED = "L2_APPROVED"
    REJECTED = "REJECTED"


class LotStatus(str, Enum):
    """Lot/Item statuses"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    LIVE = "LIVE"
    SOLD = "SOLD"
    UNSOLD = "UNSOLD"
    CANCELLED = "CANCELLED"


class BidStatus(str, Enum):
    """Bid statuses"""
    ACTIVE = "ACTIVE"
    OUTBID = "OUTBID"
    WON = "WON"
    LOST = "LOST"
    CANCELLED = "CANCELLED"


class BidType(str, Enum):
    """Types of bids"""
    MANUAL = "MANUAL"
    AUTO = "AUTO"
    PROXY = "PROXY"


class AutoBidStatus(str, Enum):
    """Auto-bid statuses"""
    ACTIVE = "ACTIVE"
    OUTBID = "OUTBID"
    CANCELLED = "CANCELLED"
    EXHAUSTED = "EXHAUSTED"


class PaymentType(str, Enum):
    """Payment types"""
    REGISTRATION_FEE = "REGISTRATION_FEE"
    EMD = "EMD"
    FINAL_PAYMENT = "FINAL_PAYMENT"
    EMD_REFUND = "EMD_REFUND"
    COMMISSION = "COMMISSION"
    PENALTY = "PENALTY"


class PaymentStatus(str, Enum):
    """Payment statuses"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class PaymentMethod(str, Enum):
    """Payment methods"""
    UPI = "UPI"
    CARD = "CARD"
    NET_BANKING = "NET_BANKING"
    WALLET = "WALLET"


class ParticipationStatus(str, Enum):
    """Auction participation statuses"""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    BANNED = "BANNED"


class CommissionType(str, Enum):
    """Commission types"""
    SELLER = "SELLER"
    BUYER = "BUYER"
    PLATFORM_FEE = "PLATFORM_FEE"


class CommissionStatus(str, Enum):
    """Commission collection statuses"""
    PENDING = "PENDING"
    COLLECTED = "COLLECTED"
    WAIVED = "WAIVED"
    DISPUTED = "DISPUTED"


class SettlementStatus(str, Enum):
    """Settlement statuses"""
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    COMPLETED = "COMPLETED"
    OVERDUE = "OVERDUE"


class NotificationType(str, Enum):
    """Notification types"""
    OUTBID = "OUTBID"
    LOT_ENDING_SOON = "LOT_ENDING_SOON"
    WON = "WON"
    LOST = "LOST"
    PAYMENT_DUE = "PAYMENT_DUE"
    AUCTION_STARTING = "AUCTION_STARTING"
    AUCTION_EXTENDED = "AUCTION_EXTENDED"
    EMD_REFUND_PROCESSED = "EMD_REFUND_PROCESSED"
    REGISTRATION_CONFIRMED = "REGISTRATION_CONFIRMED"
    LOT_APPROVED = "LOT_APPROVED"
    LOT_REJECTED = "LOT_REJECTED"


class NotificationPriority(str, Enum):
    """Notification priority levels"""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class AuctionType(str, Enum):
    """Auction types"""
    FORWARD = "FORWARD"  # Traditional ascending bid
    REVERSE = "REVERSE"  # Descending bid (for procurement)
    DUTCH = "DUTCH"      # Price drops over time


class UnitType(str, Enum):
    """Measurement units"""
    KG = "KG"
    MT = "MT"
    TON = "TON"
    PIECES = "PIECES"
    LITERS = "LITERS"
    CUBIC_METER = "CUBIC_METER"


class ScrapType(str, Enum):
    """Scrap categories"""
    FERROUS = "Ferrous"
    NON_FERROUS = "Non-Ferrous"
    PRECIOUS_METALS = "Precious Metals"
    E_WASTE = "E-Waste"
    PLASTIC = "Plastic"
    PAPER = "Paper"
    GLASS = "Glass"
    TEXTILE = "Textile"
    RUBBER = "Rubber"
    MIXED = "Mixed"


class ActivityAction(str, Enum):
    """Activity log actions"""
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    VIEW = "VIEW"


class EntityType(str, Enum):
    """Entity types for activity logging"""
    AUCTION = "AUCTION"
    LOT = "LOT"
    BID = "BID"
    PAYMENT = "PAYMENT"
    USER = "USER"
    COMMISSION = "COMMISSION"
    SETTLEMENT = "SETTLEMENT"


class BidEventType(str, Enum):
    """Bid event types"""
    BID_PLACED = "BID_PLACED"
    BID_OUTBID = "BID_OUTBID"
    AUTO_BID_TRIGGERED = "AUTO_BID_TRIGGERED"
    BID_WON = "BID_WON"
    BID_LOST = "BID_LOST"
    BID_CANCELLED = "BID_CANCELLED"


class RuleType(str, Enum):
    """Commission rule types"""
    SELLER_COMMISSION = "SELLER_COMMISSION"
    BUYER_COMMISSION = "BUYER_COMMISSION"
    BOTH = "BOTH"


# Helper functions
def get_enum_values(enum_class) -> list:
    """Get all values from an enum"""
    return [item.value for item in enum_class]


def is_valid_enum(enum_class, value: str) -> bool:
    """Check if value is valid for given enum"""
    return value in get_enum_values(enum_class)
