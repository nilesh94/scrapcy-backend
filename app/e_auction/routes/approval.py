from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.auth.dependencies import get_current_user  # Assuming this exists
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
    Unified endpoint for all workflow actions: 
    SUBMIT, APPROVE_L1, APPROVE_L2, APPROVE_ADMIN, PUBLISH, REJECT, CANCEL, RESUBMIT.
    [cite: 11, 201, 357]
    """
    
    # 1. Map actions to their required permission keys from the design doc
    # [cite: 124, 407]
    permission_map = {
        ApprovalAction.SUBMIT: "auction:submit",
        ApprovalAction.RESUBMIT: "auction:submit",
        ApprovalAction.APPROVE_L1: "auction:approve_l1",
        ApprovalAction.APPROVE_L2: "auction:approve_l2",
        ApprovalAction.APPROVE_ADMIN: "auction:approve_admin",
        ApprovalAction.PUBLISH: "auction:publish_any",
        ApprovalAction.REJECT: "auction:reject",
        ApprovalAction.CANCEL: "auction:cancel"
    }

    perm_key = permission_map.get(request.action)
    if not perm_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid approval action requested."
        )

    # 2. Execute the Backend Permission Check Query [cite: 158, 169]
    has_permission = await AuctionApprovalService.check_permission(
        db, 
        current_user.id, 
        perm_key
    )
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User does not have required permission: {perm_key}"
        )

    # 3. Process the transition using the State Machine logic [cite: 201, 152]
    # This service method enforces the Dual-Write Rule [cite: 152, 155]
    result = await AuctionApprovalService.process_approval_action(
        db=db,
        auction_id=auction_id,
        user_id=current_user.id,
        user_role=current_user.role_code, # Extracted from user object
        request=request
    )

    return result
