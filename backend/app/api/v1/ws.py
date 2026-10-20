"""
SmartCart AI - Real-Time Dashboard WebSocket Router
Provides live telemetry, alert streams, and checkout verification broadcasts to staff interfaces.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.app.core.logging import logger
from backend.app.core.websocket import ws_manager

router = APIRouter(prefix="/ws", tags=["Real-Time WebSockets"])


@router.websocket("/dashboard")
async def dashboard_websocket_endpoint(websocket: WebSocket):
    """
    Bi-directional real-time WebSocket connection for store staff dashboard.
    Receives pings/heartbeats from client, broadcasts real-time alerts,
    session verifications, and inventory updates.
    """
    await ws_manager.connect(websocket)
    # Send initial welcome and synchronization handshake
    try:
        await websocket.send_json({
            "event_type": "HANDSHAKE_ESTABLISHED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Connected to SmartCart AI Real-Time Retail Stream.",
            "protocol_version": "1.0"
        })

        while True:
            # Keep connection open, handle client heartbeats
            data = await websocket.receive_text()
            if data == "ping" or data == '{"type":"ping"}':
                await websocket.send_json({
                    "event_type": "PONG",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket client error: {e}")
        ws_manager.disconnect(websocket)
