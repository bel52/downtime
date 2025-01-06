from fastapi import FastAPI, Request, Form, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from pydantic import BaseModel
import datetime
import logging
import json
import asyncio
import uuid

# Initialize FastAPI and database
app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

DATABASE_URL = "sqlite:///server.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Global variable to store connected clients
connected_clients = {}  # Format: {client_id: {"websocket": websocket, "queue": asyncio.Queue()}}

# Define database models
class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    friendly_name = Column(String, nullable=True)
    ip = Column(String, nullable=False)
    state = Column(String, default="unpaused")
    registered_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_heartbeat = Column(DateTime)
    client_id = Column(String, unique=True, default=lambda: str(uuid.uuid4()))

class Schedule(Base):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    disable_time = Column(String, nullable=False)
    enable_time = Column(String, nullable=False)
    client = relationship("Client", back_populates="schedules")

Client.schedules = relationship("Schedule", back_populates="client", cascade="all, delete-orphan")

Base.metadata.create_all(bind=engine)

# Dependency for database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models for WebSocket communication
class WebSocketMessage(BaseModel):
    action: str
    status: str | None = None

@app.on_event("startup")
async def startup_event():
    """Startup event to initialize state enforcement."""
    asyncio.create_task(enforce_downtime())

async def enforce_downtime():
    """Periodically enforce downtime schedules."""
    while True:
        db = SessionLocal()
        try:
            now = datetime.datetime.now().time()
            schedules = db.query(Schedule).all()
            for schedule in schedules:
                client = db.query(Client).filter(Client.id == schedule.client_id).first()
                if not client:
                    continue

                disable_time = datetime.datetime.strptime(schedule.disable_time, "%H:%M").time()
                enable_time = datetime.datetime.strptime(schedule.enable_time, "%H:%M").time()
                in_downtime = disable_time <= now <= enable_time or (
                    disable_time > enable_time and (now >= disable_time or now <= enable_time)
                )

                if in_downtime and client.state != "paused":
                    client.state = "paused"
                    db.commit()
                    client_info = connected_clients.get(client.client_id)
                    if client_info:
                        await client_info["websocket"].send_json({"action": "state_update", "paused": True})
                        logging.debug(f"Sent state_update (paused=True) to client {client.client_id}")
                elif not in_downtime and client.state != "unpaused":
                    client.state = "unpaused"
                    db.commit()
                    client_info = connected_clients.get(client.client_id)
                    if client_info:
                        await client_info["websocket"].send_json({"action": "state_update", "paused": False})
                        logging.debug(f"Sent state_update (paused=False) to client {client.client_id}")
        except Exception as e:
            logging.error(f"Error enforcing downtime: {e}")
        finally:
            db.close()
        await asyncio.sleep(60)

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, db: SessionLocal = Depends(get_db)):
    await websocket.accept()
    logging.info(f"WebSocket connection established with client_id: {client_id}")

    try:
        # Validate the provided client_id against the database
        client = db.query(Client).filter(Client.client_id == client_id).first()

        if client:
            # Known client: Update IP address and mark as active
            logging.info(f"Reusing existing client_id: {client_id} for IP: {websocket.client.host}")
            client.ip = websocket.client.host
            client.last_heartbeat = datetime.datetime.utcnow()  # Update heartbeat on connect
            db.commit()
        else:
            # Unknown client_id: Treat as invalid and close the connection
            logging.warning(f"Unknown client_id: {client_id}. Rejecting connection.")
            await websocket.close(code=1008, reason="Invalid client_id")
            return

        # Track the WebSocket connection in the global dictionary
        connected_clients[client_id] = {"websocket": websocket, "queue": asyncio.Queue()}

        # Main WebSocket message handling loop
        while True:
            try:
                data = await websocket.receive_json()
                logging.debug(f"Message received from client {client_id}: {data}")

                # Handle "register" action
                if data.get("action") == "register":
                    client_id_from_client = data.get("client_id")
                    if client_id_from_client != client_id:
                        logging.warning(f"Client {client_id} tried to register with mismatched ID: {client_id_from_client}. Ignoring.")
                        continue

                # Handle other actions
                elif data.get("action") == "state_update":
                    client_state = data.get("state")
                    logging.info(f"Client {client_id} state updated to: {client_state}")

                elif data.get("action") == "update_name":
                    new_name = data.get("new_name")
                    if new_name:
                        client.name = new_name
                        db.commit()
                        logging.info(f"Client {client_id} name updated to: {new_name}")
                        await websocket.send_json({"action": "update_name", "new_name": new_name})

                else:
                    logging.warning(f"Unknown action received from client {client_id}: {data}")

            except Exception as e:
                logging.error(f"Error processing message from client {client_id}: {e}")

    except WebSocketDisconnect:
        logging.warning(f"Client {client_id} disconnected.")
    except Exception as e:
        logging.error(f"Error in WebSocket handler for client {client_id}: {e}")
    finally:
        # Clean up the connection from the global dictionary
        connected_clients.pop(client_id, None)
        db.close()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: SessionLocal = Depends(get_db)):
    try:
        clients = db.query(Client).all()
        return templates.TemplateResponse("dashboard.html", {"request": request, "clients": clients})
    except Exception as e:
        logging.error(f"Failed to load dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to load dashboard.")

