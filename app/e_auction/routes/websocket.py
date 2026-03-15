"""
WebSocket Routes
Real-time bidding updates
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
import logging
import asyncio
from datetime import datetime, timezone

from app.database.connection import get_db
from app.e_auction.websockets.connection_manager import connection_manager
from app.e_auction.models import AuctionItem, Auction, AuctionParticipant
from app.e_auction.schemas.bid import BidUpdateMessage
from app.e_auction.config import settings
from app.e_auction.utils.enums import AuctionStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/e-auction/ws", tags=["WebSocket"])


@router.websocket("/lots/{lot_id}/bids")
@router.websocket("/lots/{lot_id}/bids/")
async def websocket_lot_bids(
    websocket: WebSocket,
    lot_id: int,
    user_id: Optional[int] = Query(None, description="User ID (optional if token is provided)"),
    token: Optional[str] = Query(None, description="JWT Access Token for authentication"),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time bid updates on a specific lot
    
    Authentication:
    Backend expects the JWT access token in the query parameter 'token'.
    Alternatively, for testing, 'user_id' can be passed directly.
    
    Usage from frontend (Example):
    ```javascript
    const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...';
    const lotId = 66100701; // Replace with dynamic lot ID from your logic
    const ws = new WebSocket(`ws://localhost:8000/api/v1/e-auction/ws/lots/${lotId}/bids?token=${token}`);
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Bid update:', data);
        
        if (data.event_type === 'BID_PLACED') {
            updateBidUI(data);
        } else if (data.event_type === 'AUCTION_EXTENDED') {
            showExtensionNotification(data);
        } else if (data.event_type === 'AUCTION_CLOSING') {
            showClosingWarning(data);
        }
    };
    ```
    
    Events sent:
    - BID_PLACED: When a new bid is placed
    - BID_OUTBID: When user gets outbid
    - AUCTION_EXTENDED: When auction time is extended
    - AUCTION_CLOSING: 60s warning before close
    - heartbeat: Keep-alive message
    """
    
    # CRITICAL: Always accept connection first in FastAPI to avoid 403 handshake errors.
    # If we perform logic before accept(), the handshake fails.
    await websocket.accept()
    
    # ==== RBAC: Authenticate User ====
    authenticated_user_id = user_id
    
    if token:
        try:
            # Dynamically import to avoid circular dependencies
            from app.utils import userUtils as utils
            from app.models.users import User
            
            # Verify JWT Token
            payload = utils.verify_token(token)
            if payload and payload.get("type") == "access":
                email = payload.get("sub")
                # Get numeric User ID from email
                user = db.query(User.id).filter(User.email == email).first()
                if user:
                    authenticated_user_id = user.id
                else:
                    await websocket.close(code=1008, reason="User not found for token")
                    return
            else:
                await websocket.close(code=1008, reason="Invalid or expired token")
                return
        except Exception as e:
            logger.error(f"WS Auth Error: {str(e)}")
            await websocket.close(code=1008, reason="Authentication failed")
            return
            
    if not authenticated_user_id:
        await websocket.close(code=1008, reason="Authentication required (token or user_id)")
        return

    # Verify lot exists in database
    lot = db.query(AuctionItem).filter(AuctionItem.id == lot_id).first()
    if not lot:
        await websocket.close(code=1008, reason="Lot not found")
        return

    # --- Eligibility & Status Validation - Start ---
    # 1. Verify Auction is LIVE
    auction = db.query(Auction).filter(Auction.id == lot.auction_id).first()
    if not auction or auction.status != AuctionStatus.LIVE:
        await websocket.close(code=1008, reason="Auction is not LIVE")
        return

    # 2. Verify User has paid EMD and is eligible to participate
    participation = db.query(AuctionParticipant).filter(
        AuctionParticipant.auction_id == lot.auction_id,
        AuctionParticipant.user_id == authenticated_user_id,
        AuctionParticipant.payment_status == 'SUCCESS'
    ).first()

    if not participation:
        await websocket.close(code=1008, reason="EMD Payment required for access")
        return
    # --- END ---
    
    # Connect (register connection in manager)
    await connection_manager.connect(
        websocket, 
        lot_id, 
        authenticated_user_id, 
        auction_id=lot.auction_id,
        already_accepted=True
    )
    
    # Send initial state to the newly connected client
    try:
        # SaaS FIX: Use UTC Standard for remaining time calculation
        now_utc = datetime.now(timezone.utc)
        lot_end_utc = lot.lot_end_time.replace(tzinfo=timezone.utc) if lot.lot_end_time and lot.lot_end_time.tzinfo is None else lot.lot_end_time
        
        initial_state = BidUpdateMessage(
            event_type="INITIAL_STATE",
            auction_item_id=lot_id,
            lot_id=lot_id,
            current_highest_bid=lot.highest_bid_amount or lot.starting_bid_amount,
            total_bids=lot.total_bids_count or 0,
            unique_bidders=lot.unique_bidders_count or 0,
            lot_end_time=lot_end_utc,
            time_remaining_seconds=int((lot_end_utc - now_utc).total_seconds()) if lot_end_utc else None,
            is_extended=False,
            extension_count=lot.extension_count or 0,
            winning_user_id=lot.winner_user_id,
            is_current_user_winning=(lot.winner_user_id == authenticated_user_id) if lot.winner_user_id else False
        )
        
        # FIXED: Using model_dump(mode='json') to ensure Decimal objects are serialized to float/string
        await connection_manager.send_personal_message(
            initial_state.model_dump(mode='json'),
            websocket
        )
    
    except Exception as e:
        logger.error(f"Error sending initial state: {str(e)}")
    
    try:
        # Keep connection alive and handle incoming messages (e.g., heartbeats)
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            
            # Simple heartbeat mechanism
            if data == "ping":
                await websocket.send_text("pong")
    
    except WebSocketDisconnect:
        # Clean up connection on disconnect
        connection_manager.disconnect(websocket, lot_id, authenticated_user_id)
        logger.info(f"Client disconnected from lot {lot_id}")
    
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        connection_manager.disconnect(websocket, lot_id, authenticated_user_id)


