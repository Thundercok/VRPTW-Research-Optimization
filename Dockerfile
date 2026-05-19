FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/backend ./src/backend
COPY docs/vrptw ./docs/vrptw
COPY logs ./logs
WORKDIR /app/src/backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
