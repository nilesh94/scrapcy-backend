from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException, status
from datetime import datetime
from app.e_auction.models.auction import Auction
from app.e_auction.models.approval import AuctionApprovalLog
from app.e_auction.schemas.approval import ApprovalActionRequest
from app.e_auction.utils.enums import ApprovalStatus, AuctionStatus, ApprovalAction

class AuctionApprovalService:
    @staticmethod
    async def check_permission(db: Session, user_id: int, perm_key: str) -> bool:
        """
        Executes the Backend Permission Check Query[cite: 158].
        Verifies active user roles and permissions in scrapcy_app[cite: 161, 169].
        """
        query = text("""
            SELECT 1
            FROM   scrapcy_app.user_roles    ur
            JOIN   scrapcy_app.role_permissions rp ON rp.role_id = ur.role_id
            JOIN   scrapcy_app.permissions   p  ON p.perm_id  = rp.perm_id
            JOIN   scrapcy_app.roles         r  ON r.role_id  = ur.role_id
            WHERE  ur.user_id   = :user_id
            AND    ur.is_active = 1
            AND    r.is_active  = 1
            AND    p.perm_key   = :perm_key
        """)
        result = db.execute(query, {"user_id": user_id, "perm_key": perm_key}).fetchone()
        return result is not None

    @staticmethod
    async def process_approval_action(
        db: Session, 
        auction_id: int, 
        user_id: int, 
        user_role: str, 
        request: ApprovalActionRequest
    ):
        """
        Main State Machine implementing the v3.0 logic[cite: 201, 447].
        Enforces Dual-Write Rule for transactional integrity[cite: 153].
        """
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise HTTPException(status_code=404, detail="Auction not found")

        # Capture initial states for logging [cite: 61, 62]
        from_app_status = auction.approval_status
        from_auc_status = auction.status
        to_app_status = from_app_status
        to_auc_status = from_auc_status
        perm_key = ""

        # --- SUBMIT / RESUBMIT Logic [cite: 205, 223] ---
        if request.action in [ApprovalAction.SUBMIT, ApprovalAction.RESUBMIT]:
            perm_key = "auction:submit"
            to_auc_status = AuctionStatus.PENDING_APPROVAL
            to_app_status = ApprovalStatus.PENDING_L1
            # Set submitted_at timestamp only on first submit 
            if not auction.submitted_at:
                auction.submitted_at = datetime.utcnow()

        # --- L1 APPROVE Logic [cite: 206, 359] ---
        elif request.action == ApprovalAction.APPROVE_L1:
            perm_key = "auction:approve_l1"
            if from_app_status != ApprovalStatus.PENDING_L1:
                raise HTTPException(status_code=400, detail="Invalid L1 transition")
            to_app_status = ApprovalStatus.PENDING_L2
            auction.publish_l1_approved_by = user_id
            auction.publish_l1_approved_at = datetime.utcnow()
            auction.publish_l1_remarks = request.comments

        # --- L2 APPROVE Logic [cite: 207, 360] ---
        elif request.action == ApprovalAction.APPROVE_L2:
            perm_key = "auction:approve_l2"
            if from_app_status != ApprovalStatus.PENDING_L2:
                raise HTTPException(status_code=400, detail="Invalid L2 transition")
            to_app_status = ApprovalStatus.PENDING_ADMIN
            auction.publish_l2_approved_by = user_id
            auction.publish_l2_approved_at = datetime.utcnow()
            auction.publish_l2_remarks = request.comments

        # --- ADMIN APPROVE Logic (v3.0 Transition) [cite: 185, 208, 361] ---
        elif request.action == ApprovalAction.APPROVE_ADMIN:
            perm_key = "auction:approve_admin"
            if from_app_status != ApprovalStatus.PENDING_ADMIN:
                raise HTTPException(status_code=400, detail="Invalid Admin approval transition")
            to_auc_status = AuctionStatus.APPROVED
            to_app_status = ApprovalStatus.READY_TO_PUBLISH
            auction.publish_admin_approved_by = user_id
            auction.publish_admin_approved_at = datetime.utcnow()
            auction.publish_admin_remarks = request.comments

        # --- ADMIN PUBLISH Logic (OCI Trigger) [cite: 211, 362] ---
        elif request.action == ApprovalAction.PUBLISH:
            perm_key = "auction:publish_any"
            if from_auc_status != AuctionStatus.APPROVED or from_app_status != ApprovalStatus.READY_TO_PUBLISH:
                raise HTTPException(status_code=400, detail="Auction must be Admin-approved before publishing")
            to_auc_status = AuctionStatus.SCHEDULED
            to_app_status = ApprovalStatus.PUBLISHED # Terminal state [cite: 226]
            auction.published_at = datetime.utcnow()

        # --- REJECT Logic [cite: 222, 363] ---
        elif request.action == ApprovalAction.REJECT:
            perm_key = "auction:reject"
            to_auc_status = AuctionStatus.DRAFT
            to_app_status = ApprovalStatus.REJECTED

        # --- CANCEL Logic [cite: 225, 365] ---
        elif request.action == ApprovalAction.CANCEL:
            perm_key = "auction:cancel"
            to_auc_status = AuctionStatus.CANCELLED
            to_app_status = ApprovalStatus.CANCELLED

        # 1. Verify Permission [cite: 160]
        if not await AuctionApprovalService.check_permission(db, user_id, perm_key):
            raise HTTPException(status_code=403, detail="Forbidden: Insufficient permissions")

        # 2. Update Auction Table (Write 1) [cite: 154]
        auction.status = to_auc_status
        auction.approval_status = to_app_status
        auction.updated_at = datetime.utcnow()

        # 3. Create Approval Log entry (Write 2) [cite: 155]
        approval_log = AuctionApprovalLog(
            auction_id=auction_id,
            action_by=user_id,
            action_by_role=user_role,
            action=request.action,
            from_status=from_app_status, # Captures internal workflow change
            to_status=to_app_status,
            comments=request.comments
        )
        db.add(approval_log)

        try:
            db.commit()
            return {"status": "success", "auction_id": auction_id, "new_status": to_auc_status}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
