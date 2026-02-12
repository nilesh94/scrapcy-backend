"""
SCRAPCY E-Auction - Main Application
Complete integration with all features
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
from pathlib import Path

from app.e_auction.config import settings, get_allowed_origins, is_local
from app.e_auction.routes import all_routers
from app.e_auction.routes.websocket import router as websocket_router

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
logging.basicConfig(
    level=settings.log_level_value,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CREATE FASTAPI APP
# ============================================================================
app = FastAPI(
    title="SCRAPCY E-Auction API",
    description="Complete E-Auction Platform API with Real-time Bidding",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,  # Disable docs in production
    redoc_url="/redoc" if settings.DEBUG else None,
)

# ============================================================================
# CORS MIDDLEWARE
# ============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# STATIC FILES (for local file uploads)
# ============================================================================
if settings.STORAGE_PROVIDER == "local":
    upload_dir = Path(settings.LOCAL_UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    app.mount(
        "/uploads",
        StaticFiles(directory=str(upload_dir)),
        name="uploads"
    )
    logger.info(f"✅ Static files mounted: {upload_dir}")

# ============================================================================
# INCLUDE ROUTERS
# ============================================================================
# REST API Routes
for router in all_routers:
    app.include_router(router)
    logger.info(f"✅ Included router: {router.prefix}")

# WebSocket Route
app.include_router(websocket_router)
logger.info(f"✅ Included WebSocket router: {websocket_router.prefix}")

# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "SCRAPCY E-Auction",
        "version": "1.0.0",
        "environment": settings.APP_ENV.value,
        "database": "connected",  # TODO: Add actual DB health check
        "scheduler": "running" if settings.SCHEDULER_ENABLED else "disabled",
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "SCRAPCY E-Auction API",
        "docs": "/docs" if settings.DEBUG else "Disabled in production",
        "health": "/health",
        "environment": settings.APP_ENV.value,
    }

# ============================================================================
# STARTUP EVENT
# ============================================================================
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("=" * 80)
    logger.info("🚀 STARTING SCRAPCY E-AUCTION API")
    logger.info("=" * 80)
    logger.info(f"📌 Environment: {settings.APP_ENV.value}")
    logger.info(f"📌 Debug Mode: {settings.DEBUG}")
    logger.info(f"📌 Backend URL: {settings.BACKEND_URL}")
    logger.info(f"📌 Frontend URL: {settings.FRONTEND_URL}")
    logger.info(f"📌 Database: {settings.DATABASE_URL.split('@')[0]}@***")  # Hide credentials
    logger.info(f"📌 Storage Provider: {settings.STORAGE_PROVIDER}")
    logger.info(f"📌 Redis: {settings.REDIS_URL}")
    logger.info(f"📌 Razorpay: {'Enabled' if settings.RAZORPAY_ENABLED else 'Disabled'}")
    
    # Start background scheduler
    if settings.SCHEDULER_ENABLED:
        from app.e_auction.tasks.scheduler import start_scheduler
        start_scheduler()
        logger.info(f"✅ Background scheduler started (interval: {settings.scheduler_interval}s)")
    else:
        logger.info("⏸️  Background scheduler disabled")
    
    # Create upload directory if using local storage
    if settings.STORAGE_PROVIDER == "local":
        upload_dir = Path(settings.LOCAL_UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Upload directory ready: {upload_dir}")
    
    logger.info("=" * 80)
    logger.info("✅ SCRAPCY E-AUCTION API READY")
    logger.info("=" * 80)
    
    if is_local():
        logger.info("")
        logger.info("📚 API Documentation: http://localhost:8000/docs")
        logger.info("🔍 Health Check: http://localhost:8000/health")
        logger.info("")

# ============================================================================
# SHUTDOWN EVENT
# ============================================================================
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Shutting down SCRAPCY E-Auction API")
    
    # Stop background scheduler
    if settings.SCHEDULER_ENABLED:
        from app.e_auction.tasks.scheduler import stop_scheduler
        stop_scheduler()
        logger.info("✅ Background scheduler stopped")
    
    logger.info("✅ Shutdown complete")

# ============================================================================
# ERROR HANDLERS (Optional - for production)
# ============================================================================
from fastapi import Request
from fastapi.responses import JSONResponse
from app.e_auction.utils.exceptions import EAuctionException

@app.exception_handler(EAuctionException)
async def eauction_exception_handler(request: Request, exc: EAuctionException):
    """Handle custom e-auction exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    # In production, don't expose internal errors
    if settings.APP_ENV == "production":
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Internal server error"}
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(exc)}
        )

# ============================================================================
# RUN APPLICATION (for development)
# ============================================================================
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=is_local(),  # Auto-reload only in local
        log_level=settings.log_level_value.lower()
    )