@router.websocket("/notifications")
@router.websocket("/notifications/")
async def websocket_notifications(
    websocket: WebSocket,
    user_id: Optional[int] = Query(None, description="User ID (optional if token is provided)"),
    token: Optional[str] = Query(None, description="JWT Access Token for authentication"),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time user notifications
    
    Authentication:
    Backend expects the JWT access token in the query parameter 'token'.
    Alternatively, for testing, 'user_id' can be passed directly.
    
    Usage:
    ```javascript
    const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...';
    const ws = new WebSocket(`ws://localhost:8000/api/v1/e-auction/ws/notifications?token=${token}`);
    
    ws.onmessage = (event) => {
        const notification = JSON.parse(event.data);
        showNotification(notification.title, notification.message);
    };
    ```
    
    Sends notifications for:
    - Outbid alerts
    - Auction won
    - Payment reminders
    - Auction starting soon
    """
    
    # CRITICAL: Always accept connection first in FastAPI to avoid 403 handshake errors
    await websocket.accept()
    
    # ==== RBAC: Authenticate User ====
    authenticated_user_id = user_id
    
    if token:
        try:
            from app.utils import userUtils as utils
            from app.models.users import User
            
            payload = utils.verify_token(token)
            if payload and payload.get("type") == "access":
                email = payload.get("sub")
                user = db.query(User.id).filter(User.email == email).first()
                if user:
                    authenticated_user_id = user.id
                else:
                    await websocket.close(code=1008, reason="User not found for token")
                    return
            else:
                await websocket.close(code=1008, reason="Invalid or expired token")
                return
        except Exception as e:
            logger.error(f"WS Auth Error: {str(e)}")
            await websocket.close(code=1008, reason="Authentication failed")
            return
            
    if not authenticated_user_id:
        await websocket.close(code=1008, reason="Authentication required (token or user_id)")
        return
    
    # Send welcome message
    await websocket.send_json({
        "type": "connected",
        "user_id": authenticated_user_id,
        "message": "Connected to notifications"
    })
    
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            
            # Echo heartbeat
            if data == "ping":
                await websocket.send_text("pong")
    
    except WebSocketDisconnect:
        logger.info(f"Notification websocket disconnected for user {authenticated_user_id}")
    
    except Exception as e:
        logger.error(f"Notification WebSocket error: {str(e)}")



# Helper function to broadcast bid updates (called from bidding service)
async def broadcast_bid_update(
    lot_id: int,
    bid_amount: float,
    total_bids: int,
    unique_bidders: int,
    winning_user_id: int,
    exclude_user_id: Optional[int] = None
):
    """
    Broadcast bid update to all watchers
    Call this from BiddingService after a bid is placed
    """
    from app.e_auction.models import AuctionItem
    from app.database.connection import SessionLocal
    
    db = SessionLocal()
    try:
        lot = db.query(AuctionItem).filter(AuctionItem.id == lot_id).first()
        if not lot:
            return
        
        # Calculate time remaining
        time_remaining = None
        if lot.lot_end_time:
            # SaaS FIX: Use UTC Standard for broadcast sync
            now_utc = datetime.now(timezone.utc)
            lot_end_utc = lot.lot_end_time.replace(tzinfo=timezone.utc) if lot.lot_end_time.tzinfo is None else lot.lot_end_time
            time_remaining = int((lot_end_utc - now_utc).total_seconds())
            time_remaining = max(0, time_remaining)  # Don't show negative
        
        # Create update message
        update = BidUpdateMessage(
            event_type="BID_PLACED",
            auction_item_id=lot_id,
            bid_amount=bid_amount,
            current_highest_bid=bid_amount,
            total_bids=total_bids,
            unique_bidders=unique_bidders,
            time_remaining_seconds=time_remaining,
            is_extended=False,
            extension_count=lot.extension_count or 0,
            winning_user_id=None,  # Don't reveal winner until closed
            is_current_user_winning=False  # Calculated per user
        )
        
        # Broadcast to all watchers
        await connection_manager.broadcast_to_lot(
            lot_id=lot_id,
            message=update,
            exclude_user_id=exclude_user_id
        )
        
        logger.info(f"📢 Broadcasted bid update for lot {lot_id}")
    
    finally:
        db.close()
