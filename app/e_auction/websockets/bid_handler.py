"""
Bid WebSocket Handler
Real-time bid update broadcasting
"""
from typing import Optional
from datetime import datetime
import logging

from app.e_auction.websockets.connection_manager import connection_manager
from app.e_auction.schemas.bid import BidUpdateMessage
from app.e_auction.models import AuctionItem, Bid
from app.database.connection import SessionLocal
from datetime import datetime

logger = logging.getLogger(__name__)


async def broadcast_bid_placed(
    lot_id: int,
    bid_id: int,
    bid_amount: float,
    bidder_user_id: int,
    total_bids: int,
    unique_bidders: int
):
    """
    Broadcast when a new bid is placed
    
    Args:
        lot_id: Auction item ID
        bid_id: ID of the bid just placed
        bid_amount: Amount of the new bid
        bidder_user_id: User who placed the bid
        total_bids: Total bid count for this lot
        unique_bidders: Number of unique bidders
    """
    db = SessionLocal()
    try:
        # Get lot details
        lot = db.query(AuctionItem).filter(AuctionItem.id == lot_id).first()
        if not lot:
            logger.error(f"Lot {lot_id} not found for bid broadcast")
            return
        
        # Calculate time remaining
        time_remaining = None
        if lot.lot_end_time:
            delta = lot.lot_end_time - datetime.now()
            time_remaining = max(0, int(delta.total_seconds()))
        
        # Create update message
        update_message = BidUpdateMessage(
            event_type="BID_PLACED",
            auction_item_id=lot_id,
            bid_id=bid_id,
            bid_amount=bid_amount,
            current_highest_bid=bid_amount,
            total_bids=total_bids,
            unique_bidders=unique_bidders,
            time_remaining_seconds=time_remaining,
            is_extended=False,
            extension_count=lot.extension_count or 0,
            winning_user_id=None,  # Don't reveal until closed
            is_current_user_winning=False  # Set per-user below
        )
        
        # Broadcast to all watchers
        await connection_manager.broadcast_to_lot(
            lot_id=lot_id,
            message=update_message,
            exclude_user_id=bidder_user_id  # Don't send to bidder
        )
        
        # Send personalized message to the bidder (you're winning!)
        # UPDATED: model_copy() for Pydantic V2
        bidder_message = update_message.model_copy()
        bidder_message.is_current_user_winning = True
        
        # UPDATED: model_dump() for Pydantic V2
        await connection_manager.broadcast_to_user(
            user_id=bidder_user_id,
            message=bidder_message.model_dump()
        )
        
        logger.info(f"📢 Broadcasted bid update for lot {lot_id}: {bid_amount}")
    
    except Exception as e:
        logger.error(f"❌ Error broadcasting bid: {str(e)}")
    finally:
        db.close()


async def broadcast_outbid(lot_id: int, outbid_user_id: int, new_highest_bid: float):
    """
    Send personalized outbid notification to specific user
    
    Args:
        lot_id: Auction item ID
        outbid_user_id: User who was outbid
        new_highest_bid: The new highest bid amount
    """
    db = SessionLocal()
    try:
        lot = db.query(AuctionItem).filter(AuctionItem.id == lot_id).first()
        if not lot:
            return
        
        # Calculate time remaining
        time_remaining = None
        if lot.lot_end_time:
            delta = lot.lot_end_time - datetime.now()
            time_remaining = max(0, int(delta.total_seconds()))
        
        # Create outbid message
        outbid_message = BidUpdateMessage(
            event_type="BID_OUTBID",
            auction_item_id=lot_id,
            current_highest_bid=new_highest_bid,
            total_bids=lot.total_bids_count or 0,
            unique_bidders=lot.unique_bidders_count or 0,
            time_remaining_seconds=time_remaining,
            is_current_user_winning=False
        )
        
        # Send only to outbid user
        # UPDATED: model_dump() for Pydantic V2
        await connection_manager.broadcast_to_user(
            user_id=outbid_user_id,
            message=outbid_message.model_dump()
        )
        
        logger.info(f"🔔 Sent outbid notification to user {outbid_user_id} for lot {lot_id}")
    
    except Exception as e:
        logger.error(f"❌ Error broadcasting outbid: {str(e)}")
    finally:
        db.close()


async def broadcast_extension(lot_id: int, extension_minutes: int):
    """
    Broadcast that auction time has been extended
    
    Args:
        lot_id: Auction item ID
        extension_minutes: How many minutes added
    """
    db = SessionLocal()
    try:
        lot = db.query(AuctionItem).filter(AuctionItem.id == lot_id).first()
        if not lot:
            return
        
        # Calculate new time remaining
        time_remaining = None
        if lot.lot_end_time:
            delta = lot.lot_end_time - datetime.now()
            time_remaining = max(0, int(delta.total_seconds()))
        
        # Create extension message
        extension_message = BidUpdateMessage(
            event_type="AUCTION_EXTENDED",
            auction_item_id=lot_id,
            current_highest_bid=lot.highest_bid_amount or lot.starting_bid_amount,
            total_bids=lot.total_bids_count or 0,
            unique_bidders=lot.unique_bidders_count or 0,
            time_remaining_seconds=time_remaining,
            is_extended=True,
            extension_count=lot.extension_count or 0
        )
        
        # Broadcast to all watchers
        await connection_manager.broadcast_to_lot(
            lot_id=lot_id,
            message=extension_message
        )
        
        logger.info(f"⏰ Broadcasted extension for lot {lot_id}: +{extension_minutes} minutes")
    
    except Exception as e:
        logger.error(f"❌ Error broadcasting extension: {str(e)}")
    finally:
        db.close()


