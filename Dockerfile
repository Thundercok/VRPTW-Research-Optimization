# ==========================================
# Stage 1: Build the Vite frontend assets
# ==========================================
FROM node:20-slim AS frontend-builder
WORKDIR /app

# Copy dependency configs
COPY package*.json ./
COPY vite.config.js ./

# Copy frontend source files
COPY src/frontend/ ./src/frontend/

# Install dependencies and build static assets
RUN npm ci && npm run build

# ==========================================
# Stage 2: Create the Python runtime image
# ==========================================
FROM python:3.12-slim

# Install system dependencies (numba and other JIT elements may compile on install)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements (specifying torch CPU to save download/image size)
COPY requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# Copy source directories (vrptw, backend, frontend)
COPY src/ /app/src/

# Precompile python source to bytecode for faster startup
RUN python -m compileall /app/src

# Copy built frontend assets from Stage 1 builder
COPY --from=frontend-builder /app/dist /app/dist

# Copy trained weights and Solomon data files
COPY rl_alns_dr_v15.safetensors /app/rl_alns_dr_v15.safetensors
COPY data /app/data
RUN mkdir -p /app/logs

# Set python path to allow importing packages from src
ENV PYTHONPATH=/app/src:/app/src/backend

EXPOSE 8080

# Start FastAPI server on port 8080
CMD ["uvicorn", "src.backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
