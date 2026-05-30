# syntax=docker/dockerfile:1.7

# ---------- Frontend build ----------
FROM node:22-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------- Backend runtime ----------
FROM python:3.12-slim AS backend
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libffi-dev \
        libjpeg-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.9.21

WORKDIR /app
COPY backend/pyproject.toml ./pyproject.toml
RUN uv sync --no-install-project

COPY backend/app ./app

COPY --from=frontend-build /frontend/dist /app/frontend_dist

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
