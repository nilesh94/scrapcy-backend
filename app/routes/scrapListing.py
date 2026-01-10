from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import uuid
import io

from app.database.connection import get_db
from app.models.scrapListing import ScrapListing, ScrapImage
from app.schemas import scrapListingSchema as schemas
from app.utils.driveUtils import upload_file_to_drive, delete_file_from_drive 

router = APIRouter(
    prefix="/scrap",
    tags=["Scrap Listings"]
)

# --- 1. CREATE LISTING (ADMIN) ---
@router.post("/add", status_code=status.HTTP_201_CREATED)
async def add_scrap_listing(
    # Seller Details
    seller_name: str = Form(...),
    company_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    alternate_phone: Optional[str] = Form(None),
    gst_number: str = Form(...),
    
    # Scrap Details
    scrap_type: str = Form(...),
    grade: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    quantity: float = Form(...),
    unit: str = Form(...),
    monthly_capacity: Optional[str] = Form(None),
    price_per_unit: float = Form(...),
    price_unit: str = Form(...),
    
    # Location Details
    address: str = Form(...),
    pickup_conditions: Optional[str] = Form(None),
    
    # Files & DB
    images: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    # --- VALIDATION: IMAGE COUNT ---
    if len(images) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Maximum 5 images allowed per listing."
        )
    
    # A. Check for Duplicate GST (Optional: You might want to allow same GST for different scraps)
    # if gst_number:
    #     existing_listing = db.query(ScrapListing).filter(ScrapListing.gst_number == gst_number).first()
    #     if existing_listing:
    #         raise HTTPException(status_code=400, detail="A listing with this GST Number already exists.")

    # B. Create the Parent Listing
    new_listing = ScrapListing(
        seller_name=seller_name,
        company_name=company_name,
        email=email,
        phone=phone,
        alternate_phone=alternate_phone,
        gst_number=gst_number,
        
        scrap_type=scrap_type,
        grade=grade,
        description=description,
        quantity=quantity,
        unit=unit,
        monthly_capacity=monthly_capacity,
        price_per_unit=price_per_unit,
        price_unit=price_unit,
        
        address=address,
        pickup_conditions=pickup_conditions,
        
        is_admin_entry=True
    )
    
    db.add(new_listing)
    db.flush()
    db.refresh(new_listing)

    # C. Handle Image Uploads
    uploaded_image_urls = []
    
    try:
        for img in images:
            unique_filename = f"{new_listing.id}_{uuid.uuid4()}_{img.filename}"
            file_content = io.BytesIO(await img.read())
            
            # --- UPDATE: Returns dict { 'id': '...', 'url': '...' } ---
            upload_result = upload_file_to_drive(file_content, unique_filename, img.content_type)
            
            new_image = ScrapImage(
                scrap_listing_id=new_listing.id,
                seller_email=email,
                image_url=upload_result['url'],       # Viewable Link
                drive_file_id=upload_result['id'],    # <--- Saving Drive ID for deletion
                is_active=True
            )
            db.add(new_image)
            uploaded_image_urls.append(upload_result['url'])
            
        db.commit()
        
        return {
            "message": "Scrap listing created successfully",
            "listing_id": new_listing.id,
            "images_count": len(uploaded_image_urls)
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        print(f"Upload Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload images: {str(e)}")


# --- 2. GET ALL LISTINGS ---
@router.get("/all", response_model=List[schemas.ScrapListingResponse])
def get_all_listings(scrap_type: Optional[str] = None, skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    query = db.query(ScrapListing).options(joinedload(ScrapListing.images))
    if scrap_type and scrap_type != "All":
        query = query.filter(ScrapListing.scrap_type == scrap_type)
    return query.offset(skip).limit(limit).all()

# --- 3. GET SINGLE LISTING ---
@router.get("/{listing_id}", response_model=schemas.ScrapListingResponse)
def get_listing_detail(listing_id: int, db: Session = Depends(get_db)):
    listing = db.query(ScrapListing).options(joinedload(ScrapListing.images)).filter(ScrapListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing

# --- 4. DELETE LISTING ---
@router.delete("/{listing_id}")
def delete_scrap_listing(listing_id: int, db: Session = Depends(get_db)):
    # 1. Find Listing
    listing = db.query(ScrapListing).filter(ScrapListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # 2. Find Associated Images
    images = db.query(ScrapImage).filter(ScrapImage.scrap_listing_id == listing_id).all()

    # 3. Delete from Google Drive
    for img in images:
        if img.drive_file_id:
            delete_file_from_drive(img.drive_file_id)
        else:
            print(f"Skipping Drive delete for image {img.id} (No Drive ID found)")

    # 4. Delete from Database
    # Note: If you have ON DELETE CASCADE set in your DB models, deleting the listing 
    # might automatically delete images. But being explicit here is safer for logic.
    for img in images:
        db.delete(img)
        
    db.delete(listing)
    db.commit()

    return {"detail": "Listing and associated Drive images deleted successfully"}