@app.post("/clients/update_state")
async def update_client_state(client_id: str, db: SessionLocal = Depends(get_db)):
    """Manually update a client's state."""
    client = db.query(Client).filter(Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found.")
    client_info = connected_clients.get(client.client_id)
    if client_info:
        schedule = client.schedules[0] if client.schedules else None
        await client_info["websocket"].send_json(
            {
                "action": "state_update",
                "paused": client.state == "paused",
                "schedule": {
                    "disable_time": schedule.disable_time if schedule else None,
                    "enable_time": schedule.enable_time if schedule else None,
                },
            }
        )
    return {"status": "success"}

@app.post("/control")
async def control_client(pause: bool = Form(...), client_id: str = Form(...), db: SessionLocal = Depends(get_db)):
    """Pause or unpause a client."""
    client = db.query(Client).filter(Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found.")
    client.state = "paused" if pause else "unpaused"
    db.commit()
    logging.info(f"Client {client.name} state updated to {client.state}")

    # Notify the client via WebSocket
    client_info = connected_clients.get(client_id)
    if client_info:
        try:
            await client_info["websocket"].send_json({"action": "state_update", "state": client.state})
        except Exception as e:
            logging.error(f"Failed to send state update to client {client_id}: {e}")
            connected_clients.pop(client_id, None)

    return RedirectResponse(url="/", status_code=303)

@app.post("/heartbeat.php")
async def heartbeat(client_id: str = Form(...), db: SessionLocal = Depends(get_db)):
    """Handle periodic heartbeat requests from clients."""
    logging.debug(f"Received heartbeat from client_id: {client_id}")
    try:
        client = db.query(Client).filter(Client.client_id == client_id).first()
        if not client:
            logging.warning(f"Heartbeat received for unknown client_id: {client_id}")
            raise HTTPException(status_code=404, detail="Client not found.")

        # Update the last_heartbeat timestamp
        client.last_heartbeat = datetime.datetime.utcnow()
        db.commit()

        logging.info(f"Heartbeat acknowledged for client_id: {client_id}")
        return {"status": "success", "message": "Heartbeat acknowledged."}
    except Exception as e:
        logging.error(f"Error handling heartbeat for client_id: {client_id}, error: {e}")
        raise HTTPException(status_code=500, detail="Error processing heartbeat.")

@app.post("/schedule")
async def set_schedule(client_id: str = Form(...), disable_time: str = Form(...), enable_time: str = Form(...), db: SessionLocal = Depends(get_db)):
    """Set a downtime schedule for a client."""
    client = db.query(Client).filter(Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found.")
    schedule = db.query(Schedule).filter(Schedule.client_id == client.id).first()
    if not schedule:
        schedule = Schedule(client_id=client.id, disable_time=disable_time, enable_time=enable_time)
        db.add(schedule)
    else:
        schedule.disable_time = disable_time
        schedule.enable_time = enable_time
    db.commit()

    client_websocket = connected_clients.get(client_id)
    if client_websocket:
        try:
            await client_websocket.send_text(json.dumps({"schedule": {"disable_time": disable_time, "enable_time": enable_time}}))
        except Exception:
            logging.error(f"Failed to notify client {client.name} of schedule change.")
    return RedirectResponse(url="/", status_code=303)

@app.post("/clients/rename")
async def rename_client(client_id: str = Form(...), new_name: str = Form(...), db: SessionLocal = Depends(get_db)):
    """Rename a client."""
    client = db.query(Client).filter(Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found.")
    if new_name != client.name and db.query(Client).filter(Client.friendly_name == new_name).first():
        raise HTTPException(status_code=400, detail="Friendly name already in use.")
    old_name = client.name
    client.name = new_name
    db.commit()

    # Notify the client via WebSocket
    client_info = connected_clients.get(client_id)
    if client_info:
        websocket = client_info.get("websocket")  # Retrieve the WebSocket object
        if websocket:  # Ensure the WebSocket is still connected
            try:
                await websocket.send_json({"action": "update_name", "new_name": new_name})
            except Exception as e:
                logging.error(f"Failed to send name update to client {client_id}: {e}")
                connected_clients.pop(client_id, None)

    logging.info(f"Client renamed from '{old_name}' to '{new_name}'")
    return RedirectResponse(url="/", status_code=303)

@app.post("/clients/delete")
async def delete_client(client_id: str = Form(...), db: SessionLocal = Depends(get_db)):
    """Delete a client."""
    client = db.query(Client).filter(Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found.")
    db.delete(client)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

async def handle_client_messages(client_id, websocket):
    """Handle client WebSocket messages."""
    while True:
        try:
            message = await connected_clients[client_id]["queue"].get()
            for retry in range(3):
                try:
                    await websocket.send_json(message)
                    logging.info(f"Sent message to client {client_id}: {message}")
                    break
                except Exception as e:
                    if retry < 2:
                        await asyncio.sleep(2 ** retry)
                        continue
                    logging.error(f"Failed to send message to client {client_id}: {e}")
                    break
        except Exception as e:
            logging.error(f"Unexpected error in client message handling: {e}")
            break
