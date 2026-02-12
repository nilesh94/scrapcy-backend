"""
WebSocket Routes
Real-time bidding updates
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
import logging
import asyncio
from datetime import datetime

from app.database.connection import get_db
from app.e_auction.websockets.connection_manager import connection_manager
from app.e_auction.models import AuctionItem
from app.e_auction.schemas.bid import BidUpdateMessage
from app.e_auction.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/e-auction/ws", tags=["WebSocket"])


@router.websocket("/lots/{lot_id}/bids")
async def websocket_lot_bids(
    websocket: WebSocket,
    lot_id: int,
    user_id: int = Query(..., description="User ID for authentication"),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time bid updates on a specific lot
    
    Usage from frontend:
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/api/v1/e-auction/ws/lots/123/bids?user_id=1');
    
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
    
    # ==== RBAC: In production, verify user_id from JWT ====
    # For now, using query param for testing
    
    # Verify lot exists
    lot = db.query(AuctionItem).filter(AuctionItem.id == lot_id).first()
    if not lot:
        await websocket.close(code=1008, reason="Lot not found")
        return
    
    # Connect
    await connection_manager.connect(websocket, lot_id, user_id)
    
    # Send initial state
    try:
        initial_state = BidUpdateMessage(
            event_type="CONNECTED",
            auction_item_id=lot_id,
            current_highest_bid=lot.highest_bid_amount or lot.starting_bid_amount,
            total_bids=lot.total_bids_count or 0,
            unique_bidders=lot.unique_bidders_count or 0,
            time_remaining_seconds=int((lot.lot_end_time - datetime.now()).total_seconds()) if lot.lot_end_time else None,
            is_extended=False,
            extension_count=lot.extension_count or 0,
            is_current_user_winning=(lot.winner_user_id == user_id) if lot.winner_user_id else False
        )
        
        await connection_manager.send_personal_message(
            initial_state.dict(),
            websocket
        )
    
    except Exception as e:
        logger.error(f"Error sending initial state: {str(e)}")
    
    try:
        # Keep connection alive and handle incoming messages
        while True:
            # Wait for messages from client (if any)
            # In this implementation, client sends heartbeat responses
            data = await websocket.receive_text()
            
            # Process client messages (optional)
            # For now, just echo back as heartbeat response
            if data == "ping":
                await websocket.send_text("pong")
    
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, lot_id, user_id)
        logger.info(f"Client disconnected from lot {lot_id}")
    
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        connection_manager.disconnect(websocket, lot_id, user_id)


@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    user_id: int = Query(..., description="User ID for authentication")
):
    """
    WebSocket endpoint for real-time user notifications
    
    Usage:
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/api/v1/e-auction/ws/notifications?user_id=1');
    
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
    
    # ==== RBAC: In production, verify user_id from JWT ====
    
    await websocket.accept()
    
    # Send welcome message
    await websocket.send_json({
        "type": "connected",
        "user_id": user_id,
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
        logger.info(f"Notification websocket disconnected for user {user_id}")
    
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
            time_remaining = int((lot.lot_end_time - datetime.now()).total_seconds())
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
