import logging
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

# ✨ E-AUCTION MODELS (NEW)
from app.e_auction.models import (
    auction as auction_models,
    auction_item as auction_item_models,
    # Add other e-auction models if you have them:
    # bid as bid_models,
    # participant as participant_models,
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

# ✨ E-AUCTION ROUTERS (NEW)
from app.e_auction.routes import auction_routes
from app.e_auction.routes import admin_routes

# ============================================================================
# SETUP LOGGING
# ============================================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# INITIALIZE APP
# ============================================================================
app = FastAPI(
    title="Scrapcy Backend",
    description="Scrap Management & E-Auction Platform",
    version="2.0.0"
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
# CREATE DATABASE TABLES
# ============================================================================
try:
    logger.info("Connecting to Database...")
    # Creates all tables from imported models
    Base.metadata.create_all(bind=engine)
    logger.info("Database connected and tables checked.")
except Exception as e:
    logger.error(f"Database connection warning: {e}")

# ============================================================================
# INCLUDE ROUTERS - EXISTING
# ============================================================================
app.include_router(user_routes.router)
app.include_router(scrap_routes.router)
app.include_router(category_routes.router)
app.include_router(location_routes.router)
app.include_router(market_price_routes.router)
app.include_router(requirement_routes.router)

# ============================================================================
# ✨ INCLUDE E-AUCTION ROUTERS (NEW)
# ============================================================================

# Public Auction Routes (Create, View, Browse)
app.include_router(
    auction_routes.router,
    prefix="/api/v1/e-auction",
    tags=["E-Auction"]
)

# Admin Routes (Manage, Delete, Archive, Audit)
app.include_router(
    admin_routes.router,
    prefix="/api/v1/e-auction",
    tags=["E-Auction Admin"]
)

# ============================================================================
# ROOT ENDPOINT
# ============================================================================
@app.get("/")
def read_root():
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
