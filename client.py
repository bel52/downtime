import os
import requests
import subprocess
import socket
import time
import logging
import ctypes

# Configuration
GITHUB_RAW_URL = "https://raw.githubusercontent.com/bel52/downtime/main/client.py"  # Raw GitHub URL to client.py
LOCAL_FILE = os.path.abspath(__file__)  # Path to the currently running script
SERVER_IP = "192.168.86.10"  # Replace with your server IP
SERVER_PORT = 65432
HEARTBEAT_INTERVAL = 30  # Time in seconds between heartbeats

# Logging setup
LOG_FILE = "client_log.txt"
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s - %(message)s")

# Function to fetch the latest version of the script from GitHub
def fetch_latest_version():
    """
    Fetches the latest version of the client script from GitHub.
    """
    try:
        logging.info("Checking for updates...")
        response = requests.get(GITHUB_RAW_URL)
        if response.status_code == 200:
            with open(LOCAL_FILE, "wb") as file:
                file.write(response.content)
            logging.info("Updated script successfully. Restarting...")
            subprocess.Popen(["python", LOCAL_FILE])  # Restart the updated script
            exit(0)
        else:
            logging.warning(f"Failed to fetch latest version: {response.status_code}")
    except Exception as e:
        logging.error(f"Error fetching latest version: {e}")

# Firewall helper functions
def run_command(cmd):
    try:
        subprocess.run(cmd, check=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {cmd} | Error: {e}")

def reset_firewall():
    """
    Resets the firewall and ensures traffic to/from the server is always allowed.
    """
    logging.info("Resetting firewall...")
    run_command("netsh advfirewall reset")
    run_command(f"netsh advfirewall firewall add rule name='Allow Server Traffic' dir=in action=allow remoteip={SERVER_IP}")
    run_command(f"netsh advfirewall firewall add rule name='Allow Server Traffic' dir=out action=allow remoteip={SERVER_IP}")
    logging.info("Firewall reset and server communication rules added.")

def block_internet():
    """
    Blocks all internet traffic except communication with the server.
    """
    logging.info("Blocking internet access...")
    reset_firewall()
    run_command("netsh advfirewall firewall add rule name='Block All Out' dir=out action=block remoteip=any")
    logging.info("Internet access blocked.")

def unblock_internet():
    """
    Allows all internet traffic.
    """
    logging.info("Unblocking internet access...")
    reset_firewall()
    logging.info("Internet access unblocked.")

# Function to handle server commands
def handle_command(command):
    if command == "pause":
        block_internet()
    elif command == "unpause":
        unblock_internet()
    else:
        logging.warning(f"Unknown command received: {command}")

# Heartbeat functionality
def send_heartbeat():
    """
    Sends a heartbeat to the server to indicate the client is active.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((SERVER_IP, SERVER_PORT))
            heartbeat_message = {"client_ip": socket.gethostbyname(socket.gethostname()), "name": "PC1"}
            s.sendall(str(heartbeat_message).encode())
            response = s.recv(1024).decode()
            logging.info(f"Heartbeat response: {response}")
            handle_command(response)
    except Exception as e:
        logging.error(f"Heartbeat failed: {e}")

# Main script execution
def main():
    # Ensure script is running with admin privileges
    if not ctypes.windll.shell32.IsUserAnAdmin():
        logging.error("Script must be run with administrator privileges.")
        print("Script must be run with administrator privileges.")
        exit(1)

    logging.info("Client script started.")
    reset_firewall()  # Reset the firewall on startup
    fetch_latest_version()  # Check for updates

    while True:
        send_heartbeat()
        time.sleep(HEARTBEAT_INTERVAL)

if __name__ == "__main__":
    main()
