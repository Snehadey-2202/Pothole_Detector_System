# pyrefly: ignore [missing-import]
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import sqlite3
import os
import sys
import json
from datetime import datetime
from uuid import uuid4
import subprocess

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT_DIR)

from env_utils import load_env_file

load_env_file()

app = FastAPI(title="Pothole Detection API")

cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "*").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")
INGEST_TOKEN = os.getenv("INGEST_TOKEN")
ALLOW_RESET = os.getenv("ALLOW_RESET", "true").lower() == "true"
DB_PATH = os.path.join(ROOT_DIR, "detections.db")
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "..", "public")
FRONTEND_DIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
FRONTEND_ASSETS_DIR = os.path.join(FRONTEND_DIST_DIR, "assets")
DETECTIONS_DIR = os.path.join(PUBLIC_DIR, "detections")

# Ensure public directory exists
os.makedirs(PUBLIC_DIR, exist_ok=True)
os.makedirs(DETECTIONS_DIR, exist_ok=True)

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

def require_ingest_token(x_ingest_token: str | None):
    if INGEST_TOKEN and x_ingest_token != INGEST_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid ingest token")


def safe_image_name(prefix="det"):
    return f"{prefix}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{uuid4().hex[:8]}.jpg"


async def save_upload(upload: UploadFile, filename: str):
    if upload.content_type and not upload.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are supported")

    file_path = os.path.join(DETECTIONS_DIR, filename)
    with open(file_path, "wb") as output_file:
        while chunk := await upload.read(1024 * 1024):
            output_file.write(chunk)
    return f"/detections/{filename}"


def write_live_status(prediction=None, confidence=None, image_path="/detections/current_frame.jpg"):
    status_path = os.path.join(DETECTIONS_DIR, "status.json")
    status = {
        "frame_updated_at": datetime.now().isoformat(),
        "prediction": prediction,
        "confidence": confidence,
        "image_path": image_path,
    }
    with open(status_path, "w", encoding="utf-8") as status_file:
        json.dump(status, status_file)

# ----------------- Specialized Routes -----------------

@app.get("/detections/current_frame.jpg")
def serve_current_frame():
    local_path = os.path.join(DETECTIONS_DIR, "current_frame.jpg")
    if os.path.exists(local_path):
        return FileResponse(local_path, headers={"Cache-Control": "no-store"})
    return {"error": "Current frame not available yet."}

# Mount public directory for serving local images statically
app.mount("/detections", StaticFiles(directory=DETECTIONS_DIR), name="detections")

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

@app.get("/api/health")
def health_check():
    return {"ok": True}

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

@app.get("/api/live-status")
def live_status():
    status_path = os.path.join(DETECTIONS_DIR, "status.json")
    current_frame_path = os.path.join(DETECTIONS_DIR, "current_frame.jpg")

    status = {
        "has_frame": os.path.exists(current_frame_path),
        "frame_updated_at": None,
        "prediction": None,
        "confidence": None,
        "image_path": "/detections/current_frame.jpg",
    }

    if os.path.exists(status_path):
        try:
            with open(status_path, "r", encoding="utf-8") as status_file:
                status.update(json.load(status_file))
        except (OSError, json.JSONDecodeError) as e:
            print(f"Error reading live status: {e}")

    if status["has_frame"] and not status.get("frame_updated_at"):
        modified_at = os.path.getmtime(current_frame_path)
        status["frame_updated_at"] = datetime.fromtimestamp(modified_at).isoformat()

    return status

@app.post("/api/live-frame")
async def ingest_live_frame(
    image: UploadFile = File(...),
    prediction: str | None = Form(default=None),
    confidence: float | None = Form(default=None),
    x_ingest_token: str | None = Header(default=None),
):
    require_ingest_token(x_ingest_token)
    image_path = await save_upload(image, "current_frame.jpg")
    write_live_status(prediction=prediction, confidence=confidence, image_path=image_path)
    return {"ok": True, "image_path": image_path}

@app.post("/api/detections")
async def ingest_detection(
    image: UploadFile = File(...),
    timestamp: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    confidence: float = Form(...),
    x_ingest_token: str | None = Header(default=None),
):
    require_ingest_token(x_ingest_token)
    image_path = await save_upload(image, safe_image_name())
    query = '''
        INSERT INTO detections (timestamp, latitude, longitude, confidence, image_path)
        VALUES (%s, %s, %s, %s, %s)
    '''
    run_query(query, (timestamp, latitude, longitude, confidence, image_path), commit=True)
    return {"ok": True, "image_path": image_path}

@app.post("/api/reset")
def reset_db():
    """Clears all detections from the database."""
    if not ALLOW_RESET:
        raise HTTPException(status_code=403, detail="Reset is disabled")
    query = "DELETE FROM detections"
    run_query(query, commit=True)
    return {"message": "Database reset successfully"}

@app.post("/api/run-edge")
def run_edge():
    """Runs the run_edge.ps1 script."""
    if os.name == 'nt':
        script_path = os.path.join(ROOT_DIR, "run_edge.ps1")
        if not os.path.exists(script_path):
            raise HTTPException(status_code=404, detail="Edge script not found")
        
        try:
            subprocess.Popen(
                ["powershell.exe", "-ExecutionPolicy", "Bypass", "-NoExit", "-File", script_path],
                cwd=ROOT_DIR,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            return {"message": "Edge node started successfully (Windows)"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # Linux / Render deployment
        edge_script = os.path.join(ROOT_DIR, "edge", "scheduler.py")
        if not os.path.exists(edge_script):
            raise HTTPException(status_code=404, detail="Edge script not found in deployment")
        
        try:
            subprocess.Popen(
                [sys.executable, edge_script],
                cwd=os.path.join(ROOT_DIR, "edge")
            )
            return {"message": "Edge node started successfully (Linux)"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

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
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
