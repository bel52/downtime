import socket
import subprocess
import requests
import time
from datetime import datetime

# Configuration
SERVER_IP = '192.168.86.10'  # Replace with your server's IP
SERVER_PORT = 65432          # Port for server communication
HEARTBEAT_URL = f"http://{SERVER_IP}/timelimits/heartbeat.php"
CLIENT_NAME = "PC1"
HEARTBEAT_INTERVAL = 60  # Time in seconds

def get_client_ip():
    """
    Retrieve the IP address of the current machine.
    """
    hostname = socket.gethostname()
    return socket.gethostbyname(hostname)

def create_allow_rules():
    """
    Create firewall rules to allow all communication with the server.
    """
    try:
        # Define rule names
        ALLOW_RULE_NAME = "Allow Server Communication"
        BLOCK_RULE_NAME = "Block All Outbound"

        # Delete existing allow rule to avoid duplicates
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={ALLOW_RULE_NAME}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Add allow rule for server communication (outbound)
        subprocess.run(
            [
                "netsh", "advfirewall", "firewall", "add", "rule",
                f"name={ALLOW_RULE_NAME}", "dir=out", "action=allow",
                "protocol=any", f"remoteip={SERVER_IP}"
            ],
            check=True
        )

        # Add allow rule for server communication (inbound)
        subprocess.run(
            [
                "netsh", "advfirewall", "firewall", "add", "rule",
                f"name={ALLOW_RULE_NAME}", "dir=in", "action=allow",
                "protocol=any", f"remoteip={SERVER_IP}"
            ],
            check=True
        )

        # Delete existing block rule to avoid conflicts
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={BLOCK_RULE_NAME}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Add block rule for all outbound traffic except the server
        block_command = [
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name={BLOCK_RULE_NAME}", "dir=out", "action=block",
            "protocol=any", "remoteip=0.0.0.0-192.168.86.9,192.168.86.11-255.255.255.255"
        ]
        subprocess.run(block_command, check=True)

        print("[INFO] Firewall rules created to allow server communication.")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to create firewall rules: {e}")

def ensure_firewall():
    """
    Ensure that Windows Firewall is enabled.
    """
    try:
        result = subprocess.run(
            ["netsh", "advfirewall", "show", "allprofiles"],
            stdout=subprocess.PIPE,
            text=True
        )
        if "State OFF" in result.stdout:
            print("[INFO] Firewall is not enabled. Enabling now...")
            subprocess.run(
                ["netsh", "advfirewall", "set", "allprofiles", "state", "on"],
                check=True
            )
            print("[INFO] Firewall enabled.")
        else:
            print("[INFO] Firewall is already enabled.")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to verify or enable firewall: {e}")

def send_heartbeat():
    """
    Send a heartbeat to the server with the client IP and name.
    """
    data = {
        "client_ip": get_client_ip(),
        "name": CLIENT_NAME
    }
    try:
        response = requests.post(HEARTBEAT_URL, json=data, timeout=10)
        response.raise_for_status()
        print(f"[DEBUG] Heartbeat sent: {response.text}")
    except requests.RequestException as e:
        print(f"[ERROR] Heartbeat error: {e}")

def execute_command(command):
    """
    Execute a system command.
    """
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip()
    except Exception as e:
        return False, str(e)

def handle_commands():
    """
    Listen for commands from the server and execute them.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((get_client_ip(), SERVER_PORT))
        s.listen(1)
        print(f"[INFO] Listening for commands on port {SERVER_PORT}...")
        while True:
            conn, addr = s.accept()
            with conn:
                print(f"[INFO] Connection established with {addr}...")
                command = conn.recv(1024).decode()
                if command == "pause":
                    print("[DEBUG] Command received: pause")
                    success, output = execute_command(
                        'netsh advfirewall firewall add rule name="Block All Outbound" dir=out action=block protocol=any remoteip=0.0.0.0-192.168.86.9,192.168.86.11-255.255.255.255'
                    )
                    if success:
                        conn.sendall(b"Pausing internet...\nOk.")
                    else:
                        conn.sendall(f"[ERROR] {output}".encode())
                elif command == "unpause":
                    print("[DEBUG] Command received: unpause")
                    success, output = execute_command(
                        'netsh advfirewall firewall delete rule name="Block All Outbound"'
                    )
                    if success:
                        conn.sendall(b"Unpausing internet...\nOk.")
                    else:
                        conn.sendall(f"[ERROR] {output}".encode())
                else:
                    print(f"[ERROR] Unknown command: {command}")
                    conn.sendall(b"[ERROR] Unknown command.")

if __name__ == "__main__":
    print("[INFO] Starting client script...")
    ensure_firewall()
    create_allow_rules()
    print("[INFO] Firewall rules verified.")
    send_heartbeat()
    handle_commands()
