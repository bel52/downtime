import socket
import subprocess
import logging
import threading
import time

# Configuration
SERVER_IP = "192.168.86.10"  # Replace with your server IP
SERVER_PORT = 65432
HEARTBEAT_INTERVAL = 30  # seconds
FIREWALL_RULE_NAME = "BlockInternet"

# Logging configuration
logging.basicConfig(
    filename="client.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def configure_firewall(action):
    """
    Configures the Windows firewall to block or allow all internet traffic.

    :param action: 'block' to block internet access, 'unblock' to allow internet access.
    """
    logging.info(f"Configuring firewall to {action} internet access...")
    try:
        if action == "block":
            # Delete existing rule, if any
            delete_command = f"netsh advfirewall firewall delete rule name={FIREWALL_RULE_NAME}"
            subprocess.run(delete_command, check=False, shell=True, capture_output=True, text=True)

            # Add a new blocking rule
            add_command = f"netsh advfirewall firewall add rule name={FIREWALL_RULE_NAME} dir=out action=block protocol=any"
            result = subprocess.run(add_command, check=True, shell=True, capture_output=True, text=True)
            logging.info(f"Firewall rule added successfully: {result.stdout.strip()}")

        elif action == "unblock":
            # Delete the blocking rule
            delete_command = f"netsh advfirewall firewall delete rule name={FIREWALL_RULE_NAME}"
            result = subprocess.run(delete_command, check=False, shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                logging.info(f"Firewall rule deleted successfully: {result.stdout.strip()}")
            else:
                logging.warning(f"No existing rule to delete. Command output: {result.stderr.strip()}")

        else:
            logging.error(f"Unknown action '{action}' specified for firewall configuration.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to configure firewall. Command: {e.cmd} | Return Code: {e.returncode} | Output: {e.output}")
    except Exception as e:
        logging.error(f"Unexpected error in configure_firewall: {e}")

def send_heartbeat():
    """
    Sends a heartbeat message to the server at regular intervals.
    """
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((SERVER_IP, SERVER_PORT))
                s.sendall(b"status")
                logging.info("Heartbeat sent successfully.")
        except Exception as e:
            logging.error(f"Failed to send heartbeat: {e}")
        time.sleep(HEARTBEAT_INTERVAL)

def listen_for_commands():
    """
    Listens for commands from the server and executes them.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind(("0.0.0.0", SERVER_PORT))
        server_socket.listen(5)
        logging.info(f"Listening for commands on port {SERVER_PORT}...")

        while True:
            client_socket, client_address = server_socket.accept()
            with client_socket:
                logging.info(f"Connected by {client_address}")
                try:
                    data = client_socket.recv(1024).decode("utf-8").strip()
                    logging.info(f"Received command: {data}")

                    if data == "pause":
                        configure_firewall("block")
                        client_socket.sendall(b"Internet access blocked.\n")
                    elif data == "unpause":
                        configure_firewall("unblock")
                        client_socket.sendall(b"Internet access unblocked.\n")
                    elif data == "status":
                        client_socket.sendall(b"Client is online and listening.\n")
                    else:
                        logging.warning(f"Unknown command received: {data}")
                        client_socket.sendall(b"Unknown command.\n")
                except Exception as e:
                    logging.error(f"Error handling command: {e}")
                    client_socket.sendall(b"Error processing command.\n")

def main():
    """
    Main function to start the client script.
    """
    logging.info("Starting client script...")
    try:
        # Ensure internet access is allowed at the start
        configure_firewall("unblock")

        # Start the heartbeat thread
        send_heartbeat_thread = threading.Thread(target=send_heartbeat, daemon=True)
        send_heartbeat_thread.start()

        # Listen for commands
        listen_for_commands()
    except Exception as e:
        logging.error(f"Critical error in main: {e}")

if __name__ == "__main__":
    main()
