import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 1. Import Database Connection
from app.database.connection import engine, Base

# 2. Import Models 
# (CRITICAL: Must be imported so Base.metadata knows they exist to create tables)
from app.models import users as user_models
from app.models import scrapListing as scrap_models

# 3. Import Routers 
# (Corrected paths based on your screenshot structure)
from app.routes import users as user_routes
from app.routes import scrapListing as scrap_routes

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize App
app = FastAPI(title="Scrapcy Backend")

# CORS Config
origins = [
    "http://localhost:3000",
    "https://scrapcy-frontend.onrender.com",
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

# Create Database Tables
try:
    logger.info("Connecting to Database...")
    # This checks for models imported above and creates tables if missing
    Base.metadata.create_all(bind=engine)
    logger.info("Successfully connected and tables checked.")
except Exception as e:
    logger.error(f"Database connection warning: {e}")

# Include Routers
# This maps the routes defined in your files to the API
app.include_router(user_routes.router)
app.include_router(scrap_routes.router)

@app.get("/")
def read_root():
    return {"message": "Scrapcy API is running & modularized!"}
