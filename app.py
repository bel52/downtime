from fastapi import FastAPI, Request, Form, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, validator
import datetime
import logging
import asyncio
import uuid
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from websockets.exceptions import ConnectionClosedError

# Initialize FastAPI and database
app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

DATABASE_URL = "sqlite:///server.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Global variables
connected_clients = {}  # Persistent client WebSocket connections
scheduler = AsyncIOScheduler()
scheduler.start()

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
    websocket_id = Column(String, nullable=True)  # To track WebSocket connections

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

# Utility functions
def schedule_downtime(client_id, disable_time, enable_time):
    """Schedule downtime and enable events using APScheduler."""
    scheduler.add_job(
        lambda: update_client_state(client_id, "paused"),
        "cron",
        hour=int(disable_time.split(":")[0]),
        minute=int(disable_time.split(":")[1]),
        id=f"{client_id}_disable",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: update_client_state(client_id, "unpaused"),
        "cron",
        hour=int(enable_time.split(":")[0]),
        minute=int(enable_time.split(":")[1]),
        id=f"{client_id}_enable",
        replace_existing=True,
    )

def update_client_state(client_id, state):
    """Update the client's state in the database and notify via WebSocket."""
    with SessionLocal() as db:
        client = db.query(Client).filter(Client.client_id == client_id).first()
        if client:
            client.state = state
            db.commit()
            logging.info(f"Client {client.name} state updated to {state}.")
            client_websocket = connected_clients.get(client_id)
            if client_websocket:
                asyncio.create_task(
                    client_websocket["websocket"].send_json({"action": "state_update", "state": state})
                )

# Models for API validation
class ClientRegistration(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    ip: str = Field(..., regex=r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")

    @validator("name")
    def name_unique(cls, name, values):
        with SessionLocal() as db:
            if db.query(Client).filter(Client.name == name).first():
                raise ValueError("Client name already exists.")
        return name

# WebSocket endpoint
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """Handle WebSocket communication."""
    await websocket.accept()
    with SessionLocal() as db:
        client = db.query(Client).filter(Client.client_id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        client.websocket_id = websocket.client.host
        db.commit()

    connected_clients[client_id] = {"websocket": websocket}
    logging.info(f"WebSocket connected: {client_id}")

    try:
        while True:
            message = await websocket.receive_json()
            logging.info(f"Received message from {client_id}: {message}")
    except ConnectionClosedError:
        logging.warning(f"WebSocket disconnected: {client_id}")
    finally:
        connected_clients.pop(client_id, None)

# Register a new client
@app.post("/clients/register")
async def register_client(data: ClientRegistration, db: SessionLocal = Depends(get_db)):
    """Register a client with validation."""
    client = db.query(Client).filter(Client.name == data.name).first()
    if client:
        # Update existing client
        client.ip = data.ip
        client.last_heartbeat = datetime.datetime.utcnow()
    else:
        # Register new client
        client = Client(name=data.name, ip=data.ip)
        db.add(client)
    db.commit()
    logging.info(f"Client registered: {client.name}")
    return {"status": "success", "client_id": client.client_id}

# Set a schedule for a client
@app.post("/schedule")
async def set_schedule(client_id: str, disable_time: str, enable_time: str, db: SessionLocal = Depends(get_db)):
    """Set a schedule for the client."""
    client = db.query(Client).filter(Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    schedule = db.query(Schedule).filter(Schedule.client_id == client.id).first()
    if schedule:
        schedule.disable_time = disable_time
        schedule.enable_time = enable_time
    else:
        schedule = Schedule(client_id=client.id, disable_time=disable_time, enable_time=enable_time)
        db.add(schedule)

    db.commit()
    schedule_downtime(client_id, disable_time, enable_time)
    logging.info(f"Schedule set for client {client.name}: {disable_time} - {enable_time}")
    return {"status": "success"}

# Enforce downtime at startup
@app.on_event("startup")
async def startup_event():
    """Schedule all existing downtimes at startup."""
    with SessionLocal() as db:
        schedules = db.query(Schedule).all()
        for schedule in schedules:
            schedule_downtime(schedule.client.client_id, schedule.disable_time, schedule.enable_time)