async def broadcast_closing_warning(lot_id: int):
    """
    Broadcast warning that lot is closing soon (60 seconds)
    
    Args:
        lot_id: Auction item ID
    """
    db = SessionLocal()
    try:
        lot = db.query(AuctionItem).filter(AuctionItem.id == lot_id).first()
        if not lot:
            return
        
        # Calculate exact time remaining
        time_remaining = 60  # Default to 60 if can't calculate
        if lot.lot_end_time:
            delta = lot.lot_end_time - datetime.now()
            time_remaining = max(0, int(delta.total_seconds()))
        
        # Create closing warning
        warning_message = BidUpdateMessage(
            event_type="AUCTION_CLOSING",
            auction_item_id=lot_id,
            current_highest_bid=lot.highest_bid_amount or lot.starting_bid_amount,
            total_bids=lot.total_bids_count or 0,
            unique_bidders=lot.unique_bidders_count or 0,
            time_remaining_seconds=time_remaining
        )
        
        # Broadcast to all watchers
        await connection_manager.broadcast_to_lot(
            lot_id=lot_id,
            message=warning_message
        )
        
        logger.info(f"⚠️ Broadcasted closing warning for lot {lot_id}")
    
    except Exception as e:
        logger.error(f"❌ Error broadcasting closing warning: {str(e)}")
    finally:
        db.close()


async def broadcast_auction_ended(lot_id: int, winner_user_id: Optional[int] = None):
    """
    Broadcast that auction has ended
    
    Args:
        lot_id: Auction item ID
        winner_user_id: User who won (if any)
    """
    db = SessionLocal()
    try:
        lot = db.query(AuctionItem).filter(AuctionItem.id == lot_id).first()
        if not lot:
            return
        
        # Create ended message
        ended_message = BidUpdateMessage(
            event_type="AUCTION_ENDED",
            auction_item_id=lot_id,
            current_highest_bid=lot.final_sold_price or lot.highest_bid_amount,
            total_bids=lot.total_bids_count or 0,
            unique_bidders=lot.unique_bidders_count or 0,
            time_remaining_seconds=0,
            winning_user_id=winner_user_id  # Can reveal winner now
        )
        
        # Broadcast to all watchers
        await connection_manager.broadcast_to_lot(
            lot_id=lot_id,
            message=ended_message
        )
        
        logger.info(f"🏁 Broadcasted auction end for lot {lot_id}")
    
    except Exception as e:
        logger.error(f"❌ Error broadcasting auction end: {str(e)}")
    finally:
        db.close()


async def send_heartbeat_to_lot(lot_id: int):
    """
    Send heartbeat to all connections for a lot
    Keeps connections alive
    
    Args:
        lot_id: Auction item ID
    """
    try:
        await connection_manager.send_heartbeat(lot_id)
        logger.debug(f"💓 Sent heartbeat to lot {lot_id}")
    
    except Exception as e:
        logger.error(f"❌ Error sending heartbeat: {str(e)}")


async def get_lot_watchers_count(lot_id: int) -> int:
    """
    Get number of users watching a specific lot
    
    Args:
        lot_id: Auction item ID
        
    Returns:
        Number of unique users watching
    """
    try:
        return connection_manager.get_unique_users(lot_id)
    except Exception as e:
        logger.error(f"❌ Error getting watchers count: {str(e)}")
        return 0


async def disconnect_all_from_lot(lot_id: int):
    """
    Disconnect all users from a lot (when auction ends)
    
    Args:
        lot_id: Auction item ID
    """
    try:
        # Send final message
        await broadcast_auction_ended(lot_id)
        
        # Close all connections
        # (Connections will be cleaned up naturally when users disconnect)
        
        logger.info(f"🔌 Disconnected all users from lot {lot_id}")
    
    except Exception as e:
        logger.error(f"❌ Error disconnecting users: {str(e)}")

async def broadcast_auction_started(auction_id: int):
    """
    Notifies all connected bidders that the auction is now active.
    """
    message = {
        "event_type": "AUCTION_LIVE",
        "auction_id": auction_id,
        "server_time": datetime.utcnow().isoformat(),
        "message": "Bidding is now open! Good luck."
    }
    # connection_manager will iterate through all lots belonging to this auction
    await connection_manager.broadcast_to_auction(auction_id, message)
