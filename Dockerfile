# syntax=docker/dockerfile:1

# ---- 1. Frontend: build the React SPA
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- 2. Backend: Python server that also serves the built SPA
FROM python:3.12-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
# ffmpeg lets yt-dlp merge separate video/audio streams (needed for 720p/1080p from YouTube)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/pyproject.toml ./
COPY backend/easytv ./easytv
RUN pip install .
COPY --from=web /web/dist ./static
ENV EASYTV_STATIC_DIR=/app/static \
    EASYTV_DATA_DIR=/data \
    EASYTV_PORT=8080
VOLUME /data
EXPOSE 8080
CMD ["python", "-m", "easytv"]

# ---- 3. Tests: `./run.sh test`
FROM app AS test
RUN pip install pytest
COPY backend/tests ./tests
CMD ["python", "-m", "pytest", "-q", "tests"]
