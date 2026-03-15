"""
WebSocket Connection Manager
Real-time bidding updates for auctions
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set, Optional
import json
import logging
from datetime import datetime, timezone

from app.e_auction.schemas.bid import BidUpdateMessage

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates
    Supports multiple connections per user and per auction lot
    """
    
    def __init__(self):
        # Store connections: {lot_id: {user_id: [websocket, ...]}}
        self.active_connections: Dict[int, Dict[int, List[WebSocket]]] = {}
        # Track which lots a user is watching: {user_id: {lot_id, ...}}
        self.user_lots: Dict[int, Set[int]] = {}
        # Mapping lot_id to auction_id for targeted auction broadcasts: {lot_id: auction_id}
        self.lot_to_auction: Dict[int, int] = {}
    
    async def connect(self, websocket: WebSocket, lot_id: int, user_id: int, auction_id: Optional[int] = None, already_accepted: bool = False):
        """
        Accept and register a new WebSocket connection.
        
        Args:
            websocket: The active WebSocket connection object.
            lot_id: The ID of the auction lot the user is watching.
            user_id: The ID of the authenticated user.
            auction_id: The ID of the auction this lot belongs to.
            already_accepted: Boolean indicating if the handshake has already been accepted.
                             Required for FastAPI to avoid 403 Forbidden handshake errors.
        """
        if not already_accepted:
            # Complete the WebSocket handshake if not already done
            await websocket.accept()
        
        # Register the lot's auction if provided
        if auction_id is not None:
            self.lot_to_auction[lot_id] = auction_id
        
        # Initialize connection structures for this lot
        if lot_id not in self.active_connections:
            self.active_connections[lot_id] = {}
        
        if user_id not in self.active_connections[lot_id]:
            self.active_connections[lot_id][user_id] = []
        
        # Add connection
        self.active_connections[lot_id][user_id].append(websocket)
        
        # Track user's lots
        if user_id not in self.user_lots:
            self.user_lots[user_id] = set()
        self.user_lots[user_id].add(lot_id)
        
        logger.info(f"✅ WebSocket connected: user={user_id}, lot={lot_id}, auction={auction_id}")
        logger.info(f"📊 Active connections for lot {lot_id}: {len(self.active_connections[lot_id])}")
    
    def disconnect(self, websocket: WebSocket, lot_id: int, user_id: int):
        """Remove a WebSocket connection"""
        try:
            if lot_id in self.active_connections:
                if user_id in self.active_connections[lot_id]:
                    if websocket in self.active_connections[lot_id][user_id]:
                        self.active_connections[lot_id][user_id].remove(websocket)
                    
                    # Clean up empty lists
                    if not self.active_connections[lot_id][user_id]:
                        del self.active_connections[lot_id][user_id]
                
                # Clean up empty lots
                if not self.active_connections[lot_id]:
                    del self.active_connections[lot_id]
            
            # Clean up user lots tracking
            if user_id in self.user_lots:
                self.user_lots[user_id].discard(lot_id)
                if not self.user_lots[user_id]:
                    del self.user_lots[user_id]
            
            logger.info(f"🔌 WebSocket disconnected: user={user_id}, lot={lot_id}")
        
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket: {str(e)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to a specific connection"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {str(e)}")
    
    async def broadcast_to_lot(
        self,
        lot_id: int,
        message: BidUpdateMessage,
        exclude_user_id: Optional[int] = None
    ):
        """
        Broadcast message to all users watching a specific lot
        Optionally exclude a specific user (e.g., the bidder)
        """
        if lot_id not in self.active_connections:
            return
        
        # UPDATED: model_dump(mode='json') for Pydantic V2 to ensure JSON compatibility (e.g. Decimal -> float)
        message_dict = message.model_dump(mode='json')
        dead_connections = []
        
        # Iterate over a copy of the dictionary items to avoid RuntimeError during cleanup
        for user_id, connections in list(self.active_connections[lot_id].items()):
            # Skip excluded user
            if exclude_user_id and user_id == exclude_user_id:
                continue
            
            for websocket in connections:
                try:
                    await websocket.send_json(message_dict)
                except Exception as e:
                    logger.error(f"Error broadcasting to lot {lot_id}, user {user_id}: {str(e)}")
                    dead_connections.append((lot_id, user_id, websocket))
        
        # Clean up dead connections
        for lot_id, user_id, ws in dead_connections:
            self.disconnect(ws, lot_id, user_id)

    async def broadcast_to_auction(self, auction_id: int, message: dict):
        """
        Broadcast message to all users watching any lot in a specific auction.
        Used for operational status changes like AUCTION_LIVE or AUCTION_CLOSED.
        """
        # Find all lots that belong to this specific auction
        target_lot_ids = [
            lot_id for lot_id, aid in self.lot_to_auction.items()
            if aid == auction_id and lot_id in self.active_connections
        ]
        
        for lot_id in target_lot_ids:
            dead_connections = []
            for user_id, connections in list(self.active_connections[lot_id].items()):
                for websocket in connections:
                    try:
                        await websocket.send_json(message)
                    except Exception as e:
                        logger.error(f"Error broadcasting auction update to lot {lot_id}: {str(e)}")
                        dead_connections.append((lot_id, user_id, websocket))
            
            # Clean up dead connections discovered during broadcast
            for lid, uid, ws in dead_connections:
                self.disconnect(ws, lid, uid)
    
    async def broadcast_to_user(self, user_id: int, message: dict, lot_id: Optional[int] = None):
        """
        Send message to all connections of a specific user.
        If lot_id is provided, only sends to that specific lot's connection.
        """
        if user_id not in self.user_lots:
            return
        
        dead_connections = []
        
        # If lot_id is provided, only target that lot. Otherwise, target all lots the user is watching.
        target_lot_ids = [lot_id] if lot_id is not None else list(self.user_lots[user_id])
        
        for lid in target_lot_ids:
            if lid in self.active_connections and user_id in self.active_connections[lid]:
                for websocket in self.active_connections[lid][user_id]:
                    try:
                        await websocket.send_json(message)
                    except Exception as e:
                        logger.error(f"Error broadcasting to user {user_id} on lot {lid}: {str(e)}")
                        dead_connections.append((lid, user_id, websocket))
        
        # Clean up dead connections
        for lid, uid, ws in dead_connections:
            self.disconnect(ws, lid, uid)
    
    async def send_heartbeat(self, lot_id: int):
        """Send heartbeat to all connections for a lot"""
        if lot_id not in self.active_connections:
            return
        
        # SaaS FIX: Use UTC-aware timestamp for heartbeats
        # This allows the client to calculate their local time offset from the server
        heartbeat = {
            "type": "heartbeat",
            "server_time_utc": datetime.now(timezone.utc).isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        dead_connections = []
        
        for user_id, connections in list(self.active_connections[lot_id].items()):
            for websocket in connections:
                try:
                    await websocket.send_json(heartbeat)
                except Exception as e:
                    dead_connections.append((lot_id, user_id, websocket))
        
        # Clean up dead connections
        for lot_id, user_id, ws in dead_connections:
            self.disconnect(ws, lot_id, user_id)
    
    def get_connection_count(self, lot_id: int) -> int:
        """Get total number of active connections for a lot"""
        if lot_id not in self.active_connections:
            return 0
        
        total = 0
        for user_connections in self.active_connections[lot_id].values():
            total += len(user_connections)
        return total
    
    def get_unique_users(self, lot_id: int) -> int:
        """Get number of unique users watching a lot"""
        if lot_id not in self.active_connections:
            return 0
        return len(self.active_connections[lot_id])


# Global connection manager instance
connection_manager = ConnectionManager()
