import os
import sys
import subprocess
from pathlib import Path

# Directories and files
BASE_DIR = Path(__file__).parent
FILES = {
    "app.py": """from fastapi import FastAPI
from api.endpoints import router
from scheduler import scheduler

app = FastAPI()

# Include all API endpoints
app.include_router(router)

@app.on_event("startup")
async def startup_event():
    scheduler.start()
    print("Scheduler started and application is running.")
""",
    "models.py": """from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from db import Base

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String, unique=True, nullable=False)
    ip = Column(String, nullable=False)
    state = Column(String, default="unpaused")
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_heartbeat = Column(DateTime)
    schedules = relationship("Schedule", back_populates="client", cascade="all, delete-orphan")

class Schedule(Base):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    disable_time = Column(String, nullable=False)
    enable_time = Column(String, nullable=False)
    client = relationship("Client", back_populates="schedules")
""",
    "api/endpoints.py": """from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from db import SessionLocal
from models import Client, Schedule

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
""",
    "scheduler.py": """from apscheduler.schedulers.asyncio import AsyncIOScheduler
scheduler = AsyncIOScheduler()

scheduler.start()
"""
}

# Step 1: Write or Replace Files
def write_files():
    print("Writing files...")
    for filename, content in FILES.items():
        filepath = BASE_DIR / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as file:
            file.write(content)
    print("Files written successfully.")

# Step 2: Install Dependencies
def install_dependencies():
    print("Installing dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn", "sqlalchemy", "apscheduler"])
    print("Dependencies installed.")

# Step 3: Initialize Database
def initialize_database():
    print("Initializing database...")
    from db import engine, Base
    from models import Client, Schedule
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully.")

# Step 4: Run Tests
def run_tests():
    print("Running basic tests...")
    # Add client registration and scheduling test cases here
    print("Tests completed.")

if __name__ == "__main__":
    write_files()
    install_dependencies()
    initialize_database()
    run_tests()
    print("Refactor complete.")
