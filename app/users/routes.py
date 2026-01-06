from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from . import models, schemas, utils

router = APIRouter(
    prefix="/users",  # All endpoints here start with /users
    tags=["Users"]
)

@router.post("/register", response_model=schemas.UserOut)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    
    # 1. Check if email exists
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email already registered"
        )

    # 2. Hash Password
    hashed_pwd = utils.hash_password(user.password)

    # 3. Create User
    new_user = models.User(
        **user.model_dump(exclude={"password"}), 
        hashed_password=hashed_pwd
    )

    # 4. Save to DB
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
