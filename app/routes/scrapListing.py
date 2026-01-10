from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import uuid
import io

from app.database.connection import get_db
from app.models.scrapListing import ScrapListing, ScrapImage
from app.models.scrapCategories import ScrapCategory, ScrapMaterial, ScrapGrade # NEW IMPORT
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
    
    # --- CHANGED: Now accepting IDs ---
    # scrap_type input is removed here, we derive it from IDs
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
    # We fetch the actual names so we can fill the legacy 'scrap_type' and 'grade' columns
    # This keeps your frontend working without breaking changes for existing cards.
    
    cat_obj = db.query(ScrapCategory).get(category_id)
    mat_obj = db.query(ScrapMaterial).get(material_id)
    grad_obj = db.query(ScrapGrade).get(grade_id) if grade_id else None

    if not cat_obj or not mat_obj:
         raise HTTPException(status_code=400, detail="Invalid Category or Material ID")

    # Construct the legacy strings
    # Level 1 Name for 'scrap_type' column
    legacy_scrap_type = cat_obj.scrap_type 
    # Combined Grade Name for 'grade' column (e.g., "HMS 1 - Heavy")
    legacy_grade_name = f"{mat_obj.material_name}" 
    if grad_obj:
        legacy_grade_name += f" ({grad_obj.grade_name})"

    new_listing = ScrapListing(
        seller_name=seller_name, company_name=company_name, email=email,
        phone=phone, alternate_phone=alternate_phone, gst_number=gst_number,
        
        # New IDs
        category_id=category_id,
        material_id=material_id,
        grade_id=grade_id,

        # Legacy Text Fields (Auto-Filled)
        scrap_type=legacy_scrap_type,  # e.g. "Metal Scrap"
        grade=legacy_grade_name,       # e.g. "MS Scrap (Heavy)"

        description=description,
        quantity=quantity, unit=unit, monthly_capacity=monthly_capacity,
        price_per_unit=price_per_unit, price_unit=price_unit,
        address=address, pickup_conditions=pickup_conditions,
        is_admin_entry=True
    )
    
    db.add(new_listing)
    db.flush()
    db.refresh(new_listing)

    # ... (Image Upload logic remains exactly the same as before) ...
    # Copy paste the image loop from your previous working file here
    uploaded_image_urls = []
    try:
        for img in images:
            unique_filename = f"{new_listing.id}_{uuid.uuid4()}_{img.filename}"
            file_content = io.BytesIO(await img.read())
            upload_result = upload_file_to_drive(file_content, unique_filename, img.content_type)
            new_image = ScrapImage(
                scrap_listing_id=new_listing.id, seller_email=email,
                image_url=upload_result['url'], drive_file_id=upload_result['id'], is_active=True
            )
            db.add(new_image)
            uploaded_image_urls.append(upload_result['url'])
        db.commit()
        return {"message": "Created", "listing_id": new_listing.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ... (Keep get_all and delete endpoints same as before) ...
@router.get("/all", response_model=List[schemas.ScrapListingResponse])
def get_all_listings(scrap_type: Optional[str] = None, skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    query = db.query(ScrapListing).options(joinedload(ScrapListing.images))
    if scrap_type and scrap_type != "All":
        query = query.filter(ScrapListing.scrap_type == scrap_type)
    return query.offset(skip).limit(limit).all()

@router.get("/{listing_id}", response_model=schemas.ScrapListingResponse)
def get_listing_detail(listing_id: int, db: Session = Depends(get_db)):
    listing = db.query(ScrapListing).options(joinedload(ScrapListing.images)).filter(ScrapListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing

@router.delete("/{listing_id}")
def delete_scrap_listing(listing_id: int, db: Session = Depends(get_db)):
    listing = db.query(ScrapListing).filter(ScrapListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    images = db.query(ScrapImage).filter(ScrapImage.scrap_listing_id == listing_id).all()
    for img in images:
        if img.drive_file_id:
            delete_file_from_drive(img.drive_file_id)
        db.delete(img)
    db.delete(listing)
    db.commit()
    return {"detail": "Deleted"}
