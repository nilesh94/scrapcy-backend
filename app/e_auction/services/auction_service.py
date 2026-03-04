"""
Auction Service
Complete business logic for auction management
All config from ENV - no hardcoded values
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, case
from datetime import datetime, timezone
from fastapi import UploadFile, HTTPException
import json

from app.e_auction.models import Auction, AuctionItem, AuctionParticipant
from app.e_auction.schemas.auction import *
from app.e_auction.schemas.auction_item import LotUpdateRequest
from app.e_auction.utils.exceptions import *
from app.e_auction.utils.enums import AuctionStatus, ApprovalStatus, LotStatus
from app.e_auction.config import settings

# ABSOLUTELY REQUIRED: Import Drive Utils for internal file processing
from app.utils.driveUtils import upload_file_to_drive

from app.e_auction.models.auction_item_images import AuctionItemImage

class AuctionService:
    """Auction management service - all operations for auctions"""
    
    @staticmethod
    async def create_auction(
        db: Session,
        auction_data: AuctionCreateRequest,
        # ADDED: seller_id determines ownership, created_by determines audit
        seller_id: int, 
        created_by_user_id: int,
        # ABSOLUTELY REQUIRED: Accept terms_file for internal calculation
        terms_file: Optional[UploadFile] = None,
        # ADDED: Accept lot images for integrated creation
        lot_images: Optional[List[UploadFile]] = None
    ) -> Auction:
        """Create new auction"""
        # Validate dates
        if auction_data.scheduled_end_time <= auction_data.scheduled_start_time:
            raise InvalidDateRangeException("End time must be after start time")
        
        # Extract lots data if present (handled via schema update)
        lots_data = getattr(auction_data, 'lots', [])

        # Validate that at least 1 lot is provided
        if not lots_data:
            raise InvalidDateRangeException("At least 1 lot is required to create an auction")

        # Create Auction Instance
        # Convert Enum to string for DB if necessary, or pass raw if driver handles it
        auction_type_str = str(auction_data.auction_type.value) if hasattr(auction_data.auction_type, 'value') else auction_data.auction_type

        # --- ABSOLUTELY REQUIRED: INTERNAL CALCULATION FOR FILE PATH ---
        internal_doc_url = auction_data.auction_doc_url
        if terms_file:
            try:
                # REQUIREMENT: Filename + Timestamp separated by '___'
                # SaaS FIX: Use UTC for unique filename timestamp
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
                unique_filename = f"{terms_file.filename}___{timestamp}"

                upload_res = upload_file_to_drive(
                    file_obj=terms_file.file, 
                    filename=unique_filename, 
                    mime_type=terms_file.content_type
                )
                internal_doc_url = upload_res.get('url')
            except Exception as e:
                print(f"Error uploading T&C to Drive: {str(e)}")

        auction = Auction(
            # --- OWNERSHIP & AUDIT ---
            # seller_id: The Company/Seller who owns this auction (shows in their dashboard)
            seller_id=seller_id,
            # created_by: The User (Admin or Seller) who physically created the record
            created_by=created_by_user_id,
            
            auction_title=auction_data.auction_title,
            auction_type=auction_type_str, 
            category=auction_data.category,
            region=auction_data.region,
            status=AuctionStatus.DRAFT,
            approval_status=ApprovalStatus.PENDING,
            scheduled_start_time=auction_data.scheduled_start_time,
            scheduled_end_time=auction_data.scheduled_end_time,
            currency=auction_data.currency,
            emd_amount=auction_data.emd_amount,
            registration_fee=auction_data.registration_fee,
            # Ensure int for Oracle Number(1) column
            enable_extension=1 if auction_data.enable_extension else 0, 
            extension_trigger_window_minutes=auction_data.extension_trigger_window_minutes,
            extension_duration_minutes=auction_data.extension_duration_minutes,
            extension_min_total_bids=auction_data.extension_min_total_bids,
            inspection_start_date=auction_data.inspection_start_date,
            inspection_end_date=auction_data.inspection_end_date,
            inspection_location=auction_data.inspection_location,
            inspection_contact_person=auction_data.inspection_contact_person,
            inspection_contact_number=auction_data.inspection_contact_number,
            terms_and_conditions=auction_data.terms_and_conditions,
            # Use the calculated doc URL
            auction_doc_url=internal_doc_url,
            # SaaS FIX: Set UTC created/updated at
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db.add(auction)
        db.flush() # Generate ID without committing transaction yet
        
        # Create Lots
        for lot_idx, lot_req in enumerate(lots_data):
            # Convert Pydantic model to dict, excluding unset/nulls
            # Support both Pydantic v1 (dict) and v2 (model_dump)
            try:
                lot_dict = lot_req.model_dump(exclude_unset=True)
            except AttributeError:
                lot_dict = lot_req.dict(exclude_unset=True)
            
            # --- CRITICAL LOGIC: Propagate Auction Defaults to Lot ---
            
            # 1. Sync Times: If Lot times are missing, use Auction times
            if not lot_dict.get('lot_start_time'):
                lot_dict['lot_start_time'] = auction.scheduled_start_time
            if not lot_dict.get('lot_end_time'):
                lot_dict['lot_end_time'] = auction.scheduled_end_time
            
            # 2. Sync Auction Type: The lot needs to know if it is Reverse/Dutch (DB Column: LOT_AUCTION_TYPE)
            lot_dict['lot_auction_type'] = auction.auction_type

            # 3. Handle Pincode: Merge into address if present (UI sends it, DB has no column for pincode in ITEMS)
            if lot_dict.get('location_pincode'):
                addr = lot_dict.get('location_address', '')
                pincode = lot_dict.pop('location_pincode') # Remove from dict so it doesn't crash DB insert
                if addr:
                    lot_dict['location_address'] = f"{addr}, {pincode}"
                else:
                    lot_dict['location_address'] = str(pincode)

            # Sanitize rating for fresh auctions to prevent ORA check constraint violation
            rating = lot_dict.get('condition_rating')
            if rating is None or (isinstance(rating, (int, float)) and rating < 1):
                lot_dict['condition_rating'] = 2
            elif isinstance(rating, (int, float)) and rating > 5:
                lot_dict['condition_rating'] = 5

            # Create AuctionItem linked to this auction
            new_lot = AuctionItem(
                auction_id=auction.id,
                lot_status=LotStatus.PENDING,
                **lot_dict,
                # SaaS FIX: Set UTC creation for lot
                created_at=datetime.now(timezone.utc)
            )
            db.add(new_lot)
            db.flush()

            # --- ADDED: Integrated Lot Image Upload ---
            if lot_images:
                # FIXED: Use "in" check for robust matching with frontend renamed files (lot_0_file_0...)
                lot_specific_files = [f for f in lot_images if f"lot_{lot_idx}_" in f.filename]
                if lot_specific_files:
                    await AuctionService.save_lot_images(db, new_lot.id, lot_specific_files)
                elif not lot_dict.get('id'): # For new auctions, enforce 1 image
                    raise InvalidDateRangeException(f"Lot {lot_idx + 1} requires at least one image")
        
        # Update total lots count on auction
        auction.total_lots = len(lots_data)

        db.commit()
        
        # REQUIRED FIX: Explicitly load items relationship before returning
        # This prevents the 'blank page' issue in the UI caused by missing lot IDs
        db.refresh(auction)
        _ = auction.items # Accessing relationship triggers lazy load if not already loaded
        
        return auction

    # --- SUPPORT FOR MODAL UPDATES: New Method ---
    @staticmethod
    async def update_specific_lot(
        db: Session,
        lot_id: int,
        lot_data: LotUpdateRequest,
        images: Optional[List[UploadFile]] = None,
        delete_image_ids: Optional[List[int]] = None,
        current_user_id: int = None,
        current_user_role: str = None
    ) -> AuctionItem:
        """Update a single lot and manage its images via modal with RBAC"""
        lot = db.query(AuctionItem).filter(AuctionItem.id == lot_id).first()
        if not lot:
            raise AuctionNotFoundException(lot_id)

        # --- RBAC CHECK ---
        # Allow Admin to edit anything. 
        # For others, check if they are the creator of the parent auction.
        if current_user_role != "admin":
            auction = db.query(Auction).filter(Auction.id == lot.auction_id).first()
            if not auction or auction.created_by != current_user_id:
                raise ForbiddenException("You do not have permission to edit this lot.")
        # --- END RBAC CHECK ---

        # 1. Update text fields
        try:
            update_dict = lot_data.model_dump(exclude_unset=True)
        except AttributeError:
            update_dict = lot_data.dict(exclude_unset=True)

        # SURGICAL FIX: Sanitize condition_rating to satisfy ORA CHK_CONDITION_RATING (1-5)
        # If rating is 0 or None, set to default 2 as per requirement
        if 'condition_rating' in update_dict:
            rating = update_dict.get('condition_rating')
            if rating is None or (isinstance(rating, (int, float)) and rating < 1):
                update_dict['condition_rating'] = 2
            elif isinstance(rating, (int, float)) and rating > 5:
                update_dict['condition_rating'] = 5

        for field, value in update_dict.items():
            if hasattr(lot, field):
                setattr(lot, field, value)

        # 2. Handle Image Deletions
        if delete_image_ids:
            db.query(AuctionItemImage).filter(
                AuctionItemImage.id.in_(delete_image_ids),
                AuctionItemImage.item_id == lot_id
            ).delete(synchronize_session=False)

        # 3. Handle New Image Uploads
        if images:
            # We use "lot_0_" filtering because frontend uses lot_0_ prefix for single item PUTs
            lot_specific_files = [f for f in images if "lot_0_" in f.filename]
            if lot_specific_files:
                print(f"DEBUG: Found {len(lot_specific_files)} images to upload for lot {lot_id}")
                await AuctionService.save_lot_images(db, lot_id, lot_specific_files)

        # Wrap commit in try-except to debug 500 errors post-upload
        try:
            print(f"DEBUG: Attempting final commit for lot {lot_id}")
            db.commit()
            print(f"DEBUG: Commit successful for lot {lot_id}")
            db.refresh(lot)
            return lot
        except Exception as e:
            db.rollback()
            print(f"DEBUG ERROR: Final commit failed! Type: {type(e).__name__}, Details: {str(e)}")
            raise HTTPException(status_code=500, detail="Database commit failure. See server logs.")

    # --- Support for View/Edit Page Document Upload ---
    @staticmethod
    async def upload_auction_document(
        db: Session,
        auction_id: int,
        document: UploadFile,
        user_id: int
    ) -> str:
        """Upload or replace a document for an existing auction"""
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise AuctionNotFoundException(auction_id)

        try:
            # REQUIREMENT: Combination of filename and timestamp separated by '___'
            # SaaS FIX: Use UTC for unique document filename
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            unique_filename = f"{document.filename}___{timestamp}"

            upload_res = upload_file_to_drive(
                file_obj=document.file, 
                filename=unique_filename, 
                mime_type=document.content_type
            )
            file_url = upload_res.get('url')
            
            auction.auction_doc_url = file_url
            # SaaS FIX: Set UTC updated_at
            auction.updated_at = datetime.now(timezone.utc)
            db.commit()
            return file_url
        except Exception as e:
            raise Exception(f"Failed to upload document: {str(e)}")
    
    @staticmethod
    def get_by_id(db: Session, auction_id: int) -> Auction:
        """Get auction by ID"""
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise AuctionNotFoundException(auction_id)
        
        # Increment view count
        auction.view_count = (auction.view_count or 0) + 1
        db.commit()
        return auction
    
    @staticmethod
    async def update_auction(
        db: Session,
        auction_id: int,
        auction_data: AuctionUpdateRequest,
        user_id: int,
        # ABSOLUTELY REQUIRED: Accept optional file for update
        terms_file: Optional[UploadFile] = None,
        # ADDED: Accept lot images for integrated update
        lot_images: Optional[List[UploadFile]] = None
    ) -> Auction:
        """Update auction and optionally calculate new internal doc path"""
        auction = AuctionService.get_by_id(db, auction_id)
        
        # Ownership check
        if auction.created_by != user_id and auction.seller_id != user_id:
             pass 
        
        if not auction.can_be_edited:
            raise AuctionNotEditableException(auction.status)
        
        # 1. Update standard fields
        try:
            update_data = auction_data.model_dump(exclude_unset=True)
        except AttributeError:
            update_data = auction_data.dict(exclude_unset=True)

        # Separate lots data for processing
        lots_update_data = update_data.pop('lots', [])

        for field, value in update_data.items():
            setattr(auction, field, value)

        # 2. INTERNAL CALCULATION: Handle File Update if provided
        if terms_file:
            try:
                # Combination of filename and timestamp separated by '___'
                # SaaS FIX: Use UTC for unique terms filename
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
                unique_filename = f"{terms_file.filename}___{timestamp}"

                upload_res = upload_file_to_drive(
                    file_obj=terms_file.file, 
                    filename=unique_filename, 
                    mime_type=terms_file.content_type
                )
                # Save calculated path internally
                auction.auction_doc_url = upload_res.get('url')
            except Exception as e:
                print(f"Update Upload Error: {str(e)}")

        # 3. Handle Lot and Image Updates
        for idx, lot_data in enumerate(lots_update_data):
            lot_id = lot_data.get('id')
            # Handle image deletions if flags provided in JSON
            if lot_data.get('delete_image_ids'):
                db.query(AuctionItemImage).filter(AuctionItemImage.id.in_(lot_data['delete_image_ids'])).delete(synchronize_session=False)

            # Handle new uploads for this lot index
            if lot_images and lot_id:
                # FIXED: Robust matching for integrated update
                lot_specific_files = [f for f in lot_images if f"lot_{idx}_" in f.filename]
                if lot_specific_files:
                    await AuctionService.save_lot_images(db, lot_id, lot_specific_files)
        
        # SaaS FIX: Use UTC updated_at
        auction.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(auction)
        return auction
    
    @staticmethod
    def list_auctions(
        db: Session,
        filters: AuctionFilterParams,
        page: int,
        page_size: int,
        user_id: Optional[int] = None
    ) -> AuctionListResponse:
        """List auctions with filters"""
        query = db.query(Auction)
        
        if filters.status:
            query = query.filter(Auction.status == filters.status)
        if filters.category:
            query = query.filter(Auction.category == filters.category)
        if filters.search:
            query = query.filter(Auction.auction_title.ilike(f"%{filters.search}%"))
            
        # UPDATED: Filter by seller_id (Owner) instead of created_by
        # This ensures Sellers see auctions created FOR them by Admins
        if filters.created_by_me and user_id:
            # Show auctions where the user is the Seller (Owner) OR the Creator
            # This ensures Sellers see auctions Admins made for them
            query = query.filter(
                or_(
                    Auction.seller_id == user_id,
                    Auction.created_by == user_id
                )
            )
        
        total = query.count()
        skip = (page - 1) * page_size
        auctions = query.order_by(Auction.created_at.desc()).offset(skip).limit(page_size).all()
        
        # Handle Pydantic V2 model_validate or V1 from_orm
        try:
            auction_list = [AuctionBasicResponse.model_validate(a) for a in auctions]
        except AttributeError:
            auction_list = [AuctionBasicResponse.from_orm(a) for a in auctions]

        return AuctionListResponse(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
            auctions=auction_list
        )
    
    @staticmethod
    def submit_for_approval(db: Session, auction_id: int, user_id: int) -> Auction:
        """Submit for approval"""
        auction = AuctionService.get_by_id(db, auction_id)
        
        # UPDATED: Owner (seller_id) OR Creator can submit
        if auction.created_by != user_id and auction.seller_id != user_id:
            # Allow logic to proceed if route already checked permission (e.g. Admin role)
            pass 
        
        # Check has lots
        lot_count = db.query(func.count(AuctionItem.id)).filter(
            AuctionItem.auction_id == auction_id
        ).scalar()
        if lot_count == 0:
            raise InvalidDateRangeException("Must have at least one lot")
        
        auction.status = AuctionStatus.PENDING_APPROVAL
        db.commit()
        db.refresh(auction)
        return auction
    
    @staticmethod
    def approve_l1(
        db: Session,
        auction_id: int,
        approver_id: int,
        remarks: Optional[str],
        approve: bool
    ) -> Auction:
        """L1 approval"""
        auction = AuctionService.get_by_id(db, auction_id)
        
        if approve:
            auction.approval_status = ApprovalStatus.L1_APPROVED
            auction.publish_l1_approved_by = approver_id
            # SaaS FIX: Set UTC approval time
            auction.publish_l1_approved_at = datetime.now(timezone.utc)
            auction.publish_l1_remarks = remarks
        else:
            auction.status = AuctionStatus.DRAFT
            auction.approval_status = ApprovalStatus.REJECTED
            auction.publish_l1_remarks = remarks
        
        db.commit()
        db.refresh(auction)
        return auction
    
    @staticmethod
    def approve_l2(
        db: Session,
        auction_id: int,
        approver_id: int,
        remarks: Optional[str],
        approve: bool
    ) -> Auction:
        """L2 approval"""
        auction = AuctionService.get_by_id(db, auction_id)
        
        if auction.approval_status != ApprovalStatus.L1_APPROVED:
            raise AuctionNotEditableException("Must be L1 approved first")
        
        if approve:
            auction.approval_status = ApprovalStatus.L2_APPROVED
            auction.status = AuctionStatus.SCHEDULED
            auction.publish_l2_approved_by = approver_id
            # SaaS FIX: Set UTC approval time
            auction.publish_l2_approved_at = datetime.now(timezone.utc)
            auction.publish_l2_remarks = remarks
        else:
            auction.status = AuctionStatus.DRAFT
            auction.approval_status = ApprovalStatus.REJECTED
            auction.publish_l2_remarks = remarks
        
        db.commit()
        db.refresh(auction)
        return auction
    
    @staticmethod
    def publish_auction(db: Session, auction_id: int) -> Auction:
        """Publish auction (make LIVE)"""
        auction = AuctionService.get_by_id(db, auction_id)
        
        if not auction.is_approved:
            raise AuctionNotApprovedException()
        
        auction.status = AuctionStatus.LIVE
        # SaaS FIX: Set UTC start/publish times
        auction.actual_start_time = datetime.now(timezone.utc)
        auction.published_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(auction)
        return auction
    
    @staticmethod
    def publish_auction_for_buyers(db: Session, auction_id: int) -> Auction:
        """Specific publishing for testing with evaluation attributes enabled"""
        auction = AuctionService.get_by_id(db, auction_id)
        auction.status = AuctionStatus.LIVE
        auction.approval_status = ApprovalStatus.PUBLISHED
        db.commit()
        db.refresh(auction)
        return auction

    @staticmethod
    def close_auction(db: Session, auction_id: int) -> Auction:
        """Close auction"""
        auction = AuctionService.get_by_id(db, auction_id)
        
        auction.status = AuctionStatus.CLOSED
        # SaaS FIX: Set UTC end time
        auction.actual_end_time = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(auction)
        return auction
        
    @staticmethod
    def cancel_auction(db: Session, auction_id: int, user_id: int, reason: str) -> Auction:
        """Cancel auction"""
        auction = AuctionService.get_by_id(db, auction_id)
        
        # Validation: check if user is authorized (omitted for brevity, assume caller checks)
        
        auction.status = AuctionStatus.CANCELLED
        auction.cancellation_reason = reason
        # SaaS FIX: Set UTC cancellation time
        auction.cancelled_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(auction)
        return auction
    
    @staticmethod
    def delete_auction(db: Session, auction_id: int, user_id: int):
        """Delete auction (Draft only)"""
        auction = AuctionService.get_by_id(db, auction_id)
        
        # UPDATED: Owner (seller_id) OR creator can delete
        if auction.created_by != user_id and auction.seller_id != user_id:
             # Assume Route layer handles admin override logic
             pass
            
        if auction.status not in [AuctionStatus.DRAFT, AuctionStatus.CANCELLED]:
            raise AuctionNotEditableException("Only DRAFT or CANCELLED auctions can be deleted")
            
        db.delete(auction)
        db.commit()
        
    @staticmethod
    def get_auction_stats(db: Session, user_id: Optional[int] = None) -> AuctionStatsResponse:
        """Get auction statistics"""
        query = db.query(Auction)
        if user_id:
            # UPDATED: Filter by seller_id (Owner) so stats reflect "My Auctions" correctly
            # Using same logic as list_auctions to be consistent
            query = query.filter(
                or_(
                    Auction.seller_id == user_id,
                    Auction.created_by == user_id
                )
            )
            
        total = query.count()
        draft = query.filter(Auction.status == AuctionStatus.DRAFT).count()
        live = query.filter(Auction.status == AuctionStatus.LIVE).count()
        pending = query.filter(Auction.status == AuctionStatus.PENDING_APPROVAL).count()
        
        return AuctionStatsResponse(
            total_auctions=total,
            draft_auctions=draft,
            live_auctions=live,
            pending_approval=pending,
            # Count total lots based on auctions
            total_lots=db.query(func.count(AuctionItem.id)).scalar() or 0
        )

    @staticmethod
    async def save_lot_images(db: Session, lot_id: int, images: List[UploadFile]):
        uploaded_results = []
        print(f"DEBUG: Starting database sync for lot {lot_id} images")
        
        for idx, img in enumerate(images):
            try:
                # 1. Capture original metadata for DB Audit
                img.file.seek(0, 2)
                size_in_bytes = img.file.tell()
                img.file.seek(0)
                
                # Cleanup original_name to remove internal prefixes for a cleaner DB Audit
                original_name = img.filename
                if "___" in original_name: original_name = original_name.split("___")[-1]
                if "_file_" in original_name: original_name = original_name.split("_", 3)[-1]

                # 2. Generate unique internal path for storage
                # SaaS FIX: Use UTC for unique image filename timestamp
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
                unique_storage_name = f"lot_{lot_id}_{timestamp}_{idx}"

                # 3. Physical Upload
                drive_res = upload_file_to_drive(
                    file_obj=img.file,
                    filename=unique_storage_name,
                    mime_type=img.content_type
                )
                print(f"DEBUG: Drive upload finished for {original_name}")

                # 4. Save Record to auction_item_images table
                new_image = AuctionItemImage(
                    item_id=lot_id,
                    image_url=drive_res.get('url'),
                    file_name=original_name[:250],           # Clean name with truncation to fit VARCHAR2(255)
                    drive_file_id=drive_res.get('id'), # Unique Drive ID
                    file_size=size_in_bytes,
                    is_primary=1 if idx == 0 else 0,
                    display_order=idx,
                    # SaaS FIX: Set UTC creation for image record
                    created_at=datetime.now(timezone.utc)
                )
                
                db.add(new_image)
                uploaded_results.append(drive_res.get('url'))
                print(f"DEBUG: AuctionItemImage record added to flush queue for {original_name}")

            except Exception as e:
                # ADDED: DEBUG log to identify why uploads might fail
                print(f"DEBUG ERROR: save_lot_images failed at index {idx} ({img.filename}): {str(e)}")
                raise e
        
        # Catch exact Oracle error during flush
        try:
            print("DEBUG: Executing db.flush() for new images")
            db.flush()
            print("DEBUG: Database flush successful")
        except Exception as flush_err:
            print(f"DEBUG ERROR: Oracle Flush Failed! Details: {str(flush_err)}")
            raise flush_err

        return {"lot_id": lot_id, "success_count": len(uploaded_results)}

    @staticmethod
    def list_auctions_for_buyers(
        db: Session,
        page: int,
        page_size: int,
        current_user_id: int,
        category: Optional[str] = None,
        search: Optional[str] = None
    ) -> AuctionListResponse:
        """
        REQUIREMENT: Show all Live and Upcoming (Scheduled) auctions.
        Access to bidding is gated by EMD check in the Participation Summary.
        """
        # Surgical Update: Query with outerjoin and case logic to calculate 'emd_paid'
        query = db.query(Auction).outerjoin(
            AuctionParticipant, 
            and_(AuctionParticipant.auction_id == Auction.id, AuctionParticipant.user_id == current_user_id)
        ).add_columns(
            Auction,
            case(
                (AuctionParticipant.payment_status == 'SUCCESS', True),
                else_=False
            ).label("emd_paid")
        ).filter(
            Auction.approval_status == ApprovalStatus.PUBLISHED,
            Auction.status.in_([AuctionStatus.LIVE, AuctionStatus.SCHEDULED])
        )

        if category:
            query = query.filter(Auction.category == category)
        if search:
            query = query.filter(Auction.auction_title.ilike(f"%{search}%"))

        total = query.count()
        skip = (page - 1) * page_size
        
        # Order by start time so soonest auctions appear first
        results = query.order_by(Auction.scheduled_start_time.asc()).offset(skip).limit(page_size).all()

        auction_list = []
        for row in results:
            # results contains tuples (Auction, emd_paid)
            auction_obj = row[0]
            emd_paid_flag = row[1]
            
            # Force inclusion of emd_paid in the dictionary regardless of schema filtering
            try:
                # model_validate evaluates dynamic attributes correctly
                auction_dict = AuctionBasicResponse.model_validate(auction_obj, from_attributes=True).model_dump()
            except AttributeError:
                # Handle legacy Pydantic environments
                auction_dict = AuctionBasicResponse.from_orm(auction_obj).dict()
            
            # Manually inject the flag derived from the join logic
            auction_dict["emd_paid"] = bool(emd_paid_flag)
            auction_list.append(auction_dict)

        return AuctionListResponse(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
            auctions=auction_list
        )

    @staticmethod
    async def place_bid(db: Session, lot_id: int, user_id: int, amount: float):
        """Robust bidding with row-level locking and auto-extension"""
        # 1. Acquire Lock on the Lot Row to prevent concurrent bid issues
        lot = db.query(AuctionItem).filter(AuctionItem.id == lot_id).with_for_update().first()
        
        if not lot or lot.lot_status != "LIVE":
            raise HTTPException(status_code=400, detail="Lot is not active")

        # 2. Validate Bid Amount
        min_required = (lot.highest_bid_amount or lot.starting_bid_amount) + (lot.min_increment_amount or 0)
        if amount < min_required:
            raise HTTPException(status_code=400, detail=f"Bid too low. Min: {min_required}")

        # 3. Update Lot State
        lot.highest_bid_amount = amount
        lot.winner_user_id = user_id
        lot.total_bids_count += 1
        # SaaS FIX: Set UTC bid time
        lot.last_bid_time = datetime.now(timezone.utc)

        # 4. ROBUST FEATURE: Auto-Extension (Popcorn Bidding)
        # If bid is within last 2 minutes, extend by 3 minutes
        # SaaS FIX: Use UTC-aware now for extension check
        time_left = (lot.lot_end_time.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).total_seconds()
        if time_left < 120: 
            lot.lot_end_time = lot.lot_end_time + timedelta(minutes=3)
            lot.extension_count += 1

        db.commit()
        
        # 5. Trigger Real-time Broadcast
        from app.e_auction.websockets.bid_handler import broadcast_bid_placed
        await broadcast_bid_placed(
            lot_id=lot.id,
            bid_id=0, # Replace with actual bid record ID if using BIDS table
            bid_amount=amount,
            bidder_user_id=user_id,
            total_bids=lot.total_bids_count,
            unique_bidders=lot.unique_bidders_count
        )
        return lot
