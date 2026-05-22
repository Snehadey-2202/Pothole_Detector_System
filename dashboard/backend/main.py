# pyrefly: ignore [missing-import]
from fastapi import FastAPI, Depends
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
import sqlite3
import os

app = FastAPI(title="Pothole Detection API")

# Setup CORS to allow the React frontend to communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "detections.db")
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "..", "public")
FRONTEND_DIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
FRONTEND_ASSETS_DIR = os.path.join(FRONTEND_DIST_DIR, "assets")

# Ensure public directory exists
os.makedirs(PUBLIC_DIR, exist_ok=True)
os.makedirs(os.path.join(PUBLIC_DIR, "detections"), exist_ok=True)

# ----------------- Database Setup & Query Helpers -----------------

def get_db_connection():
    if DATABASE_URL:
        # Lazy import psycopg2 to prevent required local installations
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
    run_query(query, commit=True)

init_db()

# ----------------- Specialized Routes -----------------

# Intercept current_frame.jpg requests for Cloudinary redirection
@app.get("/detections/current_frame.jpg")
def serve_current_frame():
    cloudinary_url = os.getenv("CLOUDINARY_URL")
    if cloudinary_url:
        try:
            # Construct delivery URL from CLOUDINARY_URL environment variable
            # Format: cloudinary://API_KEY:API_SECRET@CLOUD_NAME
            cloud_name = cloudinary_url.split("@")[-1]
            if "?" in cloud_name:
                cloud_name = cloud_name.split("?")[0]
            if "/" in cloud_name:
                cloud_name = cloud_name.split("/")[0]
            
            url = f"https://res.cloudinary.com/{cloud_name}/image/upload/v1/current_frame.jpg"
            return RedirectResponse(url)
        except Exception as e:
            print(f"Error parsing Cloudinary URL: {e}")
            
    # Local fallback
    local_path = os.path.join(PUBLIC_DIR, "detections", "current_frame.jpg")
    if os.path.exists(local_path):
        return FileResponse(local_path)
    return {"error": "Current frame not available yet."}

# Mount public directory for serving local images statically
app.mount("/detections", StaticFiles(directory=os.path.join(PUBLIC_DIR, "detections")), name="detections")

# Mount React static assets if built
if os.path.exists(FRONTEND_ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=FRONTEND_ASSETS_DIR), name="assets")

# ----------------- API Endpoints -----------------

@app.get("/")
def read_root():
    index_path = os.path.join(FRONTEND_DIST_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Pothole Detection API is running. Build frontend to see dashboard."}

@app.get("/api/detections")
def get_detections():
    """Returns all pothole detections from the database."""
    query = "SELECT * FROM detections ORDER BY timestamp DESC"
    return run_query(query, fetch_all=True)

@app.get("/api/stats")
def get_stats():
    """Returns basic stats about the detections."""
    query = "SELECT COUNT(*) as count FROM detections"
    result = run_query(query, fetch_one=True)
    count = result["count"] if result else 0
    return {"total_detected": count}

@app.post("/api/reset")
def reset_db():
    """Clears all detections from the database."""
    query = "DELETE FROM detections"
    run_query(query, commit=True)
    return {"message": "Database reset successfully"}

@app.get("/{catchall:path}")
def catch_all(catchall: str):
    # Only serve index.html for non-API routes when it exists
    if not catchall.startswith("api"):
        index_path = os.path.join(FRONTEND_DIST_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
    return {"detail": "Not Found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

