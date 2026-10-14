# Build from the repo root (the backend imports ../training):
#   docker build -f backend/Dockerfile -t mm-retina-backend .
# Checkpoints are gitignored; mount them at /app/training/checkpoints.
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu \
 && pip install -r backend/requirements.txt

COPY backend backend
COPY training training

WORKDIR /app/backend
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
  CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8000/api/health')"
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
