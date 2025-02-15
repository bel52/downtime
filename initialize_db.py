import sqlite3
from contextlib import closing

DB_PATH = "server.db"

def init_db():
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.executescript(
            """
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT UNIQUE NOT NULL,
    friendly_name TEXT,
    ip TEXT NOT NULL,
    state TEXT DEFAULT 'unpaused',
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_heartbeat DATETIME
);


            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                disable_time TEXT NOT NULL,
                enable_time TEXT NOT NULL,
                FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE CASCADE
            );
            """
        )

if __name__ == "__main__":
    init_db()
