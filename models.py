from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
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
