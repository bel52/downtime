import os
import logging
import socket
import datetime
import uuid
import json
import asyncio
import aiohttp
import websockets
from config import CONFIG  # Import centralized configurations

# Disable Python's output buffering
os.environ["PYTHONUNBUFFERED"] = "1"

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

# Utility functions
def get_local_ip():
    """Retrieve the local IP address."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            logging.info(f"Local IP address: {ip}")
            return ip
    except Exception as e:
        logging.error(f"Could not determine local IP: {e}")
        return "127.0.0.1"

def get_client_id():
    """Retrieve or generate the client's unique ID."""
    id_file = CONFIG["ID_FILE"]
    if os.path.exists(id_file):
        try:
            with open(id_file, "r") as f:
                client_id = f.read().strip()
                logging.info(f"Loaded client ID: {client_id}")
                return client_id
        except Exception as e:
            logging.error(f"Error reading client ID file: {e}")
    client_id = str(uuid.uuid4())
    save_client_id(client_id)
    return client_id

def save_client_id(client_id):
    """Save the client's ID to a local file."""
    try:
        with open(CONFIG["ID_FILE"], "w") as f:
            f.write(client_id)
        logging.info(f"Client ID saved: {client_id}")
    except Exception as e:
        logging.error(f"Error saving client ID: {e}")

async def register_client(client_id, local_ip):
    """Register the client with the server."""
    try:
        async with aiohttp.ClientSession() as session:
            payload = {"client_id": client_id, "ip": local_ip}
            url = CONFIG["SERVER_URL"] + "/clients/register"  # Corrected path
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    logging.info("Client registered successfully.")
                else:
                    logging.warning(f"Client registration failed: {response.status}")
    except Exception as e:
        logging.error(f"Error registering client: {e}")

async def fetch_schedule(client_id):
    """Fetch the schedule from the server."""
    try:
        async with aiohttp.ClientSession() as session:
            url = CONFIG["SERVER_URL"] + f"/clients/schedule/{client_id}"  # Corrected path
            async with session.get(url) as response:
                if response.status == 200:
                    schedule = await response.json()
                    logging.info(f"Schedule fetched: {schedule}")
                    return schedule
                else:
                    logging.warning(f"Failed to fetch schedule: {response.status}")
    except Exception as e:
        logging.error(f"Error fetching schedule: {e}")
    return None

async def send_heartbeat(client_id, local_ip):
    """Send periodic heartbeat to the server."""
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                payload = {"client_id": client_id, "ip": local_ip}
                url = CONFIG["SERVER_URL"] + "/clients/heartbeat"  # Corrected path
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        logging.info("Heartbeat sent successfully.")
                    else:
                        logging.warning(f"Heartbeat failed: {response.status}")
        except Exception as e:
            logging.error(f"Error sending heartbeat: {e}")
        await asyncio.sleep(CONFIG["HEARTBEAT_INTERVAL"])

async def websocket_client(client_id):
    """Connect to the server via WebSocket."""
    retry_delay = CONFIG["RETRY_DELAY"]
    while True:
        try:
            async with websockets.connect(f"{CONFIG['SERVER_URL']}/ws/{client_id}") as websocket:  # Corrected path
                logging.info("WebSocket connected.")
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)
                    if data.get("schedule"):
                        logging.info(f"Received new schedule: {data['schedule']}")
                    elif data.get("action") == "shutdown":
                        logging.info("Shutdown command received. Exiting...")
                        return
        except Exception as e:
            logging.error(f"WebSocket error: {e}. Retrying in {retry_delay} seconds.")
            await asyncio.sleep(retry_delay)

async def enforce_schedule(client_id):
    """Periodically enforce the downtime schedule."""
    while True:
        schedule = await fetch_schedule(client_id)
        if schedule:
            disable_time = datetime.datetime.strptime(schedule["disable_time"], "%H:%M").time()
            enable_time = datetime.datetime.strptime(schedule["enable_time"], "%H:%M").time()
            now = datetime.datetime.now().time()

            in_schedule = disable_time <= now <= enable_time or (
                disable_time > enable_time and (now >= disable_time or now <= enable_time)
            )
            configure_squid(block=in_schedule)
        else:
            logging.warning("No schedule retrieved. Using default configuration.")
        await asyncio.sleep(CONFIG["HEARTBEAT_INTERVAL"])

def configure_squid(block):
    """Modify and reload Squid configuration."""
    try:
        squid_path = os.path.join(CONFIG["SQUID_INSTALL_PATH"], "bin", "squid.exe")
        if not os.path.exists(squid_path):
            logging.error("Squid executable not found.")
            return

        config_content = "http_access deny all" if block else "http_access allow all"
        with open(CONFIG["SQUID_CONF_PATH"], "w") as conf_file:
            conf_file.write(f"http_port 3128\ndns_nameservers 8.8.8.8\n{config_content}\n")
        logging.info(f"Squid config updated: {config_content}")

        result = subprocess.run([squid_path, "-k", "reconfigure"], capture_output=True, text=True)
        if result.returncode == 0:
            logging.info("Squid reconfigured successfully.")
        else:
            logging.error(f"Squid reconfiguration failed: {result.stderr}")
    except Exception as e:
        logging.error(f"Error configuring Squid: {e}")

async def main():
    client_id = get_client_id()
    local_ip = get_local_ip()

    # Register client with server
    await register_client(client_id, local_ip)

    # Start tasks
    await asyncio.gather(
        enforce_schedule(client_id),
        send_heartbeat(client_id, local_ip),
        websocket_client(client_id),
    )

if __name__ == "__main__":
    asyncio.run(main())
