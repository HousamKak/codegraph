"""WebSocket router for real-time graph updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for broadcasting updates."""

    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: List[WebSocket] = []
        logger.info("WebSocket ConnectionManager initialized")

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send a message to a specific client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message to client: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            logger.debug("No active WebSocket connections to broadcast to")
            return

        logger.info(f"Broadcasting message to {len(self.active_connections)} client(s): {message.get('type', 'unknown')}")

        # Keep track of dead connections
        dead_connections = []

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                dead_connections.append(connection)

        # Remove dead connections
        for connection in dead_connections:
            self.disconnect(connection)


# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time graph updates.

    Clients connect to this endpoint to receive:
    - File change notifications
    - Graph update deltas
    - Validation results
    - Reindexing progress
    """
    await manager.connect(websocket)

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connection established",
            "timestamp": None
        })

        # Keep connection alive and handle client messages
        while True:
            # Receive messages from client (for future bidirectional communication)
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                logger.info(f"Received message from client: {message}")

                # Handle client messages (ping, subscribe to specific files, etc.)
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from client: {data}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        manager.disconnect(websocket)


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance."""
    return manager
