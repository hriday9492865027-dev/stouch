"""
Digital Touchpad Windows Receiver Application (PRD v2.0)
Serves the PWA Client and provides low-latency WebSocket input dispatching.
"""

import os
import sys
import json
import socket
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from input_dispatcher import InputDispatcher
from action_handler import ActionHandler
from pairing import get_local_ip, generate_pairing_pin, generate_session_token, print_banner
from diagnostics import DiagnosticsManager

# Initialize Dispatchers
dispatcher = InputDispatcher()
action_handler = ActionHandler(dispatcher)
diagnostics = DiagnosticsManager(dispatcher, action_handler)

# Host Information
HOST_NAME = socket.gethostname()
CURRENT_PIN = generate_pairing_pin()
ACTIVE_TOKENS = set()

app = FastAPI(title="Digital Touchpad Windows Receiver")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket Input Endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = generate_session_token()
    client_ip = websocket.client.host if websocket.client else "unknown"
    print(f"[Receiver] Client connected from {client_ip}. Session ID: {session_id}")

    try:
        while True:
            raw_text = await websocket.receive_text()
            if not raw_text:
                continue

            try:
                data = json.loads(raw_text)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type", "")
            payload = data.get("payload", {})
            req_id = data.get("request_id")

            # 1. Session Negotiation
            if msg_type == "SESSION_HELLO":
                new_token = generate_session_token()
                ACTIVE_TOKENS.add(new_token)
                await websocket.send_json({
                    "version": "2.0",
                    "type": "SESSION_READY",
                    "session_id": session_id,
                    "payload": {
                        "host_name": HOST_NAME,
                        "token": new_token,
                        "capabilities": [
                            "pointer", "click", "drag", "scroll",
                            "actions", "power", "volume"
                        ]
                    }
                })

            # 2. Continuous Pointer Movement (High frequency)
            elif msg_type == "POINTER_MOVE":
                dx = payload.get("dx", 0)
                dy = payload.get("dy", 0)
                dispatcher.move_pointer(dx, dy)

            # 3. Mouse Button Events
            elif msg_type == "BUTTON_STATE":
                button = payload.get("button", "left")
                state = payload.get("state", "click")
                dispatcher.set_button_state(button, state)

            # 4. Wheel Scrolling
            elif msg_type == "SCROLL":
                dx = payload.get("dx", 0)
                dy = payload.get("dy", 0)
                dispatcher.scroll(dx, dy)

            # 5. Key Chord / Zooming
            elif msg_type == "KEY_CHORD":
                action = payload.get("action")
                if action == "zoom":
                    delta = payload.get("delta", 1)
                    # Ctrl + Wheel zoom
                    VK_CONTROL = 0x11
                    dispatcher.held_keys.add(VK_CONTROL)
                    dispatcher.scroll(0, delta * 3)
                    dispatcher.held_keys.discard(VK_CONTROL)

            # 6. Allowlisted Quick Actions
            elif msg_type == "ACTION_REQUEST":
                act_id = payload.get("action", "")
                result = action_handler.handle_action(act_id, payload)
                await websocket.send_json({
                    "version": "2.0",
                    "type": "ACTION_RESULT",
                    "request_id": req_id,
                    "payload": result
                })

            # 7. Heartbeat (Liveness & Latency Probe)
            elif msg_type == "HEARTBEAT":
                await websocket.send_json({
                    "version": "2.0",
                    "type": "HEARTBEAT",
                    "payload": {
                        "echo": payload.get("timestamp"),
                        "server_time": asyncio.get_event_loop().time()
                    }
                })

            # 8. Release All Inputs
            elif msg_type == "RELEASE_ALL":
                dispatcher.release_all()

    except WebSocketDisconnect:
        print(f"[Receiver] WebSocket disconnected cleanly from {client_ip}.")
    except Exception as e:
        print(f"[Receiver] Exception on socket ({client_ip}): {e}")
    finally:
        # Mandatory Safety Watchdog: release all held buttons/keys immediately on exit
        dispatcher.release_all()
        print(f"[Receiver] Release-all executed for {client_ip}.")


# Diagnostic API Endpoints (PRD Section 15 & AT-016)
@app.get("/api/diagnostics")
async def get_diagnostics():
    return diagnostics.get_health_report()

@app.get("/api/diagnostics/export")
async def export_diagnostics():
    return diagnostics.generate_redacted_export()

# Locate and mount PWA client directory
CLIENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "client"))
app.mount("/", StaticFiles(directory=CLIENT_DIR, html=True), name="client")


def run(port: int = 8000):
    print_banner(port, CURRENT_PIN)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")

if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run(port)
