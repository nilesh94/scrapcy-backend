from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import uuid
import io

# Imports from your project structure
from database import get_db
from models import ScrapListing, ScrapImage
from drive_utils import upload_file_to_drive

router = APIRouter(
    prefix="/scrap",
    tags=["Scrap Listings"]
)

# --- 1. CREATE LISTING (ADMIN) ---
@router.post("/add", status_code=status.HTTP_201_CREATED)
async def add_scrap_listing(
    # Form Data (Matches your frontend AdminDashboard.js)
    seller_name: str = Form(...),
    company_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    gst_number: str = Form(...),
    scrap_type: str = Form(...),
    quantity: float = Form(...),
    price_per_unit: float = Form(...),
    unit: str = Form(...),
    
    # Multiple Files
    images: List[UploadFile] = File(...),
    
    # DB Session
    db: Session = Depends(get_db)
):
    # A. Check for Duplicate GST (Business Rule)
    # Note: If GST is provided, check uniqueness. If not provided, skip.
    if gst_number:
        existing_listing = db.query(ScrapListing).filter(ScrapListing.gst_number == gst_number).first()
        if existing_listing:
            raise HTTPException(status_code=400, detail="A listing with this GST Number already exists.")

    # B. Create the Parent Listing
    new_listing = ScrapListing(
        seller_name=seller_name,
        company_name=company_name,
        email=email,
        phone=phone,
        gst_number=gst_number,
        scrap_type=scrap_type,
        quantity=quantity,
        price_per_unit=price_per_unit,
        unit=unit,
        is_admin_entry=True
    )
    
    db.add(new_listing)
    db.flush() # Flush to generate new_listing.id without committing transaction yet
    db.refresh(new_listing)

    # C. Handle Image Uploads
    uploaded_image_urls = []
    
    try:
        for img in images:
            # Generate Unique Filename: ID_UUID_OriginalName
            unique_filename = f"{new_listing.id}_{uuid.uuid4()}_{img.filename}"
            
            # Read file into memory for the Drive Uploader
            file_content = io.BytesIO(await img.read())
            
            # Upload to Google Drive
            public_url = upload_file_to_drive(file_content, unique_filename, img.content_type)
            
            # Create Child Image Record
            new_image = ScrapImage(
                scrap_listing_id=new_listing.id,
                seller_email=email,
                image_url=public_url,
                is_active=True
            )
            db.add(new_image)
            uploaded_image_urls.append(public_url)
            
        # If we reached here, all images uploaded successfully logic-wise
        db.commit()
        
        return {
            "message": "Scrap listing created successfully",
            "listing_id": new_listing.id,
            "images_count": len(uploaded_image_urls)
        }

    except Exception as e:
        db.rollback() # Undo the listing creation if image upload fails
        print(f"Upload Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload images: {str(e)}")


# --- 2. GET ALL LISTINGS (MARKETPLACE) ---
@router.get("/all")
def get_all_listings(
    scrap_type: Optional[str] = None, 
    skip: int = 0, 
    limit: int = 20, 
    db: Session = Depends(get_db)
):
    query = db.query(ScrapListing).options(joinedload(ScrapListing.images))
    
    if scrap_type and scrap_type != "All":
        query = query.filter(ScrapListing.scrap_type == scrap_type)
        
    listings = query.offset(skip).limit(limit).all()
    return listings


# --- 3. GET SINGLE LISTING DETAILS ---
@router.get("/{listing_id}")
def get_listing_detail(listing_id: int, db: Session = Depends(get_db)):
    listing = db.query(ScrapListing).options(joinedload(ScrapListing.images)).filter(ScrapListing.id == listing_id).first()
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
        
    return listing
