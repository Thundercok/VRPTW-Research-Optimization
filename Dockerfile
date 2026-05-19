FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/backend ./src/backend
COPY vrptw.py ./vrptw.py
COPY rl_alns_dr_v15.safetensors ./rl_alns_dr_v15.safetensors
COPY docs/vrptw ./docs/vrptw
COPY docs/model ./docs/model
COPY logs ./logs
WORKDIR /app/src/backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
