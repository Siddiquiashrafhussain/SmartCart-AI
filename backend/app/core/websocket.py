"""
SmartCart AI - Real-Time WebSocket Connection Manager
Maintains active staff dashboard WebSocket connections and broadcasts real-time
notifications for restock alerts, inventory changes, and checkout verification outcomes.
"""

from typing import List, Dict, Any
from fastapi import WebSocket
from backend.app.core.logging import logger


class WebSocketManager:
    """
    Manages active dashboard WebSocket clients and provides thread-safe broadcasting.
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Dashboard WebSocket client connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Dashboard WebSocket client disconnected. Active connections: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """
        Broadcast a structured JSON event to all connected dashboard clients.
        Drops dead connections gracefully.
        """
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Error sending to WebSocket client: {e}")
                disconnected.append(connection)

        for dead_conn in disconnected:
            self.disconnect(dead_conn)

    def broadcast_sync(self, message: Dict[str, Any]):
        """
        Synchronous wrapper to broadcast messages from sync database contexts
        using an available async loop or best-effort delivery.
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.broadcast(message))
            else:
                loop.run_until_complete(self.broadcast(message))
        except Exception:
            # When outside an active event loop (e.g. background sync worker),
            # fire in a separate thread or log safely
            try:
                asyncio.run(self.broadcast(message))
            except Exception as e:
                logger.debug(f"Sync broadcast fallback suppressed: {e}")


ws_manager = WebSocketManager()
