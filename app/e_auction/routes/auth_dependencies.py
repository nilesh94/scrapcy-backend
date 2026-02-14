"""
Authentication & Authorization Dependencies
Role-based access control (RBAC) helpers
Currently COMMENTED for testing - uncomment when auth is ready
"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.database.connection import get_db


# ============================================================================
# CURRENT USER DEPENDENCY (for testing)
# ============================================================================

async def get_current_user_id(
    authorization: str = Header(None)  # Uncomment when JWT ready
) -> int:
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
        from app.auth.jwt_handler import verify_token
        payload = verify_token(token)
        
        # Security Note: We check multiple common keys to ensure compatibility with your JWT handler
        user_id = payload.get("user_id") or payload.get("id") or payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User identity could not be verified from token"
            )
        
        return int(user_id)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please log in again."
        )
    # ==== END COMMENTED SECTION ====
    
    # TESTING ONLY - Remove this when auth is ready
    # return 1  # Mock user ID


async def get_current_user(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> dict:
    """
    Get current user object
    
    TODO: Uncomment when User model is integrated
    """
    # ==== COMMENTED FOR TESTING - UNCOMMENT WHEN AUTH READY ====
    from app.models.users import User
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User record not found"
        )
    
    # Safety Check: Oracle 0/1 to Boolean conversion
    is_active = getattr(user, "is_active", 1)
    if is_active == 0 or is_active is False:
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

# FIX: Removed pre-wrapped Depends() to fix "not a callable object" TypeError

# SECURITY: We explicitly list roles. 
# If you want an Admin to be able to create an auction for testing/support:
RequireSeller = RoleChecker(["SELLER", "ADMIN"]) 

# For buyer-only endpoints (Admins usually need to see what buyers see for support)
RequireBuyer = RoleChecker(["BUYER", "ADMIN"])

# For admin-only endpoints (STRICT: Sellers cannot access these)
RequireAdmin = RoleChecker(["ADMIN"])

# For L1 approver (Strict workflow)
RequireL1Approver = RoleChecker(["L1_APPROVER", "ADMIN"])

# For L2 approver (Strict workflow)
RequireL2Approver = RoleChecker(["L2_APPROVER", "ADMIN"])

# Any authenticated user
RequireAuth = get_current_user
