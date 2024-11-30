import socket
import threading

HOST = "0.0.0.0"
PORT = 65432

def handle_client(conn, addr):
    print(f"[INFO] Connection established with {addr}")
    while True:
        data = conn.recv(1024)
        if not data:
            break
        print(f"[INFO] Received from {addr}: {data.decode()}")
        conn.sendall(b"ACK")
    conn.close()
    print(f"[INFO] Connection with {addr} closed.")

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((HOST, PORT))
        server.listen()
        print(f"[INFO] Listening on {HOST}:{PORT}")
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr)).start()

if __name__ == "__main__":
    start_server()
