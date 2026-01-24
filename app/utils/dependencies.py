from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

# Database and Models
from app.database.connection import get_db
from app.models.users import User

# Import pure utility function
from app.utils.userUtils import verify_token 

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="users/login", auto_error=False)

# 1. Strict Dependency (User MUST be logged in)
async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> User:
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_email = payload.get("sub")
    if user_email is None:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    user = db.query(User).filter(User.email == user_email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# 2. Optional Dependency (User MIGHT be logged in, or is Guest)
async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme_optional), 
    db: Session = Depends(get_db)
) -> Optional[User]:
    if not token:
        return None
    
    payload = verify_token(token)
    if not payload:
        return None
        
    user_email = payload.get("sub")
    if user_email is None:
        return None
        
    return db.query(User).filter(User.email == user_email).first()
