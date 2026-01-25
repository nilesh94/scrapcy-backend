from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import traceback 

from app.database.connection import get_db
from app.models.requirements import BuyerRequirement
from app.models.users import User
from app.schemas import requirementSchema as schemas
from app.utils.dependencies import get_current_user_optional, get_current_user

router = APIRouter(
    prefix="/requirements",
    tags=["Buyer Requirements"]
)

# --- 1. CREATE REQUIREMENT (Guests & Users) ---
@router.post("/create", response_model=schemas.RequirementOut)
def create_requirement(
    req: schemas.RequirementCreate, 
    db: Session = Depends(get_db),
    # Use optional auth to allow guests
    current_user: Optional[User] = Depends(get_current_user_optional) 
):
    # 1. Prepare the DB object with common fields
    db_req = BuyerRequirement(
        scrap_type=req.scrapType,
        category=req.category,
        material=req.material,
        form=req.form,
        grade=req.grade,
        locations=req.locations, # Maps to PREFERRED_LOCATIONS in DB
        description=req.description,
        note=req.note,
        status="OPEN"
    )

    # 2. Assign User ID or Validate Guest Details
    if current_user:
        # Link to logged-in user
        db_req.user_id = current_user.id
    else:
        # User is NOT logged in (Guest Mode)
        # We must enforce guest fields here because Pydantic schema makes them Optional
        # (to allow logged-in users to omit them).
        
        # Check if ALL guest fields are present
        if not all([req.guestName, req.guestEmail, req.guestPhone, req.guestCompany, req.guestGst]):
             # This raises a 400 Bad Request which the frontend can handle
             raise HTTPException(
                 status_code=400, 
                 detail="All guest details (Name, Email, Phone, Company, GST) are mandatory for non-logged in users."
             )
        
        db_req.guest_name = req.guestName
        db_req.guest_email = req.guestEmail
        db_req.guest_phone = req.guestPhone
        db_req.guest_company = req.guestCompany
        db_req.guest_gst = req.guestGst

    # 3. Save to Database
    try:
        db.add(db_req)
        db.commit()
        db.refresh(db_req)
        return db_req
    except Exception as e:
        print("Error saving requirement:", e)
        traceback.print_exc() # Print full stack trace for debugging
        db.rollback()
        # Raise a 500 error only for unexpected database failures
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")

# --- 2. GET MY REQUIREMENTS (Logged-in Only) ---
@router.get("/my", response_model=List[schemas.RequirementOut])
def get_my_requirements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # Must be logged in
):
    # Filter: User's ID AND Status is NOT 'DELETED'
    requirements = db.query(BuyerRequirement).filter(
        BuyerRequirement.user_id == current_user.id,
        BuyerRequirement.status != 'DELETED'
    ).order_by(BuyerRequirement.created_at.desc()).all()
    
    return requirements

# --- 3. UPDATE STATUS (Close, Fulfill, Soft Delete) ---
@router.put("/{req_id}/status")
def update_status(
    req_id: int,
    status_update: schemas.RequirementUpdateStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Find Requirement
    req = db.query(BuyerRequirement).filter(BuyerRequirement.id == req_id).first()
    
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
        
    # Check Ownership
    if req.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    # Validate Status
    valid_statuses = ['OPEN', 'CLOSED', 'FULFILLED', 'DELETED']
    if status_update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")

    # Update Status (Soft Delete is just setting status='DELETED')
    req.status = status_update.status
    db.commit()
    
    return {"message": f"Status updated to {status_update.status}"}
