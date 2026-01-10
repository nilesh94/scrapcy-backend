from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import uuid
import io

from app.database.connection import get_db
from app.models.scrapListing import ScrapListing, ScrapImage
# Import the definition models for lookups
from app.models.scrapCategories import ScrapCategory, ScrapMaterial, ScrapGrade 
from app.schemas import scrapListingSchema as schemas
from app.utils.driveUtils import upload_file_to_drive, delete_file_from_drive 

router = APIRouter(
    prefix="/scrap",
    tags=["Scrap Listings"]
)

# --- 1. CREATE LISTING (ADMIN) ---
@router.post("/add", status_code=status.HTTP_201_CREATED)
async def add_scrap_listing(
    seller_name: str = Form(...),
    company_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    alternate_phone: Optional[str] = Form(None),
    gst_number: str = Form(...),
    
    # --- CHANGED: Accepting IDs instead of text ---
    category_id: int = Form(...),
    material_id: int = Form(...),
    grade_id: Optional[int] = Form(None),
    
    description: Optional[str] = Form(None),
    quantity: float = Form(...),
    unit: str = Form(...),
    monthly_capacity: Optional[str] = Form(None),
    price_per_unit: float = Form(...),
    price_unit: str = Form(...),
    
    address: str = Form(...),
    pickup_conditions: Optional[str] = Form(None),
    
    images: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    if len(images) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 images allowed.")

    # --- LOOKUP NAMES FROM IDs ---
    # We fetch the actual objects to validate IDs and populate legacy text columns
    
    cat_obj = db.query(ScrapCategory).get(category_id)
    mat_obj = db.query(ScrapMaterial).get(material_id)
    grad_obj = db.query(ScrapGrade).get(grade_id) if grade_id else None

    if not cat_obj:
         raise HTTPException(status_code=400, detail="Invalid Category ID")
    if not mat_obj:
         raise HTTPException(status_code=400, detail="Invalid Material ID")

    # --- CONSTRUCT LEGACY STRINGS ---
    # This ensures your old frontend logic (which relies on text) still works
    # Assumption: Your Category/Material models have a '.name' attribute.
    
    legacy_scrap_type = cat_obj.name  # Maps Category Name -> Scrap Type
    
    legacy_grade_name = f"{mat_obj.name}" # Maps Material Name -> Grade
    if grad_obj:
        legacy_grade_name += f" ({grad_obj.name})"

    new_listing = ScrapListing(
        seller_name=seller_name, company_name=company_name, email=email,
        phone=phone, alternate_phone=alternate_phone, gst_number=gst_number,
        
        # New Relationship IDs
        category_id=category_id,
        material_id=material_id,
        grade_id=grade_id,

        # Legacy Text Fields (Auto-Filled)
        scrap_type=legacy_scrap_type,
        grade=legacy_grade_name,

        description=description,
        quantity=quantity, unit=unit, monthly_capacity=monthly_capacity,
        price_per_unit=price_per_unit, price_unit=price_unit,
        address=address, pickup_conditions=pickup_conditions,
        is_admin_entry=True
    )
    
    db.add(new_listing)
    db.flush()
    db.refresh(new_listing)

    # --- IMAGE UPLOAD LOGIC ---
    uploaded_image_urls = []
    try:
        for img in images:
            unique_filename = f"{new_listing.id}_{uuid.uuid4()}_{img.filename}"
            # Read file content
            file_content = io.BytesIO(await img.read())
            # Upload to Drive
            upload_result = upload_file_to_drive(file_content, unique_filename, img.content_type)
            
            # Save Image Record
            new_image = ScrapImage(
                scrap_listing_id=new_listing.id, 
                seller_email=email,
                image_url=upload_result['url'], 
                drive_file_id=upload_result['id'], 
                is_active=True
            )
            db.add(new_image)
            uploaded_image_urls.append(upload_result['url'])
        
        db.commit()
        return {"message": "Created", "listing_id": new_listing.id}
    
    except Exception as e:
        db.rollback()
        # Clean up already created listing if image upload fails
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# --- 2. GET ALL LISTINGS ---
@router.get("/all", response_model=List[schemas.ScrapListingResponse])
def get_all_listings(
    scrap_type: Optional[str] = None, 
    skip: int = 0, 
    limit: int = 20, 
    db: Session = Depends(get_db)
):
    # CRITICAL UPDATE: eager load the relations so Pydantic can serialize the names
    query = db.query(ScrapListing).options(
        joinedload(ScrapListing.images),
        joinedload(ScrapListing.category_ref),
        joinedload(ScrapListing.material_ref),
        joinedload(ScrapListing.grade_ref)
    )
    
    # Filter by legacy scrap_type string (Backward compatibility)
    if scrap_type and scrap_type != "All":
        query = query.filter(ScrapListing.scrap_type == scrap_type)
        
    return query.order_by(ScrapListing.created_at.desc()).offset(skip).limit(limit).all()

# --- 3. GET SINGLE LISTING ---
@router.get("/{listing_id}", response_model=schemas.ScrapListingResponse)
def get_listing_detail(listing_id: int, db: Session = Depends(get_db)):
    # CRITICAL UPDATE: eager load relations here too
    listing = db.query(ScrapListing).options(
        joinedload(ScrapListing.images),
        joinedload(ScrapListing.category_ref),
        joinedload(ScrapListing.material_ref),
        joinedload(ScrapListing.grade_ref)
    ).filter(ScrapListing.id == listing_id).first()
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing

# --- 4. DELETE LISTING ---
@router.delete("/{listing_id}")
def delete_scrap_listing(listing_id: int, db: Session = Depends(get_db)):
    listing = db.query(ScrapListing).filter(ScrapListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    # Delete images from Drive first
    images = db.query(ScrapImage).filter(ScrapImage.scrap_listing_id == listing_id).all()
    for img in images:
        if img.drive_file_id:
            try:
                delete_file_from_drive(img.drive_file_id)
            except Exception:
                pass # Continue deleting DB record even if Drive fails
        db.delete(img)
        
    db.delete(listing)
    db.commit()
    return {"detail": "Deleted"}
