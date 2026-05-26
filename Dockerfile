FROM node:22-slim AS frontend-build

WORKDIR /app/dashboard/frontend
COPY dashboard/frontend/package*.json ./
RUN npm ci
COPY dashboard/frontend ./
RUN npm run build

FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY requirements.txt ./
COPY requirements-edge.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-edge.txt

COPY env_utils.py ./
COPY dashboard ./dashboard
COPY edge ./edge
COPY ml ./ml
COPY models ./models
COPY dataset ./dataset
COPY --from=frontend-build /app/dashboard/frontend/dist ./dashboard/frontend/dist

RUN mkdir -p dashboard/public/detections

EXPOSE 8000
CMD ["sh", "-c", "uvicorn dashboard.backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
