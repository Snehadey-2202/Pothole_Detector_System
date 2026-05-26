# Pothole Detector System

**Live Demo:** [https://pothole-detector-vajb.onrender.com/](https://pothole-detector-vajb.onrender.com/)
Local-first pothole detection demo with:

- FastAPI backend serving the API and production React build
- React dashboard for live frames, detections, map, and analytics
- Edge runner that processes frames, writes local detections, and can push to a deployed backend
- Integrated button in the dashboard to start the edge node remotely

## Local Development

Install backend dependencies:

```powershell
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
```

Install frontend dependencies:

```powershell
cd dashboard\frontend
npm install
cd ..\..
```

Run the backend:

```powershell
.\run_backend.ps1
```

Run the frontend dev server:

```powershell
.\run_frontend.ps1
```

Run the edge simulator:

```powershell
.\venv\Scripts\pip install -r requirements-edge.txt
.\run_edge.ps1
```

The frontend dev server proxies `/api` and `/detections` to `http://localhost:8000`.

## Configuration

Copy `.env.example` to `.env` for local overrides.

Useful values:

- `DETECTION_THRESHOLD`: default `0.5`
- `DATABASE_URL`: optional PostgreSQL URL; SQLite is used when omitted
- `INGEST_TOKEN`: optional shared secret for remote edge uploads
- `BACKEND_API_URL`: set on the edge device to push frames to a deployed backend
- `CORS_ORIGINS`: comma-separated allowed origins; defaults to `*`
- `ALLOW_RESET`: set `false` to disable clearing detections in public deployments

## Production Build

Build the frontend:

```powershell
cd dashboard\frontend
npm ci
npm run build
cd ..\..
```

Start the web service:

```powershell
.\venv\Scripts\python -m uvicorn dashboard.backend.main:app --host 0.0.0.0 --port 8000
```

The backend serves `dashboard/frontend/dist` at `/` and API routes under `/api`.

## Docker

Build and run the web dashboard:

```powershell
docker build -t pothole-detector .
docker run -p 8000:8000 --env-file .env pothole-detector
```

For durable production data, set `DATABASE_URL` to PostgreSQL. Local SQLite and local uploaded frames are ephemeral on most hosted containers.

## Remote Edge Uploads

When the edge process runs on a different machine, set:

```powershell
$env:BACKEND_API_URL = "https://your-deployed-dashboard"
$env:INGEST_TOKEN = "same-value-as-backend"
.\run_edge.ps1
```

The edge runner will still write local files, and it will also POST live frames and detections to the deployed backend.
