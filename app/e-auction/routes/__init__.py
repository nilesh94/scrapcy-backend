"""
E-Auction Routes Package
Export all API routers
"""

from .auctions import router as auctions_router
from .bidding import router as bidding_router
from .payments_participants import payment_router, participant_router

# Collect all routers
all_routers = [
    auctions_router,
    bidding_router,
    payment_router,
    participant_router,
]

__all__ = [
    "auctions_router",
    "bidding_router",
    "payment_router",
    "participant_router",
    "all_routers",
]
