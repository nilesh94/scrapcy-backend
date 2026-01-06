import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import from our new folders
from app.database.connection import engine, Base
from app.users import routes as user_routes

# 1. Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize App
app = FastAPI(title="Scrapcy Backend")

# 2. CORS Config
origins = [
    "http://localhost:3000",
    "https://scrapcy-frontend.onrender.com",
    "https://scrapcy.nexusmeta.in",
    "*"  # Keep this for now to ensure smooth connections
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Create Database Tables
# We wrap this in a try/except block so the app doesn't crash 
# immediately if the DB is warming up.
try:
    logger.info("Connecting to Oracle Database...")
    # This creates the 'users' table if it doesn't exist
    Base.metadata.create_all(bind=engine)
    logger.info("Successfully connected and tables checked.")
except Exception as e:
    logger.error(f"Database connection warning: {e}")

# 4. Include Routers
# This loads the /users/register endpoint from the other file
app.include_router(user_routes.router)

@app.get("/")
def read_root():
    return {"message": "Scrapcy API is running & modularized!"}
