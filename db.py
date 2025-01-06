import sqlite3
from contextlib import closing

DB_PATH = "server.db"

# Initialize database
def init_db():
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
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
        """)

# Query utilities
def execute_query(query, params=(), fetch_one=False, fetch_all=False):
    try:
        with closing(sqlite3.connect(DB_PATH)) as conn, conn:
            cursor = conn.execute(query, params)
            if fetch_one:
                return cursor.fetchone()
            if fetch_all:
                return cursor.fetchall()
            return cursor.lastrowid
    except sqlite3.DatabaseError as e:
        print(f"Database error: {e}")
        return None

# Client-specific utilities
def add_client(name, ip, state="unpaused"):
    query = """
    INSERT INTO clients (name, ip, state)
    VALUES (?, ?, ?)
    ON CONFLICT(name) DO UPDATE SET
        ip = ?,
        state = ?;
    """
    execute_query(query, (name, ip, state, ip, state))

def get_client_by_name(name):
    query = "SELECT * FROM clients WHERE name = ?"
    return execute_query(query, (name,), fetch_one=True)

# Schedule-specific utilities
def add_schedule(client_id, disable_time, enable_time):
    query = """
    INSERT INTO schedules (client_id, disable_time, enable_time)
    VALUES (?, ?, ?);
    """
    execute_query(query, (client_id, disable_time, enable_time))

def get_schedule_by_client_name(name):
    query = """
    SELECT s.disable_time, s.enable_time
    FROM schedules s
    JOIN clients c ON s.client_id = c.id
    WHERE c.name = ?;
    """
    return execute_query(query, (name,), fetch_one=True)
