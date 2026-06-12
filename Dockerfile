FROM python:3.12-slim

# Install system dependencies if any are needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the core library src/vrptw, backend src/backend, and frontend src/frontend
COPY src/ /app/src/

# Copy weights and other data files
COPY rl_alns_dr_v15.safetensors /app/rl_alns_dr_v15.safetensors
COPY data /app/data
RUN mkdir -p /app/logs

# Set python path to allow importing packages from src
ENV PYTHONPATH=/app/src:/app/src/backend

WORKDIR /app

# Run from root, calling backend via python main.py or uvicorn
CMD ["uvicorn", "src.backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
