from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from db import SessionLocal
from models import Client, Schedule
from fastapi import WebSocket, WebSocketDisconnect
import logging

# Connected WebSocket clients dictionary
connected_clients = {}
router = APIRouter()

class ClientRegistration(BaseModel):
    client_id: str
    ip: str

class HeartbeatUpdate(BaseModel):
    client_id: str
    ip: str

class ScheduleUpdate(BaseModel):
    client_id: str
    disable_time: str
    enable_time: str

@router.post("/clients/register")
async def register_client(data: ClientRegistration, db: Session = Depends(SessionLocal)):
    try:
        existing_client = db.query(Client).filter(Client.client_id == data.client_id).first()
        if existing_client:
            existing_client.ip = data.ip
            existing_client.last_heartbeat = datetime.utcnow()
        else:
            new_client = Client(
                client_id=data.client_id,
                ip=data.ip,
                state="unpaused",
                registered_at=datetime.utcnow(),
                last_heartbeat=datetime.utcnow()
            )
            db.add(new_client)
        db.commit()
        return {"status": "success", "client_id": data.client_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to register client: {str(e)}")

@router.post("/clients/heartbeat")
async def update_heartbeat(data: HeartbeatUpdate, db: Session = Depends(SessionLocal)):
    try:
        client = db.query(Client).filter(Client.client_id == data.client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not registered.")
        client.ip = data.ip
        client.last_heartbeat = datetime.utcnow()
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update heartbeat: {str(e)}")

@router.post("/schedule")
async def set_schedule(data: ScheduleUpdate, db: Session = Depends(SessionLocal)):
    try:
        datetime.strptime(data.disable_time, "%H:%M")
        datetime.strptime(data.enable_time, "%H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid time format.")

    client = db.query(Client).filter(Client.client_id == data.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found.")

    schedule = db.query(Schedule).filter(Schedule.client_id == client.id).first()
    if schedule:
        schedule.disable_time = data.disable_time
        schedule.enable_time = data.enable_time
    else:
        schedule = Schedule(
            client_id=client.id,
            disable_time=data.disable_time,
            enable_time=data.enable_time
        )
        db.add(schedule)

    db.commit()
    return {"status": "success"}

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(client_id: str, websocket: WebSocket, db: Session = Depends(SessionLocal)):
    """Handle WebSocket connections for real-time updates."""
    await websocket.accept()
    try:
        # Validate the client_id exists
        client = db.query(Client).filter(Client.client_id == client_id).first()
        if not client:
            await websocket.close(code=1008)
            logging.error(f"WebSocket connection denied: Client {client_id} not found.")
            return
        
        connected_clients[client_id] = websocket
        logging.info(f"WebSocket connected: {client_id}")
        
        while True:
            # Listen for incoming messages if required
            message = await websocket.receive_json()
            logging.info(f"Received message from {client_id}: {message}")

    except WebSocketDisconnect:
        logging.warning(f"WebSocket disconnected: {client_id}")
    except Exception as e:
        logging.error(f"WebSocket error for {client_id}: {e}")
    finally:
        # Clean up WebSocket connection
        connected_clients.pop(client_id, None)
        logging.info(f"WebSocket connection closed for client {client_id}.")

@router.get("/clients/state/{client_id}")
async def get_client_state(client_id: str, db: Session = Depends(SessionLocal)):
    """Fetch the current state of a client."""
    client = db.query(Client).filter(Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found.")
    return {"client_id": client.client_id, "state": client.state}

@router.get("/clients/schedule/{client_id}")
async def get_client_schedule(client_id: str, db: Session = Depends(SessionLocal)):
    """Fetch the schedule for a client."""
    client = db.query(Client).filter(Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found.")
    schedule = db.query(Schedule).filter(Schedule.client_id == client.id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found.")
    return {"disable_time": schedule.disable_time, "enable_time": schedule.enable_time}
