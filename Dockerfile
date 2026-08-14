# ================= Stage 1: Build Frontend =================
FROM node:24-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ================= Stage 2: Backend & Runtime =================
FROM python:3.12-slim AS runner
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements & install
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source
COPY backend/app ./app

# Copy built frontend assets to static dist
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Persistent data directory
VOLUME ["/app/data"]
ENV PORT=8000
ENV HOST=0.0.0.0
ENV BASE_DATA_DIR=/app/data
ENV STORAGE_DIR=/app/data/storage
ENV CACHE_DIR=/app/data/cache
ENV DATABASE_URL=sqlite+aiosqlite:////app/data/zero9repo.db

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
