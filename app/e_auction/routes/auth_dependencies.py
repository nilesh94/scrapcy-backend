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
        token = authorization.split(" ")[1]
        
        # Verify JWT and extract user_id
        from app.auth.jwt_handler import verify_token
        payload = verify_token(token)
        user_id = payload.get("user_id")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        return user_id
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
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
    from app.models.user import User
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user
    # ==== END COMMENTED SECTION ====
    
    # TESTING ONLY
    # return {
    #     "id": user_id,
    #     "role": "SELLER",  # Mock role
    #     "is_active": True
    # }


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
        self.allowed_roles = allowed_roles
    
    async def __call__(
        self,
        current_user: dict = Depends(get_current_user)
    ):
        """Check if user has required role"""
        
        # ==== COMMENTED FOR TESTING - UNCOMMENT WHEN AUTH READY ====
        # Support both SQLAlchemy objects and dictionaries
        user_role = getattr(current_user, "role", None) or current_user.get("role")
        
        if user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(self.allowed_roles)}"
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
    """Verify user is the auction creator"""
    from app.e_auction.models import Auction
    
    auction = db.query(Auction).filter(Auction.id == auction_id).first()
    if not auction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Auction not found"
        )
    
    # ==== COMMENTED FOR TESTING - UNCOMMENT WHEN AUTH READY ====
    user_id = getattr(current_user, "id", None) or current_user.get("id")
    if auction.created_by != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only auction creator can perform this action"
        )
    # ==== END COMMENTED SECTION ====
    
    return True


# ============================================================================
# COMMON DEPENDENCIES
# ============================================================================

# FIX: Removed pre-wrapped Depends() to fix "not a callable object" TypeError
# Use these as `Depends(RequireAdmin)` in your route files.

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


# ============================================================================
# USAGE EXAMPLES (in routes)
# ============================================================================

"""
# Example 1: Public endpoint (no auth required)
@router.get("/auctions/browse")
async def browse_auctions():
    # Anyone can access
    pass

# Example 2: Authenticated user (any role)
@router.get("/my-bids")
async def get_my_bids(
    current_user: dict = Depends(RequireAuth)  # Just need to be logged in
):
    pass

# Example 3: Seller only
@router.post("/auctions")
async def create_auction(
    current_user: dict = Depends(RequireSeller)  # Only SELLER or ADMIN
):
    pass

# Example 4: Admin only
@router.post("/admin/approve")
async def approve_auction(
    current_user: dict = Depends(RequireAdmin)  # Only ADMIN
):
    pass

# Example 5: Multiple roles
@router.post("/bid")
async def place_bid(
    current_user: dict = Depends(RequireBuyer)  # Only BUYER or ADMIN
):
    pass

# Example 6: Custom permission check
@router.put("/auctions/{auction_id}")
async def update_auction(
    auction_id: int,
    current_user: dict = Depends(RequireAuth),
    is_owner: bool = Depends(verify_auction_owner)  # Custom check
):
    pass
"""
