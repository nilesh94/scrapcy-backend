from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

# Correct Imports based on your folder structure
from app.database.connection import get_db
from app.models.users import User 
from app.schemas import userSchema as schemas 
from app.utils import userUtils as utils 

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

# --- REGISTER ---
# CHANGE 1: Update response_model to the new schema that accepts token + user
@router.post("/register", response_model=schemas.UserRegistrationResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        # 1. Check if email already exists
        existing_user = db.query(User).filter(User.email == user.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Email already registered"
            )

        # 2. Check Seller Requirements
        if 'seller' == user.role:
            if not user.company_name or not user.gst_number or not user.address:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Sellers must provide Company Name, GST Number, and Registered Address."
                )

        # 3. Hash Password
        hashed_pwd = utils.hash_password(user.password)

        # 4. Create User
        new_user = User(
            **user.model_dump(exclude={"password"}), 
            hashed_password=hashed_pwd
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # 5. Create Token immediately for auto-login
        access_token = utils.create_access_token(data={"sub": new_user.email, "role": new_user.role})
        
        # CHANGE 2: Return the structure matching UserRegistrationResponse
        # We pass 'new_user' (the full DB object) to the 'user' key.
        # Pydantic will automatically extract 'id', 'created_at', etc. from it.
        return {
            "message": "Registration Successful",
            "access_token": access_token,
            "token_type": "bearer",
            "user": new_user 
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"error": "Database Transaction Failed", "details": str(e)}
        )

# --- LOGIN ---
@router.post("/login")
def login(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    try:
        # 1. Find User by Email
        user = db.query(User).filter(User.email == user_credentials.email).first()

        # 2. Validate User & Password
        if not user:
            raise HTTPException(status_code=403, detail="Invalid Credentials")
        
        if not utils.verify_password(user_credentials.password, user.hashed_password):
            raise HTTPException(status_code=403, detail="Invalid Credentials")

        # 3. Generate Token
        access_token = utils.create_access_token(data={"sub": user.email, "role": user.role})

        # 4. Return Success
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "first_name": user.first_name,
                "email": user.email,
                "role": user.role
            }
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Login Error: {e}")
        return JSONResponse(status_code=500, content={"error": "Login Failed", "details": str(e)})
