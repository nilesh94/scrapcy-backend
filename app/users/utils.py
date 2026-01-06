# File: app/users/utils.py

from passlib.context import CryptContext

# Setup bcrypt password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Takes a plain password and returns a hashed string."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Checks if a plain password matches the hash (For Login)."""
    return pwd_context.verify(plain_password, hashed_password)
