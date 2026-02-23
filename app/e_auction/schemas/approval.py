from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

class PermissionBase(BaseModel):
    perm_key: str
    category: Optional[str] = None
    description: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class RoleBase(BaseModel):
    role_code: str
    role_name: str
    is_internal: int
    model_config = ConfigDict(from_attributes=True)

class UserRoleResponse(BaseModel):
    user_id: int
    role: RoleBase
    is_active: int
    model_config = ConfigDict(from_attributes=True)

class ApprovalLogResponse(BaseModel):
    log_id: int
    auction_id: int
    action_by: int
    action_by_role: str
    action: str
    from_status: str
    to_status: str
    comments: Optional[str] = None
    actioned_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ApprovalActionRequest(BaseModel):
    """Schema for managers to submit an approval or rejection"""
    action: str  # SUBMIT, APPROVE_L1, APPROVE_L2, APPROVE_ADMIN, REJECT 
    comments: Optional[str] = None

class AuctionApprovalDetails(BaseModel):
    approval_status: str
    submitted_at: Optional[datetime] = None
    created_by_role: Optional[str] = None
    
    # L1 Metadata 
    publish_l1_approved_by: Optional[int] = None
    publish_l1_approved_at: Optional[datetime] = None
    publish_l1_remarks: Optional[str] = None
    
    # L2 Metadata 
    publish_l2_approved_by: Optional[int] = None
    publish_l2_approved_at: Optional[datetime] = None
    publish_l2_remarks: Optional[str] = None
    
    # Admin Metadata
    publish_admin_approved_by: Optional[int] = None
    publish_admin_approved_at: Optional[datetime] = None
    publish_admin_remarks: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)
