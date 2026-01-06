# File: app/users/routes.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from . import models, schemas, utils

# Create the router
# All endpoints in this file will start with /users
router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.post("/register", response_model=schemas.UserOut)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    
    # 1. Check if email already exists
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email already registered"
        )

    # 2. Hash the password
    hashed_pwd = utils.hash_password(user.password)

    # 3. Create the User Object
    # We use model_dump(exclude={'password'}) to convert Pydantic model to a dict,
    # skipping the plain password so we can swap it for the hashed one.
    new_user = models.User(
        **user.model_dump(exclude={"password"}), 
        hashed_password=hashed_pwd
    )

    # 4. Save to Database
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except Exception as e:
        db.rollback()
        # Log the error internally here if you had a logger
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")
