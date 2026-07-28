# Compute service for the VRPTW optimizer, deployed to Google Cloud Run.
#
# This is the heavy half of the stack: torch, numba, OR-Tools and the DDQN
# transfer weights. The public API (Dockerfile.render) forwards every solve here
# because Render's free instance cannot hold this image in 512 MB.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
# The default index serves the CUDA build (~2.5 GB); Cloud Run has no GPU.
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

COPY src/ /app/src/
COPY data/ /app/data/
COPY rl_alns_dr_v15.safetensors /app/rl_alns_dr_v15.safetensors
COPY app.py /app/app.py

# numba writes its JIT cache next to the source by default; the layer is
# read-only at runtime, so point it at the writable overlay instead.
ENV PYTHONPATH=/app/src:/app/src/backend \
    NUMBA_CACHE_DIR=/tmp/numba_cache \
    MPLCONFIGDIR=/tmp/matplotlib \
    HF_HOME=/tmp/huggingface \
    PYTHONUNBUFFERED=1 \
    PORT=8080

RUN mkdir -p /tmp/numba_cache /app/logs

EXPOSE 8080

# Cloud Run injects $PORT. One worker only: a solve fans out across a
# ProcessPoolExecutor already, so a second uvicorn worker would double the
# torch resident set for no throughput.
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]
