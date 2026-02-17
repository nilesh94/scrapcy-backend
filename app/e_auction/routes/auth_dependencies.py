"""
Authentication & Authorization Dependencies
Role-based access control (RBAC) helpers
Currently COMMENTED for testing - uncomment when auth is ready
"""
import logging
from typing import Optional, Union
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.database.connection import get_db

# Setup logging
logger = logging.getLogger(__name__)

# ============================================================================
# CURRENT USER DEPENDENCY (for testing)
# ============================================================================

async def get_current_user_id(
    authorization: str = Header(None),  # Uncomment when JWT ready
    db: Session = Depends(get_db)       # Added db to convert identity to numeric ID
) -> Union[int, str]:
    """
    Get current user ID from JWT token
    
    TODO: Uncomment when authentication is implemented
    Currently returns mock user ID for testing
    """
    # ==== COMMENTED FOR TESTING - UNCOMMENT WHEN AUTH READY ====
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        # Extract token from "Bearer <token>"
        parts = authorization.split(" ")
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization header format. Expected 'Bearer <token>'"
            )
        token = parts[1]
        
        # Verify JWT and extract user_id
        # Syncing with your actual utility file: app/utils/userUtils.py
        from app.utils import userUtils as utils
        
        payload = utils.verify_token(token)
        
        # Critical security check from your userUtils: must be an 'access' token
        if payload is None or payload.get("type") != "access":
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type or expired session"
            )

        # Your login logic uses "sub" for email.
        identity = payload.get("sub")
        
        if not identity:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User identity could not be verified from token"
            )
        
        # --- ABSOLUTELY REQUIRED FIX ---
        # Convert email identity to numeric ID so DB queries in services don't crash
        from app.models.users import User
        user = db.query(User.id).filter(User.email == identity).first()
        if user:
            return user.id
            
        return identity
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JWT Verification Failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please log in again."
        )
    # ==== END COMMENTED SECTION ====
    
    # TESTING ONLY - Remove this when auth is ready
    # return 1  # Mock user ID


async def get_current_user(
    identity: Union[int, str] = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> dict:
    """
    Get current user object
    
    TODO: Uncomment when User model is integrated
    """
    # ==== COMMENTED FOR TESTING - UNCOMMENT WHEN AUTH READY ====
    from app.models.users import User
    
    # Since your token uses the email address in 'sub', we look up by email
    if isinstance(identity, str) and "@" in identity:
        user = db.query(User).filter(User.email == identity).first()
    else:
        # Fallback for numeric ID if identity is an integer
        user = db.query(User).filter(User.id == identity).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User record not found"
        )
    
    # Safety Check: Oracle 0/1 to Boolean conversion
    # Based on your DB dump, we treat NULL or 1 as active, only 0 is blocked
    is_active = getattr(user, "is_active", 1)
    if is_active == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    return user
    # ==== END COMMENTED SECTION ====


# ============================================================================
# ROLE-BASED ACCESS CONTROL
# ============================================================================

class RoleChecker:
    """
    Dependency class for role-based access control
    
    Usage:
        @router.get("/admin/endpoint")
        async def admin_endpoint(
            current_user: dict = Depends(RoleChecker(["ADMIN"]))
        ):
            # Only accessible by ADMIN role
    """
    
    def __init__(self, allowed_roles: list):
        # SECURITY: Store as uppercase to prevent case-bypass attacks
        self.allowed_roles = [role.upper() for role in allowed_roles]
    
    async def __call__(
        self,
        current_user: dict = Depends(get_current_user)
    ):
        """Check if user has required role"""
        
        # ==== COMMENTED FOR TESTING - UNCOMMENT WHEN AUTH READY ====
        # Support both SQLAlchemy objects and dictionaries
        user_role_raw = getattr(current_user, "role", None) or current_user.get("role")
        
        if not user_role_raw:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has no assigned role"
            )

        user_role = str(user_role_raw).upper()
        
        if user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Security access denied. This action requires one of the following roles: {', '.join(self.allowed_roles)}"
            )
        # ==== END COMMENTED SECTION ====
        
        return current_user


# ============================================================================
# PERMISSION HELPERS
# ============================================================================

async def verify_auction_owner(
    auction_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> bool:
    """Verify user is the auction creator or has Administrative override"""
    from app.e_auction.models.auction import Auction
    
    auction = db.query(Auction).filter(Auction.id == auction_id).first()
    if not auction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Auction not found"
        )
    
    user_id = getattr(current_user, "id", None) or current_user.get("id")
    user_role = str(getattr(current_user, "role", "") or "").upper()

    # SECURITY: Admins can manage any auction, but Sellers can only manage their own
    if user_role == "ADMIN":
        return True

    if auction.created_by != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: You do not own this auction record"
        )
    
    return True


# ============================================================================
# COMMON DEPENDENCIES (Security Hardened)
# ============================================================================

# For seller-only endpoints
RequireSeller = RoleChecker(["SELLER", "ADMIN"]) 

# For buyer-only endpoints
RequireBuyer = RoleChecker(["BUYER", "ADMIN"])

# For admin-only endpoints
RequireAdmin = RoleChecker(["ADMIN"])

# For L1 approver
RequireL1Approver = RoleChecker(["L1_APPROVER", "ADMIN"])

# For L2 approver
RequireL2Approver = RoleChecker(["L2_APPROVER", "ADMIN"])

# Any authenticated user
RequireAuth = get_current_user
