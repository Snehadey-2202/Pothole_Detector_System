import os
import sqlite3

DATABASE_URL = os.getenv("DATABASE_URL")
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "detections.db")

def get_db_connection():
    if DATABASE_URL:
        # Lazy import psycopg2 so local developer environment works without psycopg2 installed
        import psycopg2
        from psycopg2.extras import RealDictCursor
        url = DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(url, cursor_factory=RealDictCursor)
        return conn
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def run_query(query, params=(), fetch_all=False, fetch_one=False, commit=False):
    is_postgres = bool(DATABASE_URL)
    
    # SQLite uses ? placeholder, PostgreSQL uses %s
    if not is_postgres:
        query = query.replace("%s", "?")
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if commit:
            conn.commit()
            
        if fetch_all:
            result = cursor.fetchall()
            return [dict(row) for row in result]
        elif fetch_one:
            result = cursor.fetchone()
            return dict(result) if result else None
        return None
    finally:
        conn.close()

def init_db():
    is_postgres = bool(DATABASE_URL)
    if is_postgres:
        query = '''
            CREATE TABLE IF NOT EXISTS detections (
                id SERIAL PRIMARY KEY,
                timestamp VARCHAR(100) NOT NULL,
                latitude DOUBLE PRECISION NOT NULL,
                longitude DOUBLE PRECISION NOT NULL,
                confidence DOUBLE PRECISION NOT NULL,
                image_path TEXT NOT NULL
            )
        '''
        print("Initializing PostgreSQL database...")
    else:
        query = '''
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                confidence REAL NOT NULL,
                image_path TEXT NOT NULL
            )
        '''
        print(f"Initializing SQLite database at {DB_PATH}...")
        
    run_query(query, commit=True)
    print("Database initialized successfully.")

if __name__ == "__main__":
    init_db()

