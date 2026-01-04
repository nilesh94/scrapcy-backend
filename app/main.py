import logging
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from . import models, schemas, database

# 1. Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize App
app = FastAPI()

# 2. CORS Config
origins = [
    "http://localhost:3000",
    "https://scrapcy-frontend.onrender.com", 
    "https://scrapcy.nexusmeta.in"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Create Database Tables (With Error Handling)
try:
    logger.info("Attempting to connect to Oracle DB and create tables...")
    models.Base.metadata.create_all(bind=database.engine)
    logger.info("Tables created successfully.")
except Exception as e:
    logger.error(f"Error creating tables: {e}")
    # We continue running so /docs still loads, but DB actions will fail until fixed.

# Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

@app.get("/")
def read_root():
    return {"message": "Scrapcy API is running"}

@app.post("/register", response_model=schemas.UserOut)
def register_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    # 1. Check if email already exists
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2. Hash the password
    hashed_pw = get_password_hash(user.password)

    # 3. Create User Object
    new_user = models.User(
        role=user.role,
        first_name=user.firstName,
        last_name=user.lastName,
        email=user.email,
        phone=user.phone,
        hashed_password=hashed_pw,
        
        # Company Fields
        company_name=user.companyName,
        business_type=user.businessType,
        industry=user.industry,
        turnover=user.turnover,
        gst_number=user.gstNumber,
        pan_number=user.panNumber,
        address=user.address,
        city=user.city,
        state=user.state,
        pincode=user.pincode
    )

    # 4. Save to DB
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except Exception as e:
        logger.error(f"Error saving user: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Database Error: Could not save user")
