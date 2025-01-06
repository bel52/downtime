import asyncio
import json
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from fastapi import APIRouter, WebSocket
from typing import Dict

# Router for FastAPI endpoints
router = APIRouter()

# Connected WebSocket clients
connected_clients: Dict[str, WebSocket] = {}

# Existing schedules
SCHEDULES = {
    "PC1": {"disable_time": "22:00", "enable_time": "06:00"},
}

async def rebroadcast_schedules():
    """Periodically rebroadcast the schedules to all connected clients."""
    while True:
        for client_name, schedule in SCHEDULES.items():
            if client_name in connected_clients:
                try:
                    await connected_clients[client_name].send(json.dumps({"schedule": schedule}))
                    print(f"Schedule rebroadcast to {client_name}: {schedule}")
                except Exception as e:
                    print(f"Failed to send schedule to {client_name}: {e}")
        await asyncio.sleep(300)  # Rebroadcast every 5 minutes


@router.post("/schedule")
async def update_schedule(client_name: str, disable_time: str, enable_time: str):
    """Update the downtime schedule for a client."""
    if client_name in SCHEDULES:
        SCHEDULES[client_name]["disable_time"] = disable_time
        SCHEDULES[client_name]["enable_time"] = enable_time
    else:
        SCHEDULES[client_name] = {"disable_time": disable_time, "enable_time": enable_time}
    print(f"Schedule updated for {client_name}: {SCHEDULES[client_name]}")
    return {"status": "success", "schedule": SCHEDULES[client_name]}


@router.websocket("/ws/{client_name}")
async def websocket_endpoint(client_name: str, websocket: WebSocket):
    """Handle WebSocket connections from clients."""
    await websocket.accept()
    connected_clients[client_name] = websocket
    print(f"{client_name} connected via WebSocket.")

    # Send the initial schedule upon connection
    if client_name in SCHEDULES:
        try:
            await websocket.send(json.dumps({"schedule": SCHEDULES[client_name]}))
            print(f"Initial schedule sent to {client_name}: {SCHEDULES[client_name]}")
        except Exception as e:
            print(f"Failed to send initial schedule to {client_name}: {e}")

    try:
        while True:
            message = await websocket.receive_text()
            print(f"Message received from {client_name}: {message}")
            data = json.loads(message)

            # Handle resync request
            if data.get("action") == "resync":
                if client_name in SCHEDULES:
                    await websocket.send(json.dumps({"schedule": SCHEDULES[client_name]}))
                    print(f"Resync schedule sent to {client_name}: {SCHEDULES[client_name]}")

    except Exception as e:
        print(f"WebSocket connection with {client_name} closed: {e}")

    finally:
        if client_name in connected_clients:
            del connected_clients[client_name]
        print(f"{client_name} disconnected.")


# Background scheduler for periodic tasks
scheduler = BackgroundScheduler()
scheduler.add_job(rebroadcast_schedules, "interval", seconds=300)  # Rebroadcast every 5 minutes
scheduler.start()

# Ensure the scheduler is shutdown gracefully
import atexit
atexit.register(lambda: scheduler.shutdown())
