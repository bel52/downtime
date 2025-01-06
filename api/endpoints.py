from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db import (
    add_client,
    get_client_by_name,
    execute_query
)

# Define your API router
router = APIRouter()

# Models
class Client(BaseModel):
    name: str
    ip: str
    state: str = "unpaused"  # Default state

# Register a client
@router.post("/clients/register")
async def register_client(client: Client):
    """
    Registers a new client or updates an existing client's IP and state.
    """
    add_client(client.name, client.ip, client.state)
    return {"status": "success", "message": "Client registered successfully."}

# Update client's heartbeat
@router.post("/clients/heartbeat")
async def update_heartbeat(client: Client):
    """
    Updates the last known heartbeat and state for a client.
    """
    db_client = get_client_by_name(client.name)
    if not db_client:
        return {"error": "Client not registered."}
    query = """
    UPDATE clients
    SET ip = ?, state = ?, last_heartbeat = CURRENT_TIMESTAMP
    WHERE name = ?
    """
    execute_query(query, (client.ip, client.state, client.name))
    return {"status": "success", "message": "Heartbeat updated successfully."}
