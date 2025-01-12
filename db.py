from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Define the database URL
DATABASE_URL = "sqlite:///server.db"

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Define the declarative base
Base = declarative_base()

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Utility functions for database operations
def get_db():
    """
    Dependency to get the database session.
    Ensures proper cleanup after the session is used.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper functions for common database operations
def add_client(client_id, ip, state="unpaused", db_session=None):
    """
    Add a new client to the database.
    """
    from models import Client
    try:
        new_client = Client(client_id=client_id, ip=ip, state=state)
        db_session.add(new_client)
        db_session.commit()
        return new_client
    except SQLAlchemyError as e:
        db_session.rollback()
        raise e

def get_client_by_id(client_id, db_session):
    """
    Retrieve a client by its unique client_id.
    """
    from models import Client
    return db_session.query(Client).filter(Client.client_id == client_id).first()

def get_all_clients(db_session):
    """
    Retrieve all clients from the database.
    """
    from models import Client
    return db_session.query(Client).all()

def add_schedule(client_id, disable_time, enable_time, db_session=None):
    """
    Add or update a schedule for a client.
    """
    from models import Schedule
    try:
        schedule = db_session.query(Schedule).filter(Schedule.client_id == client_id).first()
        if schedule:
            schedule.disable_time = disable_time
            schedule.enable_time = enable_time
        else:
            schedule = Schedule(client_id=client_id, disable_time=disable_time, enable_time=enable_time)
            db_session.add(schedule)
        db_session.commit()
        return schedule
    except SQLAlchemyError as e:
        db_session.rollback()
        raise e

def get_schedule_by_client_id(client_id, db_session):
    """
    Retrieve the schedule for a specific client.
    """
    from models import Schedule
    return db_session.query(Schedule).filter(Schedule.client_id == client_id).first()
