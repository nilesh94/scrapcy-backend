from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.routes.users import get_current_user
from app.e_auction.services.approval_service import AuctionApprovalService
from app.e_auction.schemas.approval import ApprovalActionRequest
from app.e_auction.utils.enums import ApprovalAction

router = APIRouter(
    prefix="/api/v1/e-auction/approvals",
    tags=["Auction Approval Workflow"]
)

@router.post("/{auction_id}/action")
async def perform_approval_action(
    auction_id: int,
    request: ApprovalActionRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Unified endpoint for all workflow actions[cite: 11, 201].
    Enforces role-based boundaries (e.g., Admins cannot Approve L1).
    """
    
    # Process the transition using the State Machine logic [cite: 201]
    # This service method handles permission verification and the Dual-Write Rule [cite: 152, 158]
    result = await AuctionApprovalService.process_approval_action(
        db=db,
        auction_id=auction_id,
        user_id=current_user.id,
        user_role=current_user.role_code, 
        request=request
    )

    return result
