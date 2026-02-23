from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

class PermissionBase(BaseModel):
    perm_key: str
    category: Optional[str] = None [cite: 91]
    description: Optional[str] = None [cite: 92]
    model_config = ConfigDict(from_attributes=True)

class RoleBase(BaseModel):
    role_code: str [cite: 80]
    role_name: str [cite: 81]
    is_internal: int [cite: 82]
    model_config = ConfigDict(from_attributes=True)

class UserRoleResponse(BaseModel):
    user_id: int [cite: 102]
    role: RoleBase [cite: 103]
    is_active: int [cite: 106]
    model_config = ConfigDict(from_attributes=True)

class ApprovalLogResponse(BaseModel):
    log_id: int [cite: 56]
    auction_id: int [cite: 57]
    action_by: int [cite: 58]
    action_by_role: str [cite: 59]
    action: str [cite: 60]
    from_status: str [cite: 61]
    to_status: str [cite: 62]
    comments: Optional[str] = None [cite: 63]
    actioned_at: datetime [cite: 64]
    model_config = ConfigDict(from_attributes=True)

class ApprovalActionRequest(BaseModel):
    """Schema for managers to submit an approval or rejection"""
    action: str  # SUBMIT, APPROVE_L1, APPROVE_L2, APPROVE_ADMIN, REJECT 
    comments: Optional[str] = None [cite: 63]

class AuctionApprovalDetails(BaseModel):
    approval_status: str [cite: 33]
    submitted_at: Optional[datetime] = None [cite: 27]
    created_by_role: Optional[str] = None [cite: 26]
    
    # L1 Metadata 
    publish_l1_approved_by: Optional[int] = None
    publish_l1_approved_at: Optional[datetime] = None
    publish_l1_remarks: Optional[str] = None
    
    # L2 Metadata 
    publish_l2_approved_by: Optional[int] = None
    publish_l2_approved_at: Optional[datetime] = None
    publish_l2_remarks: Optional[str] = None
    
    # Admin Metadata [cite: 20, 21, 22]
    publish_admin_approved_by: Optional[int] = None
    publish_admin_approved_at: Optional[datetime] = None
    publish_admin_remarks: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)
