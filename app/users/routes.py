from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse # Import this
from sqlalchemy.orm import Session
from app.database.connection import get_db
from . import models, schemas, utils

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.post("/register", response_model=schemas.UserOut)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        # 1. Check if email already exists
        existing_user = db.query(models.User).filter(models.User.email == user.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Email already registered"
            )

        # 2. Check Seller Requirements
        if user.role == 'seller':
            if not user.company_name or not user.gst_number or not user.address:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Sellers must provide Company Name, GST Number, and Registered Address."
                )

        # 3. Hash Password
        hashed_pwd = utils.hash_password(user.password)

        # 4. Create User
        new_user = models.User(
            **user.model_dump(exclude={"password"}), 
            hashed_password=hashed_pwd
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

    except HTTPException as he:
        # Re-raise standard HTTP exceptions (like 400 Bad Request)
        raise he
    except Exception as e:
        db.rollback()
        # DEBUGGING: This will print the EXACT error to your curl response
        # so you can see if it is "Table not found" or "Column missing"
        return JSONResponse(
            status_code=500,
            content={"error": "Database Transaction Failed", "details": str(e)}
        )
