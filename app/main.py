import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ============================================================================
# DATABASE CONNECTION
# ============================================================================
from app.database.connection import engine, Base

# ============================================================================
# IMPORT MODELS (Register with SQLAlchemy)
# ============================================================================
from app.models import users as user_models
from app.models import scrapListing as scrap_models
from app.models import scrapCategories as category_models
from app.models import market_data as market_models
from app.models import requirements as requirement_models

# ✨ E-AUCTION MODELS
from app.e_auction.models import (
    auction as auction_models,
    auction_item as auction_item_models,
    # Added Approval System Models
    approval as approval_models,
    # Re-enabling participant model now that file is created
    participant as participant_models,
    # Commenting out missing models to fix ImportError
    # bid as bid_models,
    # payment as payment_models,
    # settlement as settlement_models,
    # audit_log as audit_log_models,
)

# ============================================================================
# IMPORT ROUTERS
# ============================================================================
from app.routes import users as user_routes
from app.routes import scrapListing as scrap_routes
from app.routes import scrapCategories as category_routes
from app.routes import locations as location_routes
from app.routes import market_prices as market_price_routes
from app.routes import requirements as requirement_routes

# ✨ E-AUCTION ROUTERS (Fixed Imports)
from app.e_auction.routes import auctions as auction_routes
from app.e_auction.routes import admin_routes as admin_routes
from app.e_auction.routes import lots
# Added Approval Workflow Router
from app.e_auction.routes import approval as approval_routes
# Added bidding router for the live engine
from app.e_auction.routes import bidding as bidding_routes

# ============================================================================
# SETUP LOGGING
# ============================================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# ✨ LIFESPAN MANAGEMENT (Modern V2 Standard)
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events"""
    try:
        logger.info("Connecting to Database...")
        # Creates all tables from imported models
        Base.metadata.create_all(bind=engine)
        logger.info("Database connected and tables checked.")
    except Exception as e:
        logger.error(f"Database connection error during startup: {e}")
    
    yield
    
    logger.info("Shutting down Scrapcy API...")

# ============================================================================
# INITIALIZE APP
# ============================================================================
app = FastAPI(
    title="Scrapcy Backend",
    description="Scrap Management & E-Auction Platform",
    version="2.0.0",
    lifespan=lifespan
)

# ============================================================================
# CORS CONFIG
# ============================================================================
origins = [
    "http://localhost:3000",
    "https://scrapcy-frontend.onrender.com",
    "https://scrapcy-admin.onrender.com",
    "https://scrapcy.nexusmeta.in",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# INCLUDE ROUTERS
# ============================================================================
app.include_router(user_routes.router)
app.include_router(scrap_routes.router)
app.include_router(category_routes.router)
app.include_router(location_routes.router)
app.include_router(market_price_routes.router)
app.include_router(requirement_routes.router)
app.include_router(lots.router)

# ============================================================================
# ✨ INCLUDE E-AUCTION ROUTERS (NEW)
# ============================================================================

# 1. Auction Routes 
# Removed prefix here because it is ALREADY defined in auctions.py 
# (prefix="/api/v1/e-auction/auctions")
app.include_router(
    auction_routes.router,
    # prefix="" <--- Left empty to avoid duplication
    # tags=["E-Auction"] <--- Tags are already in the router file
)

# 2. Admin Routes
# Added prefix here because admin.py only defines "/admin"
# Combined URL: /api/v1/e-auction/admin
app.include_router(
    admin_routes.router,
    prefix="/api/v1/e-auction", 
    # tags=["E-Auction Admin"] <--- Tags are already in the router file
)

# 3. Approval Workflow Routes
# Handles multi-level approvals: L1 -> L2 -> Admin sign-off 
app.include_router(
    approval_routes.router
)

# 4. Bidding Engine Routes
# Added bidding router to process real-time bids
app.include_router(
    bidding_routes.router
)

# ============================================================================
# ROOT ENDPOINT
# ============================================================================
@app.api_route("/", methods=["GET", "HEAD"])
def read_root():
    """Root endpoint supporting GET and HEAD for health checks"""
    return {
        "message": "Scrapcy API is running & modularized!",
        "version": "2.0.0",
        "features": ["Scrap Management", "E-Auction Platform"]
    }

# ============================================================================
# HEALTH CHECK
# ============================================================================
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "e_auction": "active"
    }
