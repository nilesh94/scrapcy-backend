from datetime import datetime # Required for timestamp
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

# Correct Imports
from app.database.connection import get_db
from app.models.users import User 
from app.schemas import userSchema as schemas 
from app.utils import userUtils as utils 

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

# --- REGISTER ---
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

        # 2. MANDATORY BUSINESS VALIDATION (For ALL Roles)
        if not user.company_name or not user.gst_number or not user.address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All users must provide Company Name, GST Number, and Registered Address."
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
        
        # 6. Return Response
        return {
            "message": "Registration Successful",
            "access_token": access_token,
            "token_type": "bearer",
            "user": new_user 
        }

    except HTTPException as he:
        # Re-raise HTTP exceptions (like 400 Bad Request) so they go to frontend correctly
        raise he
    except Exception as e:
        # Log the actual error for the developer
        print(f"CRITICAL REGISTER ERROR: {str(e)}")
        db.rollback()
        # Send a safe, generic message to the frontend
        return JSONResponse(
            status_code=500,
            content={"error": "Registration failed due to a server error. Please try again later."}
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

        # --- NEW: UPDATE LAST LOGIN TIME ---
        try:
            user.last_login_at = datetime.now()
            db.commit()
        except Exception as db_e:
            # If updating time fails, just log it but don't stop the login
            print(f"WARNING: Could not update login timestamp: {str(db_e)}")
            db.rollback() 
        # -----------------------------------

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
        # Log the actual internal error
        print(f"CRITICAL LOGIN ERROR: {str(e)}")
        
        # Return a sanitized error message to the user
        return JSONResponse(
            status_code=500, 
            content={"error": "Login failed. Please contact support if the issue persists."}
        )

# --- NEW: VALIDATE TOKEN / ME ENDPOINT ---
# This is used by the frontend SessionTimeout to keep the session alive
@router.get("/me")
def get_current_user_profile(current_user: User = Depends(utils.get_current_user)):
    """
    Used by frontend to check if the token is still valid.
    If valid, returns user info.
    If expired/invalid, 'get_current_user' dependency raises 401 automatically.
    """
    return {
        "id": current_user.id,
        "first_name": current_user.first_name,
        "email": current_user.email,
        "role": current_user.role,
        "company_name": current_user.company_name
    }
