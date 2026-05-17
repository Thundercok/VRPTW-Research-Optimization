dev:
	PYTHONPATH=./src/backend uv run uvicorn src.backend.main:app --host 127.0.0.1 --port 8000 --reload

test:
	PYTHONPATH=./src/backend uv run pytest tests/ -v